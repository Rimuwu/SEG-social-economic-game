from game.session import SessionObject
from global_modules.db.baseclass import BaseClass
from modules.db import just_db
from modules.websocket_manager import websocket_manager
from modules.validation import validate_username
from modules.logs import game_logger

class User(BaseClass, SessionObject):

    __tablename__ = "users"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id
        self.username: str = ""
        self.company_id: int = 0
        self.session_id: str = ""

    async def create(self, id: int, 
               username: str, 
               session_id: str):

        self.session_id = session_id
        session = await self.get_session()

        if not session or not session.can_user_connect():
            game_logger.warning(f"Попытка создания пользователя в неверной сессии ({session_id}) или на неверном этапе.")
            raise ValueError("Неверная сессия или регистрация запрещена на данном этапе.")

        self.id = id

        with_this_name = await just_db.find_one("users", 
                                          username=username, 
                                          session_id=session_id)
        if with_this_name:
            game_logger.warning(f"Попытка создать пользователя с занятым именем '{username}' в сессии {session_id}.")
            raise ValueError(f"Имя пользователя '{username}' уже занято в этой сессии.")

        username = validate_username(username)
        self.username = username

        await self.insert()

        await websocket_manager.broadcast({
            "type": "api-create_user",
            "data": {
                'session_id': self.session_id,
                'user': self.to_dict()
            }
        })
        game_logger.info(f"Создан новый пользователь: {self.username} ({self.id}) в сессии {self.session_id}.")
        return self

    async def create_company(self, name: str):
        from game.company import Company
        session = await self.get_session_or_error()

        if self.company_id != 0:
            game_logger.warning(f"Пользователь {self.username} ({self.id}) уже в компании, но пытается создать новую.")
            raise ValueError("Пользователь уже находится в компании.")

        company = await Company().create(name=name, 
                                   session_id=self.session_id
                                   )
        if not await session.can_add_company():
            game_logger.warning(f"Пользователь {self.username} ({self.id}) не может создать компанию на данном этапе в сессии {self.session_id}.")
            raise ValueError("Невозможно добавить компанию на данном этапе.")

        self.company_id = company.id

        await self.save_to_base()
        game_logger.info(f"Пользователь {self.username} ({self.id}) создал компанию '{name}' ({company.id}) в сессии {self.session_id}.")
        return company

    async def add_to_company(self, secret_code: int):
        from game.company import Company
        if self.company_id != 0:
            game_logger.warning(f"Пользователь {self.username} ({self.id}) уже в компании, но пытается войти в другую.")
            raise ValueError("Пользователь уже находится в компании.")

        company: Company = await just_db.find_one(
                    "companies", 
                    to_class=Company, 
                    secret_code=secret_code) # type: ignore
        if not company: 
            game_logger.warning(f"Пользователь {self.username} ({self.id}) не смог найти компанию с кодом {secret_code}.")
            raise ValueError("Компания с этим секретным кодом не найдена.")

        if await company.can_user_enter() is False:
            game_logger.warning(f"Компания '{company.name}' ({company.id}) закрыта для входа, но пользователь {self.username} ({self.id}) пытается войти.")
            raise ValueError("Компания в данный момент не принимает новых пользователей.")

        self.company_id = company.id
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-user_added_to_company",
            "data": {
                "company_id": self.company_id,
                "user_id": self.id
            }
        })
        game_logger.info(f"Пользователь {self.username} ({self.id}) присоединился к компании '{company.name}' ({company.id}).")
        return company

    async def delete(self):
        await just_db.delete(self.__tablename__, id=self.id)

        try:
            await self.leave_from_company()
        except Exception: pass

        await websocket_manager.broadcast({
            "type": "api-user_deleted",
            "data": {
                "user_id": self.id
            }
        })
        game_logger.info(f"Пользователь {self.username} ({self.id}) удален.")
        return True

    async def leave_from_company(self):
        from game.company import Company
        if self.company_id == 0:
            game_logger.warning(f"Пользователь {self.username} ({self.id}) пытается покинуть компанию, не находясь в ней.")
            raise ValueError("Пользователь не находится в компании.")

        old_company_id = self.company_id
        self.company_id = 0
        await self.save_to_base()

        company = await Company(id=old_company_id).reupdate()

        await websocket_manager.broadcast({
            "type": "api-user_left_company",
            "data": {
                "company_id": old_company_id,
                "user_id": self.id
            }
        })
        game_logger.info(f"Пользователь {self.username} ({self.id}) покинул компанию {old_company_id}.")

        if company and len(await company.users) == 0:
            await company.delete()

        return True

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "company_id": self.company_id,
            "session_id": self.session_id
        }