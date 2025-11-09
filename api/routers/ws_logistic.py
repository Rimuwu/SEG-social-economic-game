from game.logistics import Logistics
from modules.websocket_manager import websocket_manager
from modules.check_password import check_password
from modules.ws_hadnler import message_handler
from modules.db import just_db
from typing import cast

@message_handler(
    "get-logistics", 
    doc="Обработчик получения списка логистик. Отправляет ответ на request_id", 
    datatypes=[
        "session_id: Optional[str]", 
        "from_company_id: Optional[int]",
        "to_company_id: Optional[int]",
        "to_city_id: Optional[int]",
        "logistics_id: Optional[int]",
        "destination_type: Literal['company', 'city']",
        "status: Literal['in_transit', 'waiting_pickup', 'delivered', 'failed']",

        "request_id: str"
        ])
async def handle_get_logistics(client_id: str, message: dict):
    """Обработчик получения списка логистик"""

    conditions = {
        "from_company_id": message.get("from_company_id"),
        "to_company_id": message.get("to_company_id"),
        "to_city_id": message.get("to_city_id"),
        "session_id": message.get("session_id"),
        "id": message.get("logistics_id"),
        "destination_type": message.get("destination_type"),
        "status": message.get("status"),
    }


    try:
        logistics_list: list[Logistics] = await just_db.find(
            'logistics',
            to_class=Logistics,
            **{k: v for k, v in conditions.items() if v is not None}) # type: ignore

        return [logistics.to_dict() for logistics in logistics_list]

    except Exception as e:
        return {"error": str(e)}

@message_handler(
    "logistics-pickup", 
    doc="Обработчик получения ожидающего груза компанией. Требуется пароль для взаимодействия.",
    datatypes=[
        "logistics_id: int",
        "company_id: int",
        "password: str",
        "request_id: str"
    ],
    messages=["api-logistics_picked_up (broadcast)"]
)
async def handle_logistics_pickup(client_id: str, message: dict):
    """Обработчик получения ожидающего груза"""

    logistics_id = message.get("logistics_id")
    company_id = message.get("company_id")
    password = message.get("password")

    # Проверяем наличие обязательных полей
    if logistics_id is None:
        return {"error": "Отсутствует обязательное поле: logistics_id"}
    if company_id is None:
        return {"error": "Отсутствует обязательное поле: company_id"}
    if password is None:
        return {"error": "Отсутствует обязательное поле: password"}

    try:
        # Проверяем пароль
        check_password(password)

        # Получаем логистику
        logistics = cast(Logistics, Logistics(logistics_id).reupdate())
        if not logistics:
            raise ValueError("Логистика не найдена")

        # Выполняем получение груза
        success = logistics.pick_up(company_id)
        
        if success:
            return {
                "success": True,
                "message": "Груз успешно получен",
                "logistics": logistics.to_dict()
            }
        else:
            return {"error": "Не удалось получить груз"}

    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Произошла ошибка: {str(e)}"}
