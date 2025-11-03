from typing import Optional, cast
from game.session import SessionObject
from global_modules.models.cells import Cells
from global_modules.db.baseclass import BaseClass
from modules.db import just_db
from global_modules.load_config import ALL_CONFIGS, Resources, Improvements, Settings, Capital, Reputation
from modules.function_way import *
from modules.websocket_manager import websocket_manager

RESOURCES: Resources = ALL_CONFIGS["resources"]
CELLS: Cells = ALL_CONFIGS['cells']
IMPROVEMENTS: Improvements = ALL_CONFIGS['improvements']
SETTINGS: Settings = ALL_CONFIGS['settings']
CAPITAL: Capital = ALL_CONFIGS['capital']
REPUTATION: Reputation = ALL_CONFIGS['reputation']

class Logistics(BaseClass, SessionObject):

    __tablename__ = "logistics"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id

        # Основная информация о грузе
        self.session_id: str = ""
        self.resource_type: str = ""
        self.amount: int = 0

        # Информация о маршруте
        self.from_company_id: int = 0  # ID компании отправителя
        self.to_company_id: int = 0    # ID компании получателя
        self.to_city_id: int = 0      # ID города получателя (альтернатива компании)
        self.destination_type: str = "company"  # "company" или "city"
        self.current_position: str = ""  # Текущая позиция "x.y"
        self.target_position: str = ""  # Целевая позиция "x.y"

        # Состояние доставки
        self.status: str = "in_transit"  # in_transit, waiting_pickup, delivered, failed
        self.distance_left: float = 0.0  # Оставшееся расстояние до цели
        self.waiting_turns: int = 0  # Количество ходов ожидания на месте назначения

        # Дополнительная информация для городов
        self.city_price: int = 0  # Цена за единицу при доставке в город
        self.created_step: int = 0  # На каком ходу была создана логистика

    async def get_delivery_speed(self) -> float:
        """Возвращает скорость доставки в клетках за ход"""

        session = await self.get_session_or_error()

        if not session:
            mod = 1.0
        else:
            mod = await session.get_event_effects().get(
                'cell_logistics', 1.0
            )

        return SETTINGS.logistics_speed * mod

    async def create(self, 
               session_id: str, resource_type: str, 
               amount: int, from_company_id: int, 
               to_company_id: Optional[int] = None,
               to_city_id: Optional[int] = None,
               sender_no_delete: bool = False
               ) -> 'Logistics':
        """Создает новую логистическую доставку"""
        
        if resource_type not in RESOURCES.resources:
            raise ValueError("Неверный тип ресурса")

        if amount <= 0:
            raise ValueError("Количество должно быть положительным")

        # Проверяем, что указана только одна цель
        if (to_company_id is None) == (to_city_id is None):
            raise ValueError("Необходимо указать либо ID компании, либо ID города получателя")

        # Получаем компанию отправителя
        from game.company import Company
        from game.citie import Citie

        sender_company = cast(Company, just_db.find_one("companies", id=from_company_id, to_class=Company))
        if not sender_company:
            raise ValueError("Компания отправитель не найдена")

        if not sender_no_delete:
            # Проверяем, что у компании достаточно ресурсов
            if resource_type not in sender_company.warehouses or sender_company.warehouses[resource_type] < amount:
                raise ValueError("Недостаточно ресурсов у компании отправителя")

        self.session_id = session_id
        session = await self.get_session_or_error()

        self.resource_type = resource_type
        self.amount = amount
        self.from_company_id = from_company_id
        self.current_position = sender_company.cell_position
        self.created_step = session.step

        if to_company_id is not None:
            # Доставка в компанию
            target_company = cast(Company, 
                await just_db.find_one("companies", 
                            id=to_company_id, 
                            to_class=Company, session_id=session_id
                ))

            if not target_company:
                raise ValueError("Компания получатель не найдена")

            self.destination_type = "company"
            self.to_company_id = to_company_id
            self.to_city_id = 0
            self.target_position = target_company.cell_position
            self.city_price = 0

        else:
            # Доставка в город
            target_city = cast(Citie, 
                await just_db.find_one("cities", 
                            id=to_city_id, 
                            to_class=Citie, session_id=session_id
                ))
            if not target_city:
                raise ValueError("Город получатель не найден")

            # Проверяем, что город принимает этот ресурс
            if resource_type not in target_city.demands:
                raise ValueError("Город не принимает этот ресурс")

            # Проверяем, что города достаточно спроса
            if amount > target_city.demands[resource_type]['amount']:
                raise ValueError(f"Город принимает только {target_city.demands[resource_type]['amount']} единиц этого ресурса")

            self.destination_type = "city"
            self.to_company_id = 0
            self.to_city_id = to_city_id if to_city_id is not None else 0
            self.target_position = target_city.cell_position
            self.city_price = target_city.demands[resource_type]['price']

        # Рассчитываем начальное расстояние до цели
        self.distance_left = self._calculate_distance()

        if not sender_no_delete:
            # Снимаем ресурсы с компании отправителя
            await sender_company.remove_resource(
                resource_type, amount)

        # Сохраняем в базу
        await self.insert()

        # Отправляем уведомление
        await websocket_manager.broadcast({
            "type": "api-logistics_created",
            "data": {
                "session_id": self.session_id,
                "logistics": self.to_dict()
            }
        })

        return self

    def _calculate_distance(self) -> float:
        """Рассчитывает манхэттенское расстояние между текущей и целевой позицией"""

        # Парсим позиции
        current_pos = [
            int(x) for x in self.current_position.split('.')]
        target_pos = [
            int(x) for x in self.target_position.split('.')]

        # Манхэттенское расстояние
        distance = abs(current_pos[0] - target_pos[0]) + abs(current_pos[1] - target_pos[1])

        return float(distance)

    async def move_next_step(self) -> bool:
        """Перемещает груз на следующий шаг по маршруту"""

        if self.status != "in_transit":
            return False

        # Если уже на месте
        if self.distance_left <= 0:
            return await self._attempt_delivery()

        # Перемещаемся с учетом скорости
        speed = await self.get_delivery_speed()
        self.distance_left = max(0, self.distance_left - speed)

        # Обновляем текущую позицию (приближаемся к цели)
        self._update_current_position(speed)

        # Проверяем, дошли ли до цели
        if self.distance_left <= 0:
            return await self._attempt_delivery()

        await self.save_to_base()

        # Отправляем уведомление о движении
        await websocket_manager.broadcast({
            "type": "api-logistics_moved",
            "data": {
                "logistics_id": self.id,
                "new_position": self.current_position,
                "distance_left": self.distance_left
            }
        })

        return True

    def _update_current_position(self, speed):
        """Обновляет текущую позицию, приближая к цели"""

        # Если уже на месте, устанавливаем целевую позицию
        if self.distance_left <= 0:
            self.current_position = self.target_position
            return

        # Парсим позиции
        current_pos = [
            int(x) for x in self.current_position.split('.')]
        target_pos = [
            int(x) for x in self.target_position.split('.')]

        # Двигаемся в сторону цели по одной клетке за раз (простая логика)
        if current_pos[0] < target_pos[0]:
            current_pos[0] += speed
        elif current_pos[0] > target_pos[0]:
            current_pos[0] -= speed
        elif current_pos[1] < target_pos[1]:
            current_pos[1] += speed
        elif current_pos[1] > target_pos[1]:
            current_pos[1] -= speed

        self.current_position = f"{current_pos[0]}.{current_pos[1]}"

    async def _attempt_delivery(self) -> bool:
        """Пытается доставить груз получателю"""
        
        if self.destination_type == "company":
            return await self._deliver_to_company()
        elif self.destination_type == "city":
            return await self._deliver_to_city()
        else:
            # Неизвестный тип назначения, помечаем как неудачу
            self.status = "failed"
            await self.save_to_base()
            return False
    
    async def _deliver_to_company(self) -> bool:
        """Доставляет груз компании"""
        
        from game.company import Company

        target_company = cast(Company, 
                              await just_db.find_one("companies", id=self.to_company_id, 
                                                     to_class=Company)
                              )
        if not target_company:
            self.status = "failed"
            await self.save_to_base()
            return False

        # Проверяем, есть ли место на складе
        free_space = await target_company.get_warehouse_free_size()

        if free_space >= self.amount:
            # Полная доставка
            await target_company.add_resource(self.resource_type, self.amount)

            self.status = "delivered"
            await self.save_to_base()

            await websocket_manager.broadcast({
                "type": "api-logistics_delivered",
                "data": {
                    "logistics_id": self.id,
                    "company_id": self.to_company_id,
                    "resource": self.resource_type,
                    "amount": self.amount
                }
            })

            return True
        else:
            # Недостаточно места, ждем
            self.status = "waiting_pickup"
            self.waiting_turns = 0
            await self.save_to_base()

            await websocket_manager.broadcast({
                "type": "api-logistics_waiting",
                "data": {
                    "logistics_id": self.id,
                    "reason": "insufficient_warehouse_space"
                }
            })

            return False

    async def _deliver_to_city(self) -> bool:
        """Доставляет груз городу"""
        
        from game.company import Company
        
        # Получаем компанию отправителя для зачисления денег
        sender_company = cast(Company, 
                              await just_db.find_one("companies", 
                                                     id=self.from_company_id, 
                                                     to_class=Company))
        if not sender_company:
            self.status = "failed"
            await self.save_to_base()
            return False

        # Зачисляем деньги компании за проданный товар
        total_payment = self.city_price * self.amount
        await sender_company.add_balance(total_payment)

        # Добавляем экономическое влияние за продажу городу
        await sender_company.set_economic_power(
            self.amount, self.resource_type, 'city_sell'
        )

        # Помечаем логистику как доставленную
        self.status = "delivered"
        await self.save_to_base()

        # Обновляем цену ресурса в сессии
        session = await self.get_session_or_error()
        if session:
            await session.update_item_price(self.resource_type, self.city_price)

        await websocket_manager.broadcast({
            "type": "api-logistics_delivered_to_city",
            "data": {
                "logistics_id": self.id,
                "city_id": self.to_city_id,
                "company_id": self.from_company_id,
                "resource": self.resource_type,
                "amount": self.amount,
                "payment": total_payment
            }
        })
        return True

    async def on_new_turn(self) -> bool:
        """Обрабатывает новый ход для логистики"""

        if self.status == "in_transit":
            return await self.move_next_step()
        
        elif self.status == "waiting_pickup":
            self.waiting_turns += 1

            # Через 1 ход ожидания пытаемся доставить частично
            if self.waiting_turns >= 1:
                return await self._force_partial_delivery()

        elif self.status in ["delivered", "failed"]:
            await self.delete()

        return False
    
    async def _force_partial_delivery(self) -> bool:
        """Принудительная частичная доставка с удалением излишков"""
        from game.company import Company
        
        target_company = cast(Company, 
                              await just_db.find_one(
                                  "companies", 
                                id=self.to_company_id, 
                                to_class=Company))
        if not target_company:
            self.status = "failed"
            await self.save_to_base()
            return False

        free_space = await target_company.get_warehouse_free_size()

        if free_space > 0:
            # Доставляем сколько поместится
            delivered_amount = min(free_space, self.amount)
            await target_company.add_resource(self.resource_type, delivered_amount)

            # Остаток теряется
            lost_amount = self.amount - delivered_amount

            self.status = "delivered"
            await self.save_to_base()

            await websocket_manager.broadcast({
                "type": "api-logistics_partial_delivery",
                "data": {
                    "logistics_id": self.id,
                    "company_id": self.to_company_id,
                    "resource": self.resource_type,
                    "delivered_amount": delivered_amount,
                    "lost_amount": lost_amount
                }
            })

            return True
        else:
            # Весь груз теряется
            self.status = "failed"
            await self.save_to_base()

            await websocket_manager.broadcast({
                "type": "api-logistics_failed",
                "data": {
                    "logistics_id": self.id,
                    "reason": "no_warehouse_space",
                    "lost_amount": self.amount
                }
            })

            return False

    async def pick_up(self, company_id: int) -> bool:
        """Позволяет компании забрать ожидающий груз"""
        if self.status != "waiting_pickup":
            raise ValueError("Груз не ожидает получения")

        if self.to_company_id != company_id:
            raise ValueError("Только компания-получатель может забрать груз")

        from game.company import Company

        company = cast(Company, 
                       await just_db.find_one("companies", 
                                              id=company_id, 
                                              to_class=Company
                                              ))
        if not company:
            raise ValueError("Компания не найдена")

        # Проверяем место на складе
        free_space = await company.get_warehouse_free_size()
        if free_space < self.amount:
            raise ValueError("Недостаточно места на складе")

        # Добавляем ресурсы компании
        await company.add_resource(self.resource_type, self.amount)

        self.status = "delivered"
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-logistics_picked_up",
            "data": {
                "logistics_id": self.id,
                "company_id": company_id,
                "resource": self.resource_type,
                "amount": self.amount
            }
        })

        return True

    async def delete(self) -> bool:
        """Удаляет логистическую доставку"""

        await just_db.delete(self.__tablename__, **{self.__unique_id__: self.id})

        await websocket_manager.broadcast({
            "type": "api-logistics_deleted",
            "data": {
                "logistics_id": self.id
            }
        })
        
        return True

    def to_dict(self) -> dict:
        """Возвращает представление логистики в виде словаря"""

        return {
            "id": self.id,
            "session_id": self.session_id,
            "resource_type": self.resource_type,
            "amount": self.amount,
            "from_company_id": self.from_company_id,
            "to_company_id": self.to_company_id,
            "to_city_id": self.to_city_id,
            "destination_type": self.destination_type,
            "current_position": self.current_position,
            "target_position": self.target_position,
            "status": self.status,
            "distance_left": self.distance_left,
            "waiting_turns": self.waiting_turns,
            "city_price": self.city_price,
            "created_step": self.created_step
        }