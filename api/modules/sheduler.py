import traceback
from typing import Callable, Optional
from modules.db import just_db
from modules.utils import *
import asyncio
from datetime import datetime
import json
from modules.logs import game_logger

class TaskScheduler:

    __table_name__ = 'time_schedule'

    def __init__(self, db=just_db):
        self.db = db
        self.running = False
        asyncio.create_task(self._init_schedule_table())

    async def _init_schedule_table(self):
        tables = await self.db.get_tables()
        if self.__table_name__ not in tables:
            await self.db.create_table(self.__table_name__)

    async def start(self):
        if self.running: return
        self.running = True
        asyncio.create_task(self._run_scheduler())

    def stop(self):
        self.running = False

    async def _run_scheduler(self):
        while self.running:
            try:
                await self._check_and_execute_tasks()
            except Exception as e:
                print(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(1)

    async def _check_and_execute_tasks(self):
        current_time = datetime.now()
        tasks =  await self.db.find(self.__table_name__)
        tasks: list[dict] = list(tasks)

        for task in tasks:
            task_time = datetime.fromisoformat(task['execute_at'])
            if task_time <= current_time:
                await self._execute_task(task)

    async def _execute_task(self, task):
        func = str_to_func(task['function_path'])
        args = json.loads(task.get('args', '[]'))
        kwargs = json.loads(task.get('kwargs', '{}'))
        repeat = task.get('repeat', False)
        add_at = datetime.fromisoformat(task['add_at'])
        execute_at = datetime.fromisoformat(task['execute_at'])

        try:
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
        except Exception as e:
            game_logger.error(f"Ошибка при выполнении запланированной задачи {task['id']}: {traceback.format_exc()}")

        if repeat:
            interval = execute_at - add_at
            next_execute_time = datetime.now() + interval
            await self.db.update(self.__table_name__, 
                           {'id': task['id']}, 
                           {'execute_at': next_execute_time.isoformat()}
                           )

        else:
            await self.db.delete(self.__table_name__, id=task['id'])

    async def schedule_task(self, function: Callable, 
                      execute_at: datetime, 
                      args: Optional[list] = None, 
                      kwargs: Optional[dict] = None,
                      repeat: bool = False,
                      delete_on_shutdown: bool = False) -> int:
        if args is None: args = []
        if kwargs is None: kwargs = {}

        task_data = {
            'function_path': func_to_str(function),
            'execute_at': execute_at.isoformat(),
            'add_at': datetime.now().isoformat(),
            'args': json.dumps(args),
            'kwargs': json.dumps(kwargs),
            'repeat': repeat,
            'delete_on_shutdown': delete_on_shutdown
        }

        return await self.db.insert(self.__table_name__, task_data)

    async def cleanup_shutdown_tasks(self):
        """
        Удаляет все задачи, помеченные для удаления при завершении работы API.
        Этот метод следует вызывать при завершении работы приложения.
        """
        try:
            deleted_count = await self.db.delete(self.__table_name__, delete_on_shutdown=True)
            print(f"Удалено {deleted_count} задач при завершении работы")
            return deleted_count
        except Exception as e:
            print(f"Ошибка при удалении задач завершения: {e}")
            return 0
    
    async def get_scheduled_tasks(self, id: int):
        """
        Возвращает список всех запланированных задач.
        """
        return await self.db.find_one(self.__table_name__, id=id)


scheduler = TaskScheduler()