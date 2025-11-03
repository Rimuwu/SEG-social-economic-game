from game.citie import Citie
from modules.websocket_manager import websocket_manager
from modules.check_password import check_password
from modules.ws_hadnler import message_handler
from modules.db import just_db

@message_handler(
    "get-cities", 
    doc="Обработчик получения списка городов. Отправляет ответ на request_id", 
    datatypes=[
        "session_id: Optional[str]", 
        "request_id: str"
        ])
async def handle_get_cities(client_id: str, message: dict):
    """Обработчик получения списка городов"""

    conditions = {
        "session_id": message.get("session_id")
    }

    # Получаем список городов из базы данных
    cities = await just_db.find('cities',
                          to_class=Citie,
                         **{k: v for k, v in conditions.items() if v is not None})

    return [city.to_dict() for city in cities]

@message_handler(
    "get-city", 
    doc="Обработчик получения города. Отправляет ответ на request_id.", 
    datatypes=[
        "id: Optional[int]", 
        "session_id: Optional[str]",
        "cell_position: Optional[str]",
        "branch: Optional[str]",
        "request_id: str"
        ])
async def handle_get_city(client_id: str, message: dict):
    """Обработчик получения города"""

    conditions = {
        "id": message.get("id"),
        "session_id": message.get("session_id"),
        "cell_position": message.get("cell_position"),
        "branch": message.get("branch")
    }

    # Получаем город из базы данных
    city = await just_db.find_one('cities', to_class=Citie,
                         **{k: v for k, v in conditions.items() if v is not None})

    if not city:
        return {"error": "City not found"}

    return city.to_dict() if city else None

@message_handler(
    "sell-to-city", 
    doc="Обработчик продажи ресурса городу. Отправляет ответ на request_id.",
    datatypes=[
        "city_id: int",
        "company_id: int",
        "resource_id: str",
        "amount: int",
        "password: str",
        "request_id: str"
    ],
    messages=["api-city-trade (broadcast)"]
)
async def handle_sell_to_city(client_id: str, message: dict):
    """Обработчик продажи ресурса городу"""

    password = message.get("password")
    city_id = message.get("city_id")
    company_id = message.get("company_id")
    resource_id = message.get("resource_id")
    amount = message.get("amount")

    for i in [password, city_id, company_id, resource_id, amount]:
        if i is None:
            return {"error": "Missing required fields"}

    try:
        check_password(password)
        
        city = await Citie(city_id).reupdate()
        if not city:
            raise ValueError("Город не найден.")

        result = await city.sell_resource(company_id, 
                                    resource_id, 
                                    amount
                )
        
        return result

    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "get-city-demands", 
    doc="Обработчик получения спроса города на товары. Отправляет ответ на request_id.", 
    datatypes=[
        "city_id: int", 
        "request_id: str"
        ])
async def handle_get_city_demands(client_id: str, message: dict):
    """Обработчик получения спроса города"""

    city_id = message.get("city_id")
    
    if city_id is None:
        return {"error": "Missing city_id"}

    city = await just_db.find_one(
        'cities', to_class=Citie, id=city_id)

    if not city:
        return {"error": "City not found"}

    return {
        "city_id": city.id,
        "demands": city.demands,
        "branch": city.branch
    }
