

from scenes.admin import __admin__
from scenes.admin import AdminMainPage
from scenes.bank_pages import __bank__
from scenes.cell_pages import __cell__
from scenes.company_pages import __company__
from scenes.contractc_pages import __contract__
# from scenes.exchange_pages import __exchange__
from scenes.exchanges_page_2 import __exchange__
from scenes.factory_pages import __factory__
from scenes.game_pages import __game__, __gameinfo__
from scenes.info_pages import __info__
from scenes.logistics_pages import __logistics__
from scenes.start_game_pages import __startgame__


from scenes.base_scene import AdminScene
from modules.db import db


class GameManager(AdminScene):

    __scene_name__ = 'scene-manager'
    __pages__ = [AdminMainPage]
    
    __pages__.extend(__contract__)
    __pages__.extend(__admin__)
    __pages__.extend(__bank__)
    __pages__.extend(__cell__)
    __pages__.extend(__company__)
    __pages__.extend(__exchange__)
    __pages__.extend(__factory__)
    __pages__.extend(__game__)
    __pages__.extend(__info__)
    __pages__.extend(__logistics__)
    __pages__.extend(__startgame__)
    @staticmethod
    async def insert_to_db(user_id: int, data: dict):
        await db.insert('scenes', data)

    @staticmethod
    async def load_from_db(user_id: int) -> dict:
        data = await db.find_one('scenes', user_id=user_id) or {}
        return data

    @staticmethod
    async def update_to_db(user_id: int, data: dict):
        await db.update('scenes', {'user_id': user_id}, data)

    @staticmethod
    async def delete_from_db(user_id: int):
        await db.delete('scenes', user_id=user_id)
    
    # Функция для вставки сцены в БД
    # В функцию передаёт user_id: int, data: dict
    __insert_function__ = insert_to_db

    # Функция для загрузки сцены из БД
    # В функцию передаёт user_id: int, вернуть должна dict
    __load_function__ = load_from_db

    # Функция для обновления сцены в БД
    # В функцию передаёт user_id: int, data: dict
    __update_function__ = update_to_db
    
    # Функция для удаления сцены из БД
    # В функцию передаёт user_id: int
    __delete_function__ = delete_from_db