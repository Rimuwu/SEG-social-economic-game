import copy
import random
from typing import Optional
from game.statistic import Statistic
from game.session import SessionObject
from global_modules.models.cells import Cells
from global_modules.db.baseclass import BaseClass
from modules.db import just_db
from global_modules.load_config import ALL_CONFIGS, Resources, Improvements, Settings, Capital, Reputation
from modules.function_way import determine_city_branch
from modules.websocket_manager import websocket_manager
from modules.logs import game_logger

RESOURCES: Resources = ALL_CONFIGS["resources"]
CELLS: Cells = ALL_CONFIGS['cells']
IMPROVEMENTS: Improvements = ALL_CONFIGS['improvements']
SETTINGS: Settings = ALL_CONFIGS['settings']
CAPITAL: Capital = ALL_CONFIGS['capital']
REPUTATION: Reputation = ALL_CONFIGS['reputation']

NAMES = [
    "Эльдория",
    "Мистия",
    "Дракония",
    "Аркания",
    "Фэнтария",
    "Неотрон",
    "Киберия",
    "Нексус",
    "Виртус",
    "Квантия",
    "Галаксия",
    "Технория",
    "Андроид",
    "Лазерия",
    "Синтия",
    "Космония",
    "Роботия",
    "Футурия",
    "Нанобург",
    "Гиперон"
]

class Citie(BaseClass, SessionObject):

    __tablename__ = "cities"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id
        self.session_id: str = ""
        self.cell_position: str = ""  # "x.y"
        self.branch: str = ""  # Приоритетная ветка: 'oil', 'metal', 'wood', 'cotton'

        self.name: str = ""

        # Спрос на товары: {resource_id: {'amount': int, 'price': int}}
        self.demands: dict = {}
        self.demands_save: dict = {}

    async def create(self, 
                     session_id: str, 
                     x: int, y: int, 
                     name: Optional[str] = None):
        """ Создание нового города
        
        Args:
            session_id: ID сессии
            x: координата X
            y: координата Y
        """

        self.session_id = session_id
        session = await self.get_session_or_error()

        self.cell_position = f"{x}.{y}"

        # Определяем приоритетную ветку на основе соседних клеток
        self.branch = await determine_city_branch(
            x, y, session_id, session.cells, session.map_size
        )

        self.name = name if name else random.choice(NAMES)

        # Инициализируем спрос
        await self._update_demands(session)

        await self.insert()
        await websocket_manager.broadcast({
            "type": "api-city-create",
            "data": {
                "city": self.to_dict()
            }
        })

        return self

    async def _update_demands(self, session=None):
        """Обновляет спрос города на товары
        
        Args:
            session: объект Session (опционально, для оптимизации)
        """
        if session is None:
            session = await self.get_session_or_error()

        if not session:
            return

        # Получаем количество пользователей в сессии (минимум 1 для расчётов)
        users_count = max(len(await session.users), 1)

        # Рассчитываем модификаторы спроса на основе разности между сохраненным и текущим спросом
        demand_modifiers = {}
        
        for resource_id in self.demands_save:
            old_amount = self.demands_save.get(resource_id, {}).get('amount', 0)
            current_amount = self.demands.get(resource_id, {}).get('amount', 0)

            if old_amount > 0:
                modifier = round(current_amount / old_amount, 2)
            else:
                modifier = 1.0
            demand_modifiers[resource_id] = max(modifier, 0.1)

        # Очищаем старый спрос
        self.demands = {}

        # Получаем все ресурсы, которые не являются сырьем
        for resource_id, resource in RESOURCES.resources.items():
            if not resource.raw:
                # Базовое количество: massModifier определяет масштаб
                # Для товаров с massModifier=100 будет ~100 единиц на игрока
                base_amount = resource.massModifier * users_count
                
                # Применяем модификатор, основанный на продажах прошлого хода
                previous_demand_modifier = demand_modifiers.get(resource_id, 1.0)
                base_amount *= previous_demand_modifier

                mod_price = session.get_event_effects().get(
                    'increase_price', {}
                ).get(resource_id, 1.0)
                mod_count = session.get_event_effects().get(
                    'increase_demand', {}
                ).get(resource_id, 1.0)

                # Модификатор для приоритетной ветки (увеличиваем спрос на 50%)
                branch_modifier = 1.5 if resource.branch == self.branch else 1.0

                # Применяем модификатор продаж прошлого хода
                previous_demand_modifier = demand_modifiers.get(resource_id, 1.0)
                if previous_demand_modifier != 1.0:
                    rand_demand = random.uniform(previous_demand_modifier, 1.0)
                else:
                    rand_demand = random.uniform(0.8, 1.5)

                # Рандомизация ±60%
                amount_variation = random.uniform(0.4, 1.6)

                # Рассчитываем финальное количество
                amount = int(base_amount * branch_modifier * rand_demand * amount_variation)

                # Ограничение: минимум зависит от massModifier
                min_min = 0
                branch_modifier = 1.0
                if resource.branch == self.branch:
                    min_min = random.randint(0, 1)
                    branch_modifier = 1.5

                min_amount = random.randint(min_min, max(int(resource.massModifier * 0.5), 2))
                max_amount = int(resource.massModifier * users_count * 2 * mod_count * branch_modifier)
                amount = random.randint(min_amount, max(min_amount, max_amount, amount))


                # Цена с рандомизацией ±20%
                current_item_price = await session.get_item_price(resource_id)
                price_variation = random.uniform(0.8, 1.2)
                price = int(current_item_price * price_variation * mod_price)

                # Бонус к цене для приоритетной ветки (+50%)
                if resource.branch == self.branch:
                    price = int(price * 1.5)

                # Минимальная цена не может быть меньше базовой
                # price = max(resource.basePrice, price)
                
                self.demands[resource_id] = {
                    'amount': amount,
                    'price': price
                }

        # Обновляем demands_save для следующего хода (сохраняем только что созданный спрос)
        self.demands_save = copy.deepcopy(self.demands)

    async def on_new_game_stage(self):
        """Вызывается при начале нового игрового хода"""
        session = await self.get_session_or_error()
        
        # Обновляем спрос на товары
        await self._update_demands(session)
        
        await self.save_to_base()
        
        await websocket_manager.broadcast({
            "type": "api-city-update-demands",
            "data": {
                "city_id": self.id,
                "session_id": self.session_id,
                "demands": self.demands
            }
        })

    async def sell_resource(self, company_id: int, 
                      resource_id: str, amount: int):
        """Продает ресурс городу
        
        Args:
            company_id: ID компании
            resource_id: ID ресурса
            amount: количество для продажи

        Returns:
            dict с результатом операции
        """
        from game.logistics import Logistics
        from game.item_price import ItemPrice

        await Logistics().create(
            session_id=self.session_id,
            resource_type=resource_id,
            amount=amount,
            from_company_id=company_id,
            to_city_id=self.id
        )
        
        # Уменьшаем спрос
        self.demands[resource_id]['amount'] -= amount
        if self.demands[resource_id]['amount'] <= 0:
            del self.demands[resource_id]

        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-city-trade",
            "data": {
                "city_id": self.id,
                "company_id": company_id,
                "resource_id": resource_id,
                "amount": amount
            }
        })

        try:
            item_price = await ItemPrice().create(
                session_id=self.session_id,
                item_id=resource_id
            )
            await item_price.add_popularity(amount)
        except Exception as e:
            game_logger.error(f"Ошибка при увеличении популярности товара {resource_id}: {e}")

        st = await Statistic.get_latest_by_company(
            session_id=self.session_id,
            company_id=company_id
        )
        if st:
            session = await self.get_session_or_error()
            await Statistic.update_me(
                company_id=company_id,
                session_id=self.session_id,
                step=session.step,
                total_products_produced=amount
            )

        return True

    def get_position(self) -> tuple[int, int]:
        """Возвращает координаты города"""
        if not self.cell_position:
            return (0, 0)
        x, y = self.cell_position.split('.')
        return (int(x), int(y))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "cell_position": self.cell_position,
            "branch": self.branch,
            "demands": self.demands,
            
            "name": self.name
        }

    async def delete(self):
        """ Удаление города
        """
        await just_db.delete(self.__tablename__, id=self.id, session_id=self.session_id)

        await websocket_manager.broadcast({
            "type": "api-city-delete",
            "data": {
                "city_id": self.id,
                "session_id": self.session_id
            }
        })

        return True