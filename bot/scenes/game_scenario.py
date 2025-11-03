from scenes.start_page import Start
from scenes.name_page import UserName
from scenes.company_create_page import CompanyCreate
from scenes.company_join_page import CompanyJoin
from scenes.main_page import MainPage
from scenes.wait_game_page import WaitStart
from scenes.wait_game_stage_page import WaitGameStagePage
from scenes.wait_select_cell_page import WaitSelectCellPage
from scenes.select_cell_page import SelectCell
from scenes.about_info_page import AboutInfo
from scenes.cells_info_page import CellsInfo
from scenes.inventory_page import InventoryPage
from scenes.bank_page import BankPage
from scenes.bank_credit_page import BankCreditPage
from scenes.bank_deposit_page import BankDepositPage
from scenes.contract_main_page import ContractMainPage
from scenes.city_page import City
from scenes.upgrade_menu import UpgradeMenu
from scenes.logistics_menu import LogisticsMenu
from scenes.factory_menu_page import FactoryMenu
from scenes.factory_rekit_groups import FactoryRekitGroups
from scenes.factory_rekit_count import FactoryRekitCount
from scenes.factory_rekit_resource import FactoryRekitResource
from scenes.factory_rekit_produce import FactoryRekitProduce
from scenes.factory_start_groups import FactoryStartGroups
from scenes.factory_change_mode import FactoryChangeMode
from scenes.exchange_page import ExchangePage
from scenes.change_turn_page import ChangeTurnPage
from scenes.prison_page import PrisonPage
from scenes.end_game_page import EndGamePage
from scenes.admin_panel_page import AdminPanelPage
from scenes.base_scene import AdminScene
from scenes.about_turn_page import AboutTurnPage
from modules.db import db


class GameManager(AdminScene):

    __scene_name__ = 'scene-manager'
    __pages__ = [
        Start,
        UserName,
        CompanyCreate,
        CompanyJoin,
        MainPage,
        WaitStart,
        WaitGameStagePage,
        WaitSelectCellPage,
        SelectCell,
        AboutInfo,
        CellsInfo,
        InventoryPage,
        BankPage,
        BankCreditPage,
        BankDepositPage,
        UpgradeMenu,
        LogisticsMenu,
        FactoryMenu,
        FactoryRekitGroups,
        FactoryRekitCount,
        FactoryRekitResource,
        FactoryRekitProduce,
        FactoryStartGroups,
        FactoryChangeMode,
        ChangeTurnPage,
        PrisonPage,
        EndGamePage,
        AdminPanelPage,
        ExchangePage,
        City,
        AboutTurnPage
    ]
    
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