from .oneuser_page import OneUserPage
from modules.ws_client import get_company_contracts, accept_contract, get_contract, get_company
from global_modules.load_config import ALL_CONFIGS, Resources


RESOURCES: Resources = ALL_CONFIGS["resources"]


Page = OneUserPage


class ContractView(Page):
    __for_blocked_pages__ = ["contract-main-page"]
    
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "stage") is None:
            self.scene.update_key(self.__page_name__, "stage", "main") #view
        if self.scene.get_key(self.__page_name__, "contract_id") is None:
            self.scene.update_key(self.__page_name__, "contract_id", -1)
    
    
    async def content_worker(self):
        datap = self.scene.get_data(self.__page_name__)
        data = self.scene.get_data("scene")
        compnay_id = data.get("company_id")
        session_id = data.get("session")
        stage = datap.get("stage", "main")
        content = ''
        if stage == "main":
            content = "Нажмите на кнопку для просмтотра информации о контракте"
        elif stage == "view":
            contract_id = datap.get("contract_id")
            if contract_id == -1:
                return "Ошибка перехода на страницу, контракт не выбран"
            contract = await get_contract(contract_id)
            supplier_id = contract.get("supplier_company_id")
            customer_id = contract.get("customer_company_id")
            who_create = contract.get("who_creator")
            resource = contract.get("resource")
            amount_per_turn = contract.get("amount_per_turn")
            payment_amount = contract.get("payment_amount")
            duration_turns = contract.get("duration_turns")
            created_at_step = contract.get("created_at_step")
            company_data_create = await get_company(id=who_create)
            company_data = await get_company(id=compnay_id)
            resource_data = RESOURCES.get_resource(resource)
            text_ = ""
            if supplier_id == compnay_id:
                text_ = f"Вы поставляете {resource_data.emoji} {resource_data.label}"
            if customer_id == compnay_id:
                text_ = f"Вам поставляют {resource_data.emoji} {resource_data.label}"
            content = f"""Создатель контракта: {company_data_create["name"]}

            {text_}
            Количество в ход: {amount_per_turn}
            Длительность контракта в ходах: {duration_turns}
            Сумма контракта: {payment_amount}
            Создан в ходе: {created_at_step}
            
            Нажмите кнопку ниже чтобы принять или отменить
            """
        return content
    
    async def buttons_worker(self):
        datap = self.scene.get_data(self.__page_name__)
        data = self.scene.get_data("scene")
        compnay_id = data.get("company_id")
        session_id = data.get("session")
        stage = datap.get("stage", "main")
        