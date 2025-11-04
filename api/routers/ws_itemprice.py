from game.item_price import ItemPrice
from modules.websocket_manager import websocket_manager
from modules.check_password import check_password
from modules.ws_hadnler import message_handler
from modules.db import just_db
from game.session import session_manager

@message_handler(
    "get-items-price", 
    doc="Обработчик получения цен товаров в городе. Отправляет ответ на request_id.", 
    datatypes=[
        "session_id: str", 
        "request_id: str"
    ])
async def handle_get_items_price(client_id: str, message: dict):
    """Обработчик получения цен товаров в городе"""

    session_id = message.get("session_id")

    for i in [session_id]:
        if i is None: return {"error": "Missing required fields."}

    session = await session_manager.get_session(session_id=session_id)
    if not session: 
        raise ValueError("Сессия не найдена.")

    try:
        items: list[ItemPrice] = await just_db.find('item_price',
                                to_class=ItemPrice,
                                session_id=session_id
                                ) # type: ignore
        
        item_list = [item.to_dict() for item in items]
        return item_list

    except Exception as e:
        return {"error": str(e)}


@message_handler(
    "get-item-price-by-id", 
    doc="Обработчик получения цены товара по ID. Отправляет ответ на request_id.", 
    datatypes=[
        "session_id: str", 
        "item_id: str",
        "request_id: str"
    ])
async def handle_get_item_price_by_id(client_id: str, message: dict):
    """Обработчик получения цены товара по ID"""

    session_id = message.get("session_id")
    item_id = message.get("item_id")

    for i in [session_id, item_id]:
        if i is None: 
            return {"error": "Missing required fields."}

    session = await session_manager.get_session(session_id=session_id)
    if not session: 
        raise ValueError("Сессия не найдена.")

    try:
        item: ItemPrice = await just_db.find_one('item_price',
                                to_class=ItemPrice,
                                id=item_id,
                                session_id=session_id
                                ) # type: ignore
        
        if not item:
            return {"error": "Товар не найден."}

        return item.to_dict()

    except Exception as e:
        return {"error": str(e)}