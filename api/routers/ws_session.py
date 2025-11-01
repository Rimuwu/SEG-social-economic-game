from modules import websocket_manager
from modules.ws_hadnler import message_handler
from modules.db import just_db
from game.session import session_manager, Session, SessionStages
from modules.check_password import check_password

@message_handler(
    "get-sessions", 
    doc="Обработчик получения списка сессий. Отправляет ответ на request_id", 
    datatypes=[
        "stage: Optional[str]", 
        "request_id: str"
        ])
async def handle_get_sessions(client_id: str, message: dict):
    """Обработчик получения списка сессий"""

    conditions = {
        "stage": message.get("stage"),
    }

    # Получаем список сессий из базы данных
    sessions = await just_db.find('sessions',
                            to_class=Session,
                         **{k: v for k, v in conditions.items() if v is not None})

    return [await s.to_dict() for s in sessions]

@message_handler(
    "get-session", 
    doc="Обработчик получения сессии. Отправляет ответ на request_id.", 
    datatypes=[
        "session_id: Optional[str]", 
        "stage: Optional[str]",
        "request_id: str"
        ])
async def handle_get_session(client_id: str, message: dict):
    """Обработчик получения сессии"""

    conditions = {
        "session_id": message.get("session_id"),
        "stage": message.get("stage")
    }

    # Получаем сессию из базы данных
    session = await just_db.find_one('sessions',
                               to_class=Session,
                         **{k: v for k, v in conditions.items() if v is not None})

    return await session.to_dict() if session else None

@message_handler(
    "create-session", 
    doc="Обработчик создания сессии. Отправляет ответ на request_id. Требуется пароль для взаимодействия.",
    datatypes=[
        "session_id: Optional[str]",
        
        "map_pattern: Optional[str]",
        "size: Optional[int]",
        "max_steps: Optional[int]",
        "session_group_url: Optional[str]",

        "password: str",
        "request_id: str"
    ]
)
async def handle_create_session(client_id: str, message: dict):
    """Обработчик создания сессии"""

    session_id = message.get("session_id", "")
    password = message.get("password", "")

    map_pattern = message.get('map_pattern', 'random')
    size = message.get('size', 6)
    max_steps = message.get('max_steps', 15)
    session_group_url = message.get(
        'session_group_url', '')

    try:
        check_password(password)

        session = await session_manager.create_session(
            session_id=session_id,
            map_pattern=map_pattern,
            size=size,
            max_steps=max_steps,
            session_group_url=session_group_url
        )
    except ValueError as e:
        return {"error": str(e)}

    return await session.to_dict()

@message_handler(
    "update-session-stage", 
    doc="Обработчик обновления стадии сессии. Требуется пароль для взаимодействия. add_shedule - Запускать ли таймер после обновления этапа. Например таймер для обновления этапа с выбора клетки на игру автоматически. По умолчанию - True",
    datatypes=[
        "session_id: Optional[str]",
        "stage: Literal['FreeUserConnect', 'CellSelect', 'Game', 'End']",
        "add_shedule: Optional[bool]"
        "password: str",
    ],
    messages=["api-update_session_stage (broadcast)"]
)
async def handle_update_session_stage(client_id: str, message: dict):
    """Обработчик обновления стадии сессии"""

    session_id = message.get("session_id", "")
    stage: str = message.get("stage", "")
    password = message.get("password", "")
    add_shedule = message.get('add_shedule', True)

    stages_to_types = {
        "FreeUserConnect": SessionStages.FreeUserConnect,
        "CellSelect": SessionStages.CellSelect,
        "Game": SessionStages.Game,
        "End": SessionStages.End
    }

    try:
        check_password(password)

        session = await session_manager.get_session(session_id=session_id)
        if not session: raise ValueError("Сессия не найдена.")

        if stage not in stages_to_types:
            raise ValueError("Неверное значение стадии.")

        await session.update_stage(stages_to_types[stage], 
                             not add_shedule)
    except ValueError as e:
        return {"error": str(e)}


@message_handler(
    "get-sessions-free-cells", 
    doc="Обработчик получения свободных клеток сессии. Отправляет ответ на request_id",
    datatypes=[
        "session_id: str",
        "request_id: str",
    ]
)
async def handle_get_sessions_free_cells(
    client_id: str, message: dict):
    """Обработчик получения свободных клеток сессии"""

    session_id = message.get("session_id", "")

    try:
        session = await session_manager.get_session(session_id=session_id)
        if not session: raise ValueError("Сессия не найдена.")

        free_cells = await session.get_free_cells()
        return {"free_cells": free_cells}

    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "delete-session", 
    doc="Обработчик удаления сессии. ВНИМАНИЕ! Это приведёт к удалению всех привязанных игроков и компаний. Требуется пароль для взаимодействия. Требуется `really=true` для подтверждения удаления.",
    datatypes=[
        "session_id: str",
        "password: str",
        "really: bool"
    ],
    messages=["api-session_deleted (broadcast)"]
)
async def handle_delete_session(
    client_id: str, message: dict):
    """Обработчик удаления сессии"""

    session_id = message.get("session_id", "")
    password = message.get("password", "")
    really = message.get("really", False)

    try:
        check_password(password)

        session = await session_manager.get_session(session_id=session_id)
        if not session: raise ValueError("Сессия не найдена.")

        if not really:
            raise ValueError("Требуется подтверждение для удаления сессии.")

        await session.delete()
    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "get-session-time-to-next-stage", 
    doc="Обработчик получения времени до следующей стадии сессии. Отправляет ответ на request_id",
    datatypes=[
        "session_id: str",
        "request_id: str",
    ],
    messages=[]
)
async def handle_get_session_time_to_next_stage(
    client_id: str, message: dict):
    """Обработчик получения времени до следующей стадии сессии"""

    session_id = message.get("session_id", "")

    session = await session_manager.get_session(session_id=session_id)
    if not session: raise ValueError("Сессия не найдена.")

    t = await session.get_time_to_next_stage()
    return {
        "time_to_next_stage": t, 
        "stage_now": session.stage, 
        "max_steps": session.max_steps, 
        "step": session.step
    }

@message_handler(
    "get-item-price", 
    doc="Обработчик получения цены конкретного товара в сессии. Отправляет ответ на request_id",
    datatypes=[
        "session_id: str",
        "item_id: str",
        "request_id: str",
    ]
)
async def handle_get_item_price(client_id: str, message: dict):
    """Обработчик получения цены конкретного товара"""

    session_id = message.get("session_id", "")
    item_id = message.get("item_id", "")

    try:
        session = await session_manager.get_session(session_id=session_id)
        if not session: 
            raise ValueError("Сессия не найдена.")

        price = await session.get_item_price(item_id)
        return {
            "item_id": item_id,
            "price": price
        }

    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "get-all-item-prices", 
    doc="Обработчик получения всех цен товаров в сессии. Отправляет ответ на request_id",
    datatypes=[
        "session_id: str",
        "request_id: str",
    ]
)
async def handle_get_all_item_prices(client_id: str, message: dict):
    """Обработчик получения всех цен товаров"""

    session_id = message.get("session_id", "")

    try:
        session = await session_manager.get_session(session_id=session_id)
        if not session: 
            raise ValueError("Сессия не найдена.")

        all_prices = await session.get_all_item_prices_dict()
        return {
            "prices": all_prices
        }

    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "get-session-event", 
    doc="Обработчик получения события сессии. Отправляет ответ на request_id",
    datatypes=[
        "session_id: str",
        "request_id: str",
    ]
)
async def handle_get_session_event(client_id: str, message: dict):
    """Обработчик получения события сессии"""

    session_id = message.get("session_id", "")

    try:
        session = await session_manager.get_session(session_id=session_id)
        if not session: 
            raise ValueError("Сессия не найдена.")

        event = session.public_event_data()
        return {
            "event": event
        }

    except ValueError as e:
        return {"error": str(e)}

@message_handler(
    "get-session-leaders", 
    doc="Обработчик получения лидеров сессии. Отправляет ответ на request_id",
    datatypes=[
        "session_id: str",
        "request_id: str",
    ]
)
async def handle_get_session_leaders(client_id: str, message: dict):
    """Обработчик получения лидеров сессии"""

    session_id = message.get("session_id", "")

    try:
        session = await session_manager.get_session(session_id=session_id)
        if not session: 
            raise ValueError("Сессия не найдена.")

        leaders = await session.leaders()
        return {
            "capital": leaders["capital"].to_dict() if leaders["capital"] else None,
            "reputation": leaders["reputation"].to_dict() if leaders["reputation"] else None,
            "economic": leaders["economic"].to_dict() if leaders["economic"] else None
        }

    except ValueError as e:
        return {"error": str(e)}
