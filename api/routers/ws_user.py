from modules.websocket_manager import websocket_manager
from game.user import User
from modules.check_password import check_password
from modules.ws_hadnler import message_handler
from modules.db import just_db
from game.session import Session, session_manager

@message_handler(
    "get-users", 
    doc="Обработчик получения списка пользователей. Отправляет ответ на request_id.", 
    datatypes=[
        "company_id: Optional[int]", 
        "session_id: Optional[int]", 
        "request_id: str"
        ])
async def handle_get_users(client_id: str, message: dict):
    """Обработчик получения списка пользователей"""

    conditions = {
        "company_id": message.get("company_id"),
        "session_id": message.get("session_id")
    }

    # Получаем список пользователей из базы данных
    users = await just_db.find('users',
                         to_class=User,
                         **{k: v for k, v in conditions.items() if v is not None})

    return [user.to_dict() for user in users]

@message_handler(
    "get-user", 
    doc="Обработчик получения пользователя. Отправляет ответ на request_id.", 
    datatypes=[
        "id: Optional[int]", 
        "username: Optional[str]", 
        "company_id: Optional[int]", 
        "session_id: Optional[str]",
        "request_id: str"
        ])
async def handle_get_user(client_id: str, message: dict):
    """Обработчик получения списка пользователей"""

    conditions = {
        "id": message.get("id"),
        "username": message.get("username"),
        "company_id": message.get("company_id"),
        "session_id": message.get("session_id")
    }

    # Получаем пользователя из базы данных
    user = await just_db.find_one('users',
                            to_class=User,
                         **{k: v for k, v in conditions.items() if v is not None})

    return user.to_dict() if user else None

@message_handler(
    "create-user", 
    doc="Обработчик создания пользователя. Отправляет ответ на request_id. Требуется пароль для взаимодействия.",
    datatypes=[
        "user_id: int",
        "username: str",
        "password: str",
        "session_id: str",
        "request_id: str"
    ],
    messages=["api-create_user (broadcast)"]
)
async def handle_create_user(client_id: str, message: dict):
    """Обработчик создания пользователя"""

    session_id = message.get("session_id")
    password = message.get("password")
    user_id = message.get("user_id")
    username = message.get("username")

    for i in [user_id, username, session_id]:
        if i is None: return {"error": "Пропущены обязательные поля."}

    try:
        check_password(password)

        user = await User().create(id=user_id, 
                            username=username, 
                            session_id=session_id)

    except ValueError as e:
        return {"error": str(e)}

    return {
        'session_id': user.session_id,
        'user': user.to_dict()
    }

@message_handler(
    "update-user", 
    doc="Обработчик обновления пользователя. Требуется пароль для взаимодействия.",
    datatypes=[
        # find
        "user_id: int",
        # update
        'username: Optional[str]',
        'company_id: Optional[int]',
        # required
        "password: str"
    ],
    messages=["api-update_user (broadcast)"]
)
async def handle_update_user(client_id: str, message: dict):
    """Обработчик обновления пользователя"""

    password = message.get("password", "")
    user_id = message.get("user_id", None)

    updates = {
        "username": message.get("username", None),
        "company_id": message.get("company_id", None)
    }

    try:
        check_password(password)

        old_user = await User(id=user_id).reupdate()
        if not old_user: raise ValueError("Пользователь не найден.")

        await just_db.update("users",
                {"id": user_id}, 
            {k: v for k, v in updates.items() if v is not None}
                       )

        new_user = await User(id=user_id).reupdate()

    except ValueError as e:
        return {"error": str(e)}
    data = {
            "session_id": new_user.session_id,
            "new": new_user.to_dict(),
            "old": old_user.to_dict()
        }

    await websocket_manager.broadcast({
        "type": "api-update_user",
        "data": data
    })
    return data

@message_handler(
    "delete-user", 
    doc="Обработчик удаления пользователя. Требуется пароль для взаимодействия.",
    datatypes=[
        "user_id: int",
        "password: str"
    ],
    messages=["api-user_deleted (broadcast)"]
)
async def handle_delete_user(client_id: str, message: dict):
    """Обработчик удаления пользователя"""

    user_id = message.get("user_id")
    password = message.get("password")

    for i in [user_id, password]:
        if i is None: return {"error": "Пропущены обязательные поля."}

    try:
        check_password(password)

        user = await User(id=user_id).reupdate()
        if not user: raise ValueError("Пользователь не найден.")

        await user.delete()

    except ValueError as e:
        return {"error": str(e)}
