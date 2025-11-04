
from typing import Optional, Literal
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

class Exchange(BaseClass, SessionObject):
    """ Предложение на бирже

        Типы сделок:
        - За монеты (offer_type='money'): X товара типа Z на Y монет
        - Бартер (offer_type='barter'): X товара типа Z на Y продукта J
    """

    __tablename__ = "exchanges"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id
        
        self.company_id: int = 0  # Компания-продавец
        self.session_id: str = ""  # Сессия, в которой создано предложение
        
        # Что продаём
        self.sell_resource: str = ""  # Тип ресурса для продажи
        self.sell_amount_per_trade: int = 0  # Количество за одну сделку
        self.total_stock: int = 0  # Общий запас товара
        
        # Что хотим получить
        self.offer_type: Literal['money', 'barter'] = 'money'
        self.price: int = 0  # Цена за один комплект (если offer_type='money')

        self.barter_resource: str = ""  # Ресурс для обмена (если offer_type='barter')
        self.barter_amount: int = 0  # Количество ресурса для обмена (если offer_type='barter')

        self.created_at: int = 0  # Время создания (игровой ход)

    async def create(self, 
               company_id: int, session_id: str, 
               sell_resource: str, sell_amount_per_trade: int, count_offers: int,
               offer_type: Literal['money', 'barter'] = 'money',
               price: int = 0, barter_resource: str = "", barter_amount: int = 0
               ):
        """ Создание нового предложения на бирже

        Args:
            company_id: ID компании-продавца
            session_id: ID сессии
            sell_resource: Тип ресурса для продажи
            sell_amount_per_trade: Количество за одну сделку
            count_offers: Количество сделок
            offer_type: Тип сделки ('money' или 'barter')
            price: Цена за комплект (для money)
            barter_resource: Ресурс для обмена (для barter)
            barter_amount: Количество ресурса для обмена (для barter)
        """
        from game.company import Company

        total_stock = count_offers * sell_amount_per_trade

        # Валидация
        if sell_amount_per_trade <= 0 or total_stock <= 0:
            raise ValueError("Суммы должны быть положительными целыми числами.")

        if RESOURCES.get_resource(sell_resource) is None:
            raise ValueError(f"Ресурс '{sell_resource}' не существует.")

        company = await Company(id=company_id).reupdate()
        if not company:
            raise ValueError("Компания не найдена.")

        # Проверяем, есть ли у компании достаточно товара
        if company.warehouses.get(sell_resource, 0) < total_stock:
            raise ValueError(f"У компании недостаточно ресурса {RESOURCES.get_resource(sell_resource).emoji} {RESOURCES.get_resource(sell_resource).label} на складе.")
        
        # Валидация типа сделки
        if offer_type == 'money':
            if price <= 0:
                raise ValueError("Цена должна быть положительным целым числом.")
            from game.item_price import ItemPrice

            item_price = await ItemPrice().create(
                session_id=self.session_id,
                item_id=sell_resource
            )
            average_price = item_price.get_effective_price()

            if abs(price - average_price) / average_price > 0.5:
                raise ValueError(f"Цена отличается от средней более чем на 50%. Средняя цена: {average_price}, выставленная цена: {price}")

        elif offer_type == 'barter':
            if not barter_resource or barter_amount <= 0:
                raise ValueError("Бартерный ресурс и количество должны быть указаны.")
            if RESOURCES.get_resource(barter_resource) is None:
                raise ValueError(f"Бартерный ресурс '{barter_resource}' не существует.")
        else:
            raise ValueError("Недействительный тип предложения.")

        self.session_id = session_id
        session = await self.get_session_or_error()

        # Создаём предложение
        self.company_id = company_id
        self.sell_resource = sell_resource
        self.sell_amount_per_trade = sell_amount_per_trade
        self.total_stock = total_stock
        self.offer_type = offer_type
        self.price = price
        self.barter_resource = barter_resource
        self.barter_amount = barter_amount
        self.created_at = session.step

        await self.insert()

        # Списываем товар со склада компании только после успешного создания
        try:
            await company.remove_resource(sell_resource, total_stock)
        except ValueError as e:
            # Если не удалось списать товар, удаляем предложение
            await self.delete()
            raise ValueError(f"Не удалось зарезервировать ресурсы: {str(e)}")

        await websocket_manager.broadcast({
            "type": "api-exchange_offer_created",
            "data": {
                "session_id": self.session_id,
                "offer": self.to_dict()
            }
        })

        return self

    async def update_offer(self, 
                    sell_amount_per_trade: Optional[int] = None,
                    price: Optional[int] = None, 
                    barter_amount: Optional[int] = None
                    ):
        """ Изменение параметров предложения

        Args:
            sell_amount_per_trade: Новое количество за одну сделку
            price: Новая цена (для money)
            barter_amount: Новое количество для обмена (для barter)
        """

        if sell_amount_per_trade is not None:
            if sell_amount_per_trade <= 0:
                raise ValueError("Количество для продажи должно быть положительным.")

            if sell_amount_per_trade > self.total_stock:
                raise ValueError("Количество для продажи не может превышать общий запас.")
            self.sell_amount_per_trade = sell_amount_per_trade

        if self.offer_type == 'money' and price is not None:
            if price <= 0:
                raise ValueError("Цена должна быть положительной.")

            from game.item_price import ItemPrice

            item_price = await ItemPrice().create(
                session_id=self.session_id,
                item_id=self.sell_resource
            )
            average_price = item_price.get_effective_price()

            if abs(price - average_price) / average_price > 0.5:
                raise ValueError(f"Цена отличается от средней более чем на 50%. Средняя цена: {average_price}, выставленная цена: {price}")

            self.price = price

        if self.offer_type == \
                'barter' and barter_amount is not None:
            if barter_amount <= 0:
                raise ValueError("Количество для бартера должно быть положительным.")
            self.barter_amount = barter_amount

        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-exchange_offer_updated",
            "data": {
                "session_id": self.session_id,
                "offer_id": self.id,
                "offer": self.to_dict()
            }
        })

        return self

    async def cancel_offer(self):
        """ Отмена предложения (возврат товара компании) """
        from game.company import Company

        company = await Company(id=self.company_id).reupdate()
        if not company:
            raise ValueError("Компания не найдена.")

        # Проверяем, есть ли место на складе для возврата товара
        current_resources = company.get_resources_amount()
        max_capacity = await company.get_max_warehouse_size()

        if current_resources + self.total_stock > max_capacity:
            raise ValueError(f"Недостаточно места на складе для возврата ресурсов. Требуется: {self.total_stock}, доступно: {max_capacity - current_resources}")

        # Возвращаем оставшийся товар на склад компании
        await company.add_resource(self.sell_resource, self.total_stock)

        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-exchange_offer_cancelled",
            "data": {
                "session_id": self.session_id,
                "offer_id": self.id,
                "company_id": self.company_id
            }
        })
        
        await self.delete()

    async def buy(self, 
                  buyer_company_id: int, 
                  quantity: int = 1
                  ):
        """ Покупка товара по предложению
        
        Args:
            buyer_company_id: ID компании-покупателя
            quantity: Количество сделок (по умолчанию 1)
        """
        from game.company import Company
        from game.logistics import Logistics
        from game.item_price import ItemPrice

        if quantity <= 0:
            raise ValueError("Количество должно быть положительным.")

        if buyer_company_id == self.company_id:
            raise ValueError("Нельзя покупать у своего собственного предложения.")

        buyer = await Company(id=buyer_company_id).reupdate()
        seller = await Company(id=self.company_id).reupdate()

        if not buyer or not seller:
            raise ValueError("Компания покупателя или продавца не найдена.")

        if buyer.session_id != self.session_id:
            raise ValueError("Покупатель должен быть в той же сессии.")

        session = await self.get_session_or_error()

        # Рассчитываем количество товара
        total_sell_amount = self.sell_amount_per_trade * quantity

        if total_sell_amount > self.total_stock:
            raise ValueError(f"Недостаточно запасов. Доступно: {self.total_stock}, запрошено: {total_sell_amount}")

        # Переменная для хранения цены за единицу товара (для обновления истории цен)
        unit_price = 0

        # Проверяем возможность сделки
        if self.offer_type == 'money':
            total_price = self.price * quantity
            unit_price = self.price // self.sell_amount_per_trade  # Цена за единицу товара

            if buyer.balance < total_price:
                raise ValueError(f"Недостаточно денег. Требуется: {total_price}, доступно: {buyer.balance}")

            # Выполняем сделку за монеты
            buyer.balance -= total_price
            seller.balance += total_price

            await buyer.save_to_base()
            await seller.save_to_base()

        elif self.offer_type == 'barter':
            total_barter_amount = self.barter_amount * quantity

            if buyer.warehouses.get(self.barter_resource, 0) < total_barter_amount:
                raise ValueError(f"Недостаточно '{self.barter_resource}' для бартера. Требуется: {total_barter_amount}")

            # # Для бартера вычисляем условную цену на основе текущих цен предметов
            # barter_resource_price = await session.get_item_price(self.barter_resource)
            # unit_price = (barter_resource_price * self.barter_amount) // self.sell_amount_per_trade
            unit_price = 0  # Для бартерных сделок цена за единицу не учитывается

            await Logistics().create(
                from_company_id=buyer.id,
                to_company_id=seller.id,
                resource_type=self.barter_resource,
                amount=total_barter_amount,
                session_id=self.session_id
            )

        await Logistics().create(
            sender_no_delete=True, # Потому что товар уже списан с продавца при создании предложения
            from_company_id=seller.id,
            to_company_id=buyer.id,
            resource_type=self.sell_resource,
            amount=total_sell_amount,
            session_id=self.session_id
        )

        item_price = await ItemPrice().create(
            session_id=self.session_id,
            item_id=self.sell_resource
        )
        await item_price.add_popularity(quantity)

        if unit_price > 0:
            await session.update_item_price(self.sell_resource, unit_price)

        await seller.set_economic_power(
            total_sell_amount, self.sell_resource, 'exchange'
        )

        # Обновляем запас предложения
        self.total_stock -= total_sell_amount

        if self.total_stock == 0:
            await self.delete()
        else:
            await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-exchange_trade_completed",
            "data": {
                "session_id": self.session_id,
                "offer_id": self.id,
                "seller_id": self.company_id,
                "buyer_id": buyer_company_id,
                "sell_resource": self.sell_resource,
                "sell_amount": total_sell_amount,
                "offer_type": self.offer_type,
                "price": self.price * quantity if self.offer_type == 'money' else None,
                "barter_resource": self.barter_resource if self.offer_type == 'barter' else None,
                "barter_amount": self.barter_amount * quantity if self.offer_type == 'barter' else None,
                "remaining_stock": self.total_stock,
                "unit_price": unit_price  # Добавляем цену за единицу в уведомление
            }
        }) 

        return self

    def to_dict(self) -> dict:
        """ Преобразование предложения в словарь """
        return {
            "id": self.id,
            "company_id": self.company_id,
            "session_id": self.session_id,
            "sell_resource": self.sell_resource,
            "sell_amount_per_trade": self.sell_amount_per_trade,
            "total_stock": self.total_stock,
            "offer_type": self.offer_type,
            "price": self.price,
            "barter_resource": self.barter_resource,
            "barter_amount": self.barter_amount,
            "created_at": self.created_at
        }

    async def delete(self):
        """ Удаление предложения из базы данных """
        await just_db.delete(self.__tablename__, **{self.__unique_id__: self.id})

        await websocket_manager.broadcast({
            "type": "api-exchange_offer_deleted",
            "data": {
                "session_id": self.session_id,
                "offer_id": self.id
            }
        })

        return True