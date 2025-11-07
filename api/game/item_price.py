from typing import cast
from game.session import SessionObject
from global_modules.models.cells import Cells
from global_modules.db.baseclass import BaseClass
from modules.db import just_db
from global_modules.load_config import ALL_CONFIGS, Resources, Improvements, Settings, Capital, Reputation
from modules.utils import *
from modules.websocket_manager import websocket_manager

RESOURCES: Resources = ALL_CONFIGS["resources"]
CELLS: Cells = ALL_CONFIGS['cells']
IMPROVEMENTS: Improvements = ALL_CONFIGS['improvements']
SETTINGS: Settings = ALL_CONFIGS['settings']
CAPITAL: Capital = ALL_CONFIGS['capital']
REPUTATION: Reputation = ALL_CONFIGS['reputation']

RESET = 100
ON_EVERY = 2

class ItemPrice(BaseClass, SessionObject):

    __tablename__ = "item_price"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: str = ""):
        self.id: str = id
        self.session_id: str = ""
        self.prices: list[int] = []
        self.current_price: int = 0
        self.material_based_price: int = 0

        self.popularity: int = 0  # Как часто покупают этот товар
        self.popularity_on_step: int = 0  # Популярность за текущий шаг

        self.price_on_last_step: int = 0  # Цена на последнем шаге


    async def add_popularity(self, amount: int = 1):
        self.popularity += amount
        self.popularity_on_step += amount

        await self.save_to_base()
        return True

    async def create(self, session_id: str, item_id: str) -> 'ItemPrice':
        self.id = item_id
        self.session_id = session_id

        # Попытка найти в базе
        data = await just_db.find_one(self.__tablename__, id=item_id, session_id=session_id)
        if data:
            self.load_from_base(data)
            return self

        self.current_price = RESOURCES.resources[item_id].basePrice
        self.prices = [self.current_price]
        self.material_based_price = await self.calculate_material_price()

        await self.insert()
        return self

    async def delete(self):
        await just_db.delete(self.__tablename__, id=self.id, session_id=self.session_id)
        return True

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "prices": self.prices,
            "current_price": self.current_price,
            "material_based_price": self.material_based_price,
            "popularity": self.popularity,
            "popularity_on_step": self.popularity_on_step,
            "price_on_last_step": self.price_on_last_step
        }

    async def calculate_material_price(self) -> int:
        resource = RESOURCES.resources.get(self.id)
        if not resource or not resource.production:
            return 0

        total_cost = 0
        for mat_id, qty in resource.production.materials.items():
            mat_price_obj = await just_db.find_one("item_price", 
                                        id=mat_id,
                                        session_id=self.session_id,
                                        to_class=ItemPrice
                                        )
            if mat_price_obj:
                mat_price = mat_price_obj.get_effective_price()
            else:
                # Если нет в базе, использовать basePrice
                mat_resource = RESOURCES.resources.get(mat_id)
                mat_price = mat_resource.basePrice if mat_resource else 0
            total_cost += mat_price * qty

        # Цена за единицу выхода
        return int(total_cost / resource.production.output)

    def get_effective_price(self) -> int:
        if self.material_based_price > 0 and self.prices:
            avg_price = sum(self.prices) / len(self.prices)

            if self.material_based_price > avg_price:
                return self.material_based_price

        return self.current_price

    async def add_price(self, new_price: int):
        self.prices.append(new_price)

        if len(self.prices) % ON_EVERY == 0:
            base_price = RESOURCES.resources[self.id].basePrice
            self.prices.append(base_price)

        if len(self.prices) > RESET:
            # Вычислить среднее из REST элементов и начать заново
            avg_price = int(sum(self.prices) / len(self.prices))
            self.prices = [avg_price]

        self.current_price = int(
            sum(self.prices) / len(self.prices)
            )

        self.material_based_price = await self.calculate_material_price()
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-item_price_updated",
            "data": {
                "item_id": self.id,
                "session_id": self.session_id,
                "price": self.get_effective_price(),
            }
        })

    async def on_new_game_step(self):
        self.popularity_on_step = 0
        self.price_on_last_step = self.get_effective_price()

        await self.save_to_base()
        return True