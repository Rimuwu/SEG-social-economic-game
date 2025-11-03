from pprint import pprint
from typing import Optional
from global_modules.db.mongo_database import MongoDatabase

class BaseClass:
    """ Базовый класс для всех классов, которые будут сохраняться в базе данных.
    """
    __tablename__: str = "base" # Имя таблицы в базе данных
    __unique_id__: str = "_id"  # Поле, которое будет использоваться как уникальный идентификатор
    __db_object__: MongoDatabase  # Экземпляр MongoDatabase, должен быть установлен в подклассе

    def load_from_base(self, data: Optional[dict]):
        """ Загружает данные из словаря в атрибуты объекта.
        """
        if data is None: return None
        for key, value in data.items(): setattr(self, key, value)

    async def save_to_base(self):
        """ Сохраняет текущие атрибуты объекта в базу данных.
        """

        # Фильтруем данные, исключая атрибуты, начинающиеся с _
        data_to_save = {key: value for key, value in self.__dict__.items() if not key.startswith('_')}

        await self.__db_object__.update(self.__tablename__, 
                {self.__unique_id__: self.__dict__[self.__unique_id__]},
                data_to_save
                )

    async def insert(self):
        """ Вставляет текущие атрибуты объекта в базу данных.
        """

        if isinstance(self.__dict__[self.__unique_id__], int) or self.__dict__[self.__unique_id__] is None:
            if not self.__dict__[self.__unique_id__]:
                self.__dict__[self.__unique_id__] = await self.__db_object__.max_id_in_table(
                    self.__tablename__) + 1

            find_by_ud = await self.__db_object__.find_one(
                self.__tablename__, 
                **{self.__unique_id__: self.__dict__[self.__unique_id__]}
                )

            if find_by_ud:
                self.__dict__[self.__unique_id__] = await self.__db_object__.max_id_in_table(
                    self.__tablename__) + 1

        # Фильтруем данные, исключая атрибуты, начинающиеся с _
        data_to_save = {key: value for key, value in self.__dict__.items(
            ) if not key.startswith('_')}

        await self.__db_object__.insert(self.__tablename__, data_to_save)
        await self.reupdate()

    async def reupdate(self):
        """ Обновляет атрибуты объекта из базы данных.
        """
        self.load_from_base(
            await self.__db_object__.find_one(self.__tablename__, 
                **{self.__unique_id__: self.__dict__[self.__unique_id__]}
                ) # type: ignore
        )
        return self

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.__dict__})>"