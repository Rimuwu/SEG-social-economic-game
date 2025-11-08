from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator

class ContractMain(OneUserPage):
    __for_blocked_pages__ = ["contract-sellect-confirm", "contract-create-page"]
    __page_name__ = "contract-main-page"
    
    async def buttons_worker(self):
        self.row_width = 2
        buttons = [
            {"text": "📄 Просмотреть все контракты", "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "contract-view-page"), "ignore_row": True},
            {"text": "✍️ Создать", "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "contract-create-page")},
            {"text": "� Выполнить контракты", "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "contract-execute-page")},
        ]
        return buttons
    
    
    