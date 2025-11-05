
from modules.ws_hadnler import message_handler
from modules.db import just_db
from game.factory import Factory
from modules.check_password import check_password

@message_handler(
    "get-factories", 
    doc="Обработчик получения списка всех фабрик. Отправляет ответ на request_id", 
    datatypes=[
        "company_id: Optional[int]",
        "complectation: Optional[str]",
        "produce: Optional[bool]",
        "is_auto: Optional[bool]",

        "request_id: str"
        ])
async def handle_get_factories(client_id: str, message: dict):
    """Обработчик получения списка фабрик"""

    conditions = {
        "company_id": message.get("company_id"),
        "complectation": message.get("complectation"),
        "produce": message.get("produce"),
        "is_auto": message.get("is_auto"),
    }

    # Получаем список фабрик из базы данных
    factories = await just_db.find('factories',
                             to_class=Factory,
                         **{k: v for k, v in conditions.items() if v is not None})

    return [await factory.to_dict() for factory in factories]

@message_handler(
    "get-factory", 
    doc="Обработчик получения информации о фабрике. Отправляет ответ на request_id.", 
    datatypes=[
        "factory_id: int", 
        "request_id: str"
        ])
async def handle_get_factory(client_id: str, message: dict):
    """Обработчик получения информации о фабрике"""

    factory_id = message.get("factory_id")
    
    if factory_id is None:
        return {"error": "factory_id is required"}

    factory = await Factory(factory_id).reupdate()
    if not factory:
        raise ValueError("Завод не найден.")
    
    return await factory.to_dict() if factory else None


@message_handler(
    "factory-recomplectation", 
    doc="Обработчик перекомплектации фабрики. Требуется пароль для взаимодействия.",
    datatypes=[
        "factory_id: int",
        "new_complectation: str",
        "password: str"
    ],
    messages=["api-factory-start-complectation (broadcast)"]
)
async def handle_factory_recomplectation(client_id: str, message: dict):
    """Обработчик перекомплектации фабрики"""

    factory_id = message.get("factory_id")
    new_complectation = message.get("new_complectation")
    password = message.get("password", "")

    if factory_id is None:
        return {"error": "factory_id is required"}
    
    if not new_complectation:
        return {"error": "new_complectation is required"}

    try:
        check_password(password)
        
        factory = await Factory(factory_id).reupdate()
        if not factory:
            raise ValueError("Завод не найден.")
        
        result = await factory.pere_complete(new_complectation)
        
        return {"success": result}
    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "factory-set-produce", 
    doc="Обработчик установки статуса производства фабрики.",
    datatypes=[
        "factory_id: int",
        "produce: bool"
    ]
)
async def handle_factory_set_produce(client_id: str, message: dict):
    """Обработчик установки статуса производства фабрики"""

    factory_id = message.get("factory_id")
    produce = message.get("produce")

    if factory_id is None:
        return {"error": "factory_id is required"}
    
    if produce is None:
        return {"error": "produce is required"}

    try:
        factory = await Factory(factory_id).reupdate()
        if not factory:
            raise ValueError("Завод не найден.")
        
        await factory.set_produce(produce)

        return {"success": True}
    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "factory-set-auto", 
    doc="Обработчик установки статуса автоматического производства фабрики.",
    datatypes=[
        "factory_id: int",
        "is_auto: bool"
    ]
)
async def handle_factory_set_auto(client_id: str, message: dict):
    """Обработчик установки статуса автоматического производства фабрики"""

    factory_id = message.get("factory_id")
    is_auto = message.get("is_auto")

    if factory_id is None:
        return {"error": "factory_id is required"}
    
    if is_auto is None:
        return {"error": "is_auto is required"}

    try:
        factory = await Factory(factory_id).reupdate()
        if not factory:
            raise ValueError("Завод не найден.")
        
        await factory.set_auto(is_auto)

        return {"success": True}
    except ValueError as e:
        return {"error": str(e)}