from utils.filter_item import ItemFilter
from oms.utils import callback_generator
from modules.ws_client import create_contract, get_company
from modules.utils import create_buttons
from aiogram.types import CallbackQuery
import json


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
    
    async def content_worker(self):
        state = self.scene.get_key("contract-create-page", "state")
        if state == "select_role":
            return "Выберите роль в контракте:"
        if state == "select_company":
            return "Выберите компанию для контракта:"
        if state == "select_resource":
            return "Выберите ресурс для контракта:"
        if state == "input_amount_per_turn":
            return "Введите количество ресурса, которое будет передаваться за ход:"
        if state == "input_duration_turns":
            return "Введите длительность контракта в ходах:"
        if state == "input_payment_amount":
            return "Введите сумму оплаты за выполнение контракта:"
    
    
    async def buttons_worker(self):
        state = self.scene.get_key("contract-create-page", "state")
        buttons = []
        self.row_width = 2
        if state == "select_role":
            buttons.append(create_buttons("Поставщик", "contract_create_select_role", "supplier"))
            buttons.append(create_buttons("Покупатель", "contract_create_select_role", "customer"))
        elif state == "select_company":
            session_id = self.scene.get_key(self.scene.__scene_name__, "session")
            user_company_id = self.scene.get_key(self.scene.__scene_name__, "company_id")
            settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
            who_creator = settings.get("who_creator")
            companies = await get_company(session_id=session_id)
            for company in companies:
                company_id = company.get("id")
                company_name = company.get("name")
                if company_id != user_company_id and company_id != who_creator:
                    buttons.append(create_buttons(company_name, "contract_create_select_company", company_id))
        elif state == "select_resource":
            return await super().buttons_worker()
        return buttons