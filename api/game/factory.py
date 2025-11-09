from typing import Optional
from game.session import SessionObject
from global_modules.models.cells import Cells
from global_modules.db.baseclass import BaseClass
from global_modules.models.resources import Production, Resource
from modules.db import just_db
from global_modules.load_config import ALL_CONFIGS, Resources, Improvements, Settings, Capital, Reputation
from modules.utils import *
from modules.websocket_manager import websocket_manager
from game.statistic import Statistic

RESOURCES: Resources = ALL_CONFIGS["resources"]
CELLS: Cells = ALL_CONFIGS['cells']
IMPROVEMENTS: Improvements = ALL_CONFIGS['improvements']
SETTINGS: Settings = ALL_CONFIGS['settings']
CAPITAL: Capital = ALL_CONFIGS['capital']
REPUTATION: Reputation = ALL_CONFIGS['reputation']

class Factory(BaseClass, SessionObject):

    __tablename__ = "factories"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id
        self.company_id: int = 0

        self.complectation: Optional[str] = None  # Какая комплектация производится
        self.progress: list[float] = [0.0, 0.0]  # [текущий прогресс, прогресс для завершения]

        self.produce: bool = False  # Должна ли фабрика производить продукцию
        self.is_auto: bool = False  # Автоматическое производство

        self.complectation_stages = 0  # Сколько ходов осталось до завершения комплектации

        self.produced: int = 0  # Сколько всего произведено продукции

        self.event_stack: list[dict] = []  # Стэк событий фабрики за этап

    async def create(self, 
                     company_id: int, 
                     complectation: Optional[str] = None,
                     is_auto: bool = False
                     ):
        """ Создание новой фабрики
        """
        if complectation not in RESOURCES.resources and complectation is not None:
            raise ValueError("Неверный тип комплектации.")

        self.company_id = company_id
        self.complectation = complectation

        if complectation is not None:
            production: Production = RESOURCES.get_resource(complectation).production # type: ignore

            turns = production.turns if production else 0
            self.progress = [0, turns]

        if is_auto and complectation is not None:
            self.is_auto = True
            self.produce = True

        await self.insert()
        await websocket_manager.broadcast({
            "type": "api-factory-create",
            "data": {
                "factory": await self.to_dict(),
                "company_id": self.company_id
            }
        })
        return self

    @property
    async def is_working(self) -> bool:
        """ Проверка, работает ли фабрика
        """

        if self.complectation_stages > 0: # Если идёт перекомплектация
            return False

        if self.complectation is None: # Если не выбрана комплектация
            return False

        if not self.produce and not self.is_auto: # Если не производит и не авто
            return False

        if not await self.check_materials(): # Если нет материалов
            return False

        return True

    async def pere_complete(self, new_complectation: str):
        """ Перекомплектация фабрики
        """
        from game.company import Company
        
        if new_complectation not in RESOURCES.resources:
            raise ValueError("Неверный тип комплектации.")

        # Проверяем, что ресурс не является сырьем
        new_resource = RESOURCES.get_resource(new_complectation)
        if new_resource is None:
            raise ValueError("Ресурс не найден.")
        
        if new_resource.raw:
            raise ValueError("Невозможно производить сырьевые ресурсы.")

        # Получаем уровни старой и новой комплектации
        old_level = 0
        if self.complectation is not None:
            old_level = RESOURCES.get_resource(self.complectation).lvl # type: ignore

        new_level = new_resource.lvl # type: ignore

        # Рассчитываем время перекомплектации
        if new_level > old_level:
            self.complectation_stages = new_level - old_level
        else:
            self.complectation_stages = new_level

        company = await Company(self.company_id).reupdate()
        mod_speed = 1.0
        if company:
            if company.fast_complectation:
                mod_speed = SETTINGS.fast_complectation

        self.complectation_stages = max(1, 
                int(self.complectation_stages // mod_speed))

        self.complectation = new_complectation
        production: Production = new_resource.production # type: ignore
        self.progress = [0, production.turns]

        await self.save_to_base()
        await websocket_manager.broadcast({
            "type": "api-factory-start-complectation",
            "data": {
            'factory_id': self.id,
            'company_id': self.company_id
            }
        })
        return True

    async def on_new_game_stage(self):
        from game.company import Company
        from game.session import Session

        company = await Company(self.company_id).reupdate()
        if not company:
            return False

        session = await Session(company.session_id).reupdate()
        if not session:
            return False
        
        self.event_stack = []  # Очищаем стэк событий компании
        await self.save_to_base()

        # Этап комплектации
        if self.complectation_stages > 0:
            self.complectation_stages -= 1
            await self.save_to_base()

            if self.complectation_stages == 0:
                await websocket_manager.broadcast({
                    "type": "api-factory-end-complectation",
                    "data": {
                        'factory_id': self.id,
                        'company_id': self.company_id
                    }
                })

                self.event_stack.append({
                    "type": "complectation_completed",
                })
                await self.save_to_base()
                return True

            else:
                self.event_stack.append({
                    "type": "complectation_progress",
                    "data": {
                        "stages_left": self.complectation_stages
                    }
                })
                await self.save_to_base()
                return True

        # Этап производства
        elif await self.is_working:
            resource = RESOURCES.get_resource(self.complectation) # type: ignore

            # Снимаем материалы со склада компании при первом ходе производства
            if self.progress[0] == 0:
                materials = resource.production.materials # type: ignore

                for mat, qty in materials.items():
                    try:
                        await company.remove_resource(mat, qty)
                    except Exception as e:
                        self.event_stack.append({
                            "type": "material_removal_failed",
                            "data": {
                                "material": mat,
                                "quantity": qty,
                                "error": str(e)
                            }
                        })
                        await self.save_to_base()
                        return False

            tasks_speed = session.get_event_effects().get(
                'tasks_speed', 1.0
            )
            self.progress[0] += tasks_speed

            # Если производство завершено - добавляем ресурсы на склад компании
            if self.progress[0] >= self.progress[1]:
                output = resource.production.output # type: ignore

                # Добавляем продукцию на склад компании
                if self.complectation:
                    free_space = await company.get_warehouse_free_size()
                    add_min = min(output, free_space)
                    await company.add_resource(
                            self.complectation, add_min,
                            )

                    self.produced += add_min
                    self.event_stack.append({
                        "type": "production_completed",
                        "data": {
                            "product": self.complectation,
                            "added": add_min,
                            "output": output
                        }
                    })

                    st = await Statistic().create(
                        session_id=company.session_id,
                        company_id=company.id,
                        step=session.step,
                    )
                    if st:
                        await st.update_me(
                            total_products_produced=add_min
                        )

                self.progress[0] = 0

                # Если авто, то проверяем материалы и продолжаем производство, если есть материалы
                if self.is_auto and await self.check_materials():
                    self.produce = True

                    self.event_stack.append({
                        "type": "production_continued",
                    })

                else:
                    self.produce = False
                    self.is_auto = False

                    self.event_stack.append({
                        "type": "production_stopped",
                    })

                await websocket_manager.broadcast({
                    "type": "api-factory-end-production",
                    "data": {
                        'factory_id': self.id,
                        'company_id': self.company_id
                    }
                })

            else:
                self.event_stack.append({
                    "type": "production_progress",
                    "data": {
                        "progress": self.progress[0],
                        "required": self.progress[1]
                    }
                })

            await self.save_to_base()
        return True

    async def set_produce(self, produce: bool):
        """ Установка статуса производства фабрики
        """
        if self.progress[0] == 0:
            self.produce = produce
            await self.save_to_base()
        else:
            raise ValueError("Нельзя изменить статус производства во время производства.")

    async def set_auto(self, is_auto: bool):
        """ Установка статуса автоматического производства фабрики
        """
        self.is_auto = is_auto
        await self.save_to_base()

    async def check_materials(self):
        """ Проверка наличия материалов для производства
        """
        from game.company import Company

        if self.complectation is None:
            raise ValueError("Комплектация не установлена.")

        resource: Resource = RESOURCES.get_resource(self.complectation) # type: ignore
        if not resource.production: return False

        materials = resource.production.materials # type: ignore

        company = await Company(self.company_id).reupdate()
        all_good = True
        for mat, qty in materials.items():
            if company.warehouses.get(mat, 0) < qty:
                all_good = False
                break

        return all_good

    async def to_dict(self) -> dict:
        """ Получение статуса фабрики
        """
        return {
            "id": self.id,
            "company_id": self.company_id,
            "complectation": self.complectation,
            "progress": self.progress,
            "produce": self.produce,
            "is_auto": self.is_auto,
            "complectation_stages": self.complectation_stages,
            "is_working": await self.is_working,
            "check_materials": await self.check_materials() if self.complectation else False,
            "event_stack": self.event_stack,
            "produced": self.produced
        }

    async def delete(self):
        """ Удаление фабрики
        """
        company_id = self.company_id
        factory_id = self.id

        await self.__db_object__.delete(self.__tablename__, 
                                  **{self.__unique_id__: self.id})

        await websocket_manager.broadcast({
            "type": "api-factory-delete",
            "data": {
                "factory_id": factory_id,
                "company_id": company_id
            }
        })

        return True