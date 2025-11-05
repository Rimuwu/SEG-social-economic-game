from scenes.utils.oneuser_page import OneUserPage
from modules.ws_client import get_contracts
from global_modules.load_config import Resources, ALL_CONFIGS
from oms.utils import callback_generator
from aiogram.types import CallbackQuery
import json


RESOURCES: Resources = ALL_CONFIGS["resources"]

class ContractMain(OneUserPage):
    __for_blocked_pages__ = ["contract-sellect-confirm", "contract-create-page"]
    __page_name__ = "contract-main-page"
    
    async def buttons_worker(self):
        self.row_width = 2
        buttons = [
            {"text": "📄 Просмотреть все контракты", "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "contract-view-page"), "ignore_row": True},
            {"text": "✍️ Создать", "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "contract-create-page")},
            {"text": "✍️ Изменить ваши", "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "contract-update-page")},
            {"text": "📄 Выполнить ваши контракты", "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "contract-execute-page")},
        ]
        return buttons
    
    
    