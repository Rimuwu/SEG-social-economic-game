from utils.filter_item import ItemFilter
from oms.utils import callback_generator
from modules.ws_client import create_contract, get_company
from modules.utils import create_buttons
from aiogram.types import CallbackQuery, Message
from global_modules.load_config import ALL_CONFIGS, Resources
import json


RESOURCE: Resources = ALL_CONFIGS["resources"]

class ContractCreatePage(ItemFilter):
    __page_name__ = "contract-create-page"
    
    
    async def data_preparate(self):
        self.scene.update_key("contract-create-page", "settings", json.dumps({
            "supplier_company_id": None,
            "customer_company_id": None,
            "session_id": self.scene.get_key(self.scene.__scene_name__, "session"),
            "resource": None,
            "amount_per_turn": None,
            "duration_turns": None,
            "payment_amount": None,
            "who_creator": self.scene.get_key(self.scene.__scene_name__, "company_id"),
        }))
        self.scene.update_key("contract-create-page", "state", "select_role")
        self.scene.update_key("contract-create-page", "page", 0)
        self.scene.update_key("contract-create-page", "error", "")
        return super().data_preparate()
    
    async def content_worker(self):
        state = self.scene.get_key("contract-create-page", "state")
        error = self.scene.get_key("contract-create-page", "error")
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        if state == "select_role":
            return "Выберите роль в контракте:"
        if state == "select_company":
            return "Выберите компанию для контракта:"
        if state == "select_resource":
            if settings.get("who_creator") == settings.get("supplier_company_id"):
                return super().content_worker()
            return "Выберите ресурс для контракта:"
        if state == "input_amount_per_turn":
            text = "Введите количество ресурса, которое будет передаваться за ход:"
            if error != "":
                return f"{text}{error}"
            self.scene.update_key("contract-create-page", "error", "")
            return text
        if state == "input_duration_turns":
            return "Введите длительность контракта в ходах:"
        if state == "input_payment_amount":
            return "Введите сумму оплаты за выполнение контракта:"
    
    
    async def buttons_worker(self):
        state = self.scene.get_key("contract-create-page", "state")
        page = self.scene.get_key("contract-create-page", "page")
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        buttons = []
        self.row_width = 2
        if state == "select_role":
            buttons.append(create_buttons(self.scene.__scene_name__, "Поставщик", "contract_create_select_role", "supplier"))
            buttons.append(create_buttons(self.scene.__scene_name__, "Покупатель", "contract_create_select_role", "customer"))
        elif state == "select_company":
            container = []
            companies = await get_company(session_id=settings.get("session_id"))
            for company in companies:
                company_id = company.get("id")
                company_name = company.get("name")
                if company_id != settings.get("who_creator"):
                    container.append(create_buttons(self.scene.__scene_name__, company_name, "contract_create_select_company", company_id, ignore_row=True))
            buttons.extend(container[page*5:page*5+5])
            if len(container) > 5:
                buttons.append({"text": "Назад",
                                "callback_data": callback_generator(self.scene.__scene_name__, "back_page"),
                                })
                buttons.append({"text": "Вперёд",
                                "callback_data": callback_generator(self.scene.__scene_name__, "next_page"),
                                })
            
        elif state == "select_resource":
            if settings.get("who_creator") == settings.get("supplier_company_id"):  
                return await super().buttons_worker()
            elif settings.get("who_creator") == settings.get("customer_company_id"):
                pass
        return buttons
    
    @ItemFilter.on_text('int')
    async def int_input(self, message: Message, value: int):
        state = self.scene.get_key("contract-create-page", "state")
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        
        if state == "input_amount_per_turn":
            if value <= 0:
                self.scene.update_key("contract-create-page", "error", "\nКоличество должно быть больше нуля. Повторите ввод.")
                await self.scene.update_message()
            