from modules.websocket_manager import websocket_manager
from modules.check_password import check_password
from modules.ws_hadnler import message_handler
from modules.db import just_db
from game.exchange import Exchange

@message_handler(
    "get-exchanges", 
    doc="Обработчик получения списка предложений на бирже. Отправляет ответ на request_id.", 
    datatypes=[
        "session_id: Optional[str]",
        "company_id: Optional[int]",
        "sell_resource: Optional[str]",
        "offer_type: Optional[str]",
        "request_id: str"
    ])
async def handle_get_exchanges(client_id: str, 
                               message: dict):
    """Обработчик получения списка предложений на бирже"""

    conditions = {
        "session_id": message.get("session_id"),
        "company_id": message.get("company_id"),
        "sell_resource": message.get("sell_resource"),
        "offer_type": message.get("offer_type")
    }

    # Получаем список предложений из базы данных
    offers = await just_db.find('exchanges',
                         **{k: v for k, v in conditions.items() if v is not None},
                         to_class=Exchange)

    return [offer.to_dict() for offer in offers] # type: ignore

@message_handler(
    "get-exchange", 
    doc="Обработчик получения конкретного предложения на бирже. Отправляет ответ на request_id.", 
    datatypes=[
        "id: int",
        "request_id: str"
    ])
async def handle_get_exchange(client_id: str, message: dict):
    """Обработчик получения конкретного предложения"""

    offer_id = message.get("id")

    if offer_id is None:
        return {"error": "Missing required field: id"}

    # Получаем предложение из базы данных
    offer: Exchange = await just_db.find_one(
        'exchanges', to_class=Exchange,
        id=offer_id
        ) # type: ignore

    if not offer:
        return {"error": "Exchange offer not found."}

    return offer.to_dict() if offer else None

@message_handler(
    "create-exchange-offer", 
    doc="Обработчик создания предложения на бирже. Отправляет ответ на request_id. Требуется пароль для взаимодействия.",
    datatypes=[
        "company_id: int",
        "session_id: str",
        "sell_resource: str",
        "sell_amount_per_trade: int",
        "count_offers: int",
        "offer_type: Literal['money', 'barter']",
        "price: Optional[int] (для offer_type='money')",
        "barter_resource: Optional[str] (для offer_type='barter')",
        "barter_amount: Optional[int] (для offer_type='barter')",

        "password: str",
        "request_id: str"
    ],
    messages=["api-exchange_offer_created (broadcast)"]
)
async def handle_create_exchange_offer(client_id: str, message: dict):
    """Обработчик создания предложения на бирже"""

    company_id = message.get("company_id", 0)
    session_id = message.get("session_id", '')
    sell_resource = message.get("sell_resource", '')
    sell_amount_per_trade = message.get("sell_amount_per_trade", 0)
    count_offers = message.get("count_offers", 0)
    offer_type = message.get("offer_type", "money")
    price = message.get("price", 0)
    barter_resource = message.get("barter_resource", "")
    barter_amount = message.get("barter_amount", 0)
    password = message.get("password", '')

    # Проверяем обязательные поля
    required_fields = [company_id, session_id, sell_resource, 
                      sell_amount_per_trade, count_offers, password]
    if any(field is None for field in required_fields):
        return {"error": "Missing required fields."}

    try:
        check_password(password)

        exchange = await Exchange().create(
            company_id=company_id,
            session_id=session_id,
            sell_resource=sell_resource,
            sell_amount_per_trade=sell_amount_per_trade,
            count_offers=count_offers,
            offer_type=offer_type,
            price=price,
            barter_resource=barter_resource,
            barter_amount=barter_amount
        )

    except ValueError as e:
        return {"error": str(e)}

    return {
        'session_id': exchange.session_id,
        'offer': exchange.to_dict()
    }

@message_handler(
    "update-exchange-offer", 
    doc="Обработчик обновления предложения на бирже. Требуется пароль для взаимодействия.",
    datatypes=[
        "offer_id: int",
        "sell_amount_per_trade: Optional[int]",
        "price: Optional[int]",
        "barter_amount: Optional[int]",

        "password: str",
        "request_id: str"
    ],
    messages=["api-exchange_offer_updated (broadcast)"]
)
async def handle_update_exchange_offer(
    client_id: str, message: dict):
    """Обработчик обновления предложения на бирже"""

    offer_id = message.get("offer_id")
    password = message.get("password")
    sell_amount_per_trade = message.get("sell_amount_per_trade")
    price = message.get("price")
    barter_amount = message.get("barter_amount")

    if offer_id is None or password is None:
        return {"error": "Missing required fields: offer_id, password"}

    try:
        check_password(password)

        exchange = await Exchange(id=offer_id).reupdate()
        if not exchange:
            raise ValueError("Обменное предложение не найдено.")

        old_offer = exchange.to_dict()

        await exchange.update_offer(
            sell_amount_per_trade=sell_amount_per_trade,
            price=price,
            barter_amount=barter_amount
        )

        new_offer = exchange.to_dict()

    except ValueError as e:
        return {"error": str(e)}

    return {
        "session_id": exchange.session_id,
        "new": new_offer,
        "old": old_offer
    }

@message_handler(
    "cancel-exchange-offer", 
    doc="Обработчик отмены предложения на бирже (возврат товара). Требуется пароль для взаимодействия.",
    datatypes=[
        "offer_id: int",
        "password: str",
        "request_id: str"
    ],
    messages=["api-exchange_offer_cancelled (broadcast)"]
)
async def handle_cancel_exchange_offer(
    client_id: str, message: dict):
    """Обработчик отмены предложения на бирже"""

    offer_id = message.get("offer_id")
    password = message.get("password")

    if offer_id is None or password is None:
        return {"error": "Missing required fields: offer_id, password"}

    try:
        check_password(password)

        exchange = await Exchange(id=offer_id).reupdate()
        if not exchange:
            raise ValueError("Обменное предложение не найдено.")

        session_id = exchange.session_id
        company_id = exchange.company_id

        await exchange.cancel_offer()

    except ValueError as e:
        return {"error": str(e)}

    return {
        "session_id": session_id,
        "offer_id": offer_id,
        "company_id": company_id,
        "status": "cancelled"
    }

@message_handler(
    "buy-exchange-offer", 
    doc="Обработчик покупки товара по предложению на бирже. Требуется пароль для взаимодействия.",
    datatypes=[
        "offer_id: int",
        "buyer_company_id: int",
        "quantity: int",  # количество сделок
        "password: str",
        "request_id: str"
    ],
    messages=["api-exchange_trade_completed (broadcast)"]
)
async def handle_buy_exchange_offer(
    client_id: str, message: dict):
    """Обработчик покупки товара по предложению"""

    offer_id = message.get("offer_id", 0)
    buyer_company_id = message.get("buyer_company_id", 0)
    quantity = message.get("quantity", 1)
    password = message.get("password", '')

    required_fields = [offer_id, buyer_company_id, password]
    if any(field is None for field in required_fields):
        return {"error": "Missing required fields: offer_id, buyer_company_id, password"}

    try:
        check_password(password)

        exchange = await Exchange(id=offer_id).reupdate()
        if not exchange:
            raise ValueError("Обменное предложение не найдено.")

        old_stock = exchange.total_stock
        
        await exchange.buy(buyer_company_id=buyer_company_id, quantity=quantity)

        # Если сделка прошла успешно
        result = {
            "session_id": exchange.session_id,
            "offer_id": offer_id,
            "buyer_company_id": buyer_company_id,
            "seller_company_id": exchange.company_id,
            "sell_resource": exchange.sell_resource,
            "sell_amount": exchange.sell_amount_per_trade * quantity,
            "offer_type": exchange.offer_type,
            "quantity": quantity,
            "old_stock": old_stock,
            "new_stock": exchange.total_stock,
            "status": "completed"
        }

        if exchange.offer_type == 'money':
            result["total_price"] = exchange.price * quantity
        elif exchange.offer_type == 'barter':
            result["barter_resource"] = exchange.barter_resource
            result["barter_amount"] = exchange.barter_amount * quantity

    except ValueError as e:
        return {"error": str(e)}

    return result