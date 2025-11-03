import asyncio
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING, Type
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel
import os
from copy import deepcopy

if TYPE_CHECKING:
    from global_modules.db.baseclass import BaseClass

class MongoDatabase:
    """MongoDB база данных с использованием motor для асинхронных операций"""
    
    def __init__(self, 
                 connection_string: Optional[str] = None, 
                 database_name: str = "seg_game_db",
                 auto_connect: bool = True):
        
        self.connection_string = connection_string or os.getenv(
            'MONGODB_URL', 
            'mongodb://localhost:27017'
        )
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._collections: Dict[str, AsyncIOMotorCollection] = {}
        
        if auto_connect:
            asyncio.create_task(self.connect())

    async def connect(self):
        """Подключается к MongoDB"""
        if self.client is None:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client[self.database_name]

        # Проверяем подключение
        try:
            await self.client.admin.command('ping')
            print(f"Подключен к MongoDB: {self.database_name}")
        except Exception as e:
            print(f"Ошибка подключения к MongoDB: {e}")
            raise

    async def disconnect(self):
        """Отключается от MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self._collections = {}

    def _get_collection(self, table_name: str) -> AsyncIOMotorCollection:
        """Получает коллекцию по имени таблицы"""
        if self.db is None:
            raise RuntimeError("Database not connected")
        if table_name not in self._collections:
            self._collections[table_name] = self.db[table_name]
        return self._collections[table_name]

    async def create_table(self, table_name: str, indexes: Optional[List[str]] = None):
        """Создаёт новую коллекцию с индексами"""
        if self.db is None:
            raise RuntimeError("Database not connected")

        if table_name not in await self.db.list_collection_names():
            await self.db.create_collection(table_name)

    async def insert(self, table_name: str, record: Dict[str, Any]) -> int:
        """Вставляет запись в коллекцию"""
        if self.db is None:
            await self.connect()

        collection = self._get_collection(table_name)
        
        # Добавляем автоматические поля
        record = deepcopy(record)
        if 'id' not in record:
            # Получаем максимальный id
            max_id = await self.max_id_in_table(table_name)
            record['id'] = max_id + 1

        record['created_at'] = datetime.now()
        record['updated_at'] = datetime.now()

        # Вставляем запись
        result = await collection.insert_one(record)
        return record['id']

    async def find(self, 
                   table_name: str, 
                   to_class: Optional[Type['BaseClass']] = None,
                   limit: Optional[int] = None,
                   skip: Optional[int] = None,
                   sort: Optional[List[tuple]] = None,
                   **conditions) -> List[Union[Dict[str, Any], 'BaseClass']]:
        """Находит записи по условиям"""
        if self.db is None:
            await self.connect()
            
        collection = self._get_collection(table_name)
        
        # Создаём запрос
        cursor = collection.find(conditions)
        
        # Применяем сортировку
        if sort:
            cursor = cursor.sort(sort)
            
        # Применяем лимит и пропуск
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        # Получаем результаты
        results = []
        async for document in cursor:
            # Убираем _id из документа
            # if '_id' in document:
            #     del document['_id']
                
            if to_class:
                instance = to_class()
                instance.load_from_base(document)
                results.append(instance)
            else:
                results.append(document)

        return results

    async def find_one(self, 
                       table_name: str, 
                       to_class: Optional[Type['BaseClass']] = None,
                       **conditions) -> Optional[Union[Dict[str, Any], 'BaseClass']]:
        """Находит одну запись"""
        if self.db is None:
            await self.connect()

        collection = self._get_collection(table_name)
        document = await collection.find_one(conditions)

        if not document:
            return None

        # # Убираем _id из документа
        # if '_id' in document:
        #     del document['_id']

        if to_class:
            instance = to_class()
            instance.load_from_base(document)
            return instance
        else:
            return document

    async def update(self, 
                     table_name: str, 
                     conditions: Dict[str, Any], 
                     updates: Dict[str, Any]) -> int:
        """Обновляет записи"""
        if self.db is None:
            await self.connect()
            
        if not isinstance(conditions, dict):
            raise ValueError(f"conditions must be a dictionary, got {type(conditions)} ({conditions})")
        
        if not isinstance(updates, dict):
            raise ValueError(f"updates must be a dictionary, got {type(updates)} ({updates})")

        if not updates:
            raise ValueError("updates cannot be empty")

        collection = self._get_collection(table_name)
        
        # Добавляем updated_at
        updates = deepcopy(updates)
        updates['updated_at'] = datetime.now()
        
        # Обновляем записи
        result = await collection.update_many(
            conditions, 
            {'$set': updates}
        )
        
        return result.modified_count

    async def delete(self, table_name: str, **conditions) -> int:
        """Удаляет записи"""
        if self.db is None:
            await self.connect()
            
        collection = self._get_collection(table_name)
        result = await collection.delete_many(conditions)
        return result.deleted_count

    async def count(self, table_name: str, **conditions) -> int:
        """Считает количество записей"""
        if self.db is None:
            await self.connect()
            
        collection = self._get_collection(table_name)
        return await collection.count_documents(conditions)

    async def get_tables(self) -> List[str]:
        """Возвращает список коллекций"""
        if self.db is None:
            await self.connect()
            
        if self.db is None:
            raise RuntimeError("Database not connected")
            
        return await self.db.list_collection_names()

    async def drop_table(self, table_name: str):
        """Удаляет коллекцию"""
        if self.db is None:
            await self.connect()
            
        collection = self._get_collection(table_name)
        await collection.drop()
        
        # Удаляем из кэша
        if table_name in self._collections:
            del self._collections[table_name]

    async def drop_all(self):
        """Удаляет все коллекции"""
        if self.db is None:
            await self.connect()
            
        collection_names = await self.get_tables()
        for name in collection_names:
            await self.drop_table(name)

    async def max_id_in_table(self, table_name: str) -> int:
        """Возвращает максимальный ID в коллекции"""
        if self.db is None:
            await self.connect()

        collection = self._get_collection(table_name)

        # Ищем документ с максимальным id
        cursor = collection.find().sort([('id', -1)]).limit(1)
        result = await cursor.to_list(length=1)
        
        if result:
            return result[0].get('id', 0)
        return 0

    # Синхронные обёртки для обратной совместимости
    def _run_async(self, coro):
        """Запускает асинхронную корутину в синхронном контексте"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # Если цикл уже запущен, создаём новый
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)

    def sync_insert(self, table_name: str, record: Dict[str, Any]) -> int:
        """Синхронная версия insert"""
        return self._run_async(self.insert(table_name, record))

    def sync_find(self, table_name: str, to_class: Optional[Type['BaseClass']] = None, **conditions):
        """Синхронная версия find"""
        return self._run_async(self.find(table_name, to_class, **conditions))

    def sync_find_one(self, table_name: str, to_class: Optional[Type['BaseClass']] = None, **conditions):
        """Синхронная версия find_one"""
        return self._run_async(self.find_one(table_name, to_class, **conditions))

    def sync_update(self, table_name: str, conditions: Dict[str, Any], updates: Dict[str, Any]) -> int:
        """Синхронная версия update"""
        return self._run_async(self.update(table_name, conditions, updates))

    def sync_delete(self, table_name: str, **conditions) -> int:
        """Синхронная версия delete"""
        return self._run_async(self.delete(table_name, **conditions))

    def sync_count(self, table_name: str, **conditions) -> int:
        """Синхронная версия count"""
        return self._run_async(self.count(table_name, **conditions))