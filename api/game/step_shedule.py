import asyncio
from global_modules.models.cells import Cells
from global_modules.db.baseclass import BaseClass
from modules.db import just_db
from game.session import SessionObject
from global_modules.load_config import ALL_CONFIGS, Resources, Improvements, Settings, Capital, Reputation
from modules.function_way import *

RESOURCES: Resources = ALL_CONFIGS["resources"]
CELLS: Cells = ALL_CONFIGS['cells']
IMPROVEMENTS: Improvements = ALL_CONFIGS['improvements']
SETTINGS: Settings = ALL_CONFIGS['settings']
CAPITAL: Capital = ALL_CONFIGS['capital']
REPUTATION: Reputation = ALL_CONFIGS['reputation']

class StepSchedule(BaseClass, SessionObject):

    __tablename__ = "step_schedule"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id

        self.session_id: str = ""
        self.in_step: int = 0
        self.functions: list = [
            ]  # Список функций для выполнения в этом шаге

    async def create(self, session_id: str, in_step: int) -> 'StepSchedule':
        if schedule := await just_db.find_one(
            self.__tablename__, 
            session_id=session_id, in_step=in_step,
            to_class=StepSchedule
            ):
            return schedule # type: ignore

        self.session_id = session_id
        self.in_step = in_step

        await self.insert()
        return self

    async def add_function(self, function, **kwargs):
        """ Добавляет функцию в расписание шага
        """
        if not function or not callable(function):
            raise ValueError("Функция должна быть вызываемой.")

        if not self.id:
            raise ValueError("Расписание должно быть сохранено перед добавлением функций.")

        session = await self.get_session()
        if not session:
            await just_db.delete(self.__tablename__, id=self.id)
            raise ValueError("Неверная сессия для добавления функции.")

        if not session.step <= self.in_step:
            raise ValueError("Неверный шаг для добавления функции.")

        self.functions.append({
            "function": func_to_str(function),
            "args": kwargs
        })
        await self.save_to_base()
        await self.reupdate()
        return True

    async def execute(self):
        """ Выполняет все функции в расписании шага
        """
        session = await self.get_session()

        if not session:
            await just_db.delete(self.__tablename__, id=self.id)
            print(f'Session {self.session_id} not found. Deleting schedule {self.id}.')
            return False

        if session.step != self.in_step:
            return False

        for func_entry in self.functions:
            func_name = func_entry.get("function")
            args = func_entry.get("args", {})

            if not func_name:
                print("Function name is missing.")
                continue

            # Импортируем функцию по имени
            function = str_to_func(func_name)

            if not callable(function):
                print(f"{func_name} is not callable.")
                continue

            # Выполняем функцию
            try:
                if asyncio.iscoroutinefunction(function):
                    await function(**args)
                else:
                    function(**args)
            except Exception as e:
                print(f"Error executing function {func_name}: {e}")

        await just_db.delete(self.__tablename__, id=self.id)
        return True