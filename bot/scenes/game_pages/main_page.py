from oms import Page
from aiogram.types import Message, CallbackQuery
from modules.ws_client import get_company, get_users, get_company_contracts, get_company_warehouse

class MainPage(Page):

    __page_name__ = 'main-page'

    async def content_worker(self) -> str:
        company_id = self.scene.get_key("scene", "company_id")
        session_id = self.scene.get_key("scene", "session")
        company = await get_company(id=company_id)
        warehouses = await get_company_warehouse(company_id=company_id)
        contracts = await get_company_contracts(company_id=company_id)
        contract_new = 0
        contract_not_delivered = 0
        for c in contracts:
            if c.get("who_create") != company_id and c.get("accepted") == False:
                contract_new += 1
            if c.get("supplier_company_id") == company_id and c.get("accepted") == True and c.get("delivered_this_turn") == False:
                contract_not_delivered += 1
                
        balance = company.get("balance")
        reputation = company.get("reputation")
        tax = company.get("tax_debt")
        credit = len(company.get("credits"))
        inventory_capacity = f"{warehouses.get('resources_amount')}/{warehouses.get('max_warehouse_size')}"
        
        return self.content.format(
            balance=balance,
            reputation=reputation,
            tax=tax,
            credit=credit,
            inventory_capacity=inventory_capacity,
            contract_new=contract_new,
            contract_not_delivered=contract_not_delivered
        )
        