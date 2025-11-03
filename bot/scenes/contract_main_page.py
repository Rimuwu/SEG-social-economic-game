from .oneuser_page import OneUserPage
from modules.ws_client import get_contracts, create_contract, accept_contract,execute_contract, cancel_contract, get_company_contracts
from oms.utils import callback_generator


Page = OneUserPage


class ContractMainPage(Page):
    __page_name__ = "contract-main-page"
    
    async def content_worker(self):
        data = self.scene.get_data('scene')
        company_id = data.get('company_id')
        contracts_as_supplier = await get_company_contracts(company_id=company_id, as_supplier=True)
        contracts_as_customer = await get_company_contracts(company_id=company_id, as_customer=True)
        k = 0
        for n in contracts_as_customer:
            if n.get("accepted"):
                k += 1
        for n in contracts_as_supplier:
            if n.get("accepted"):
                k += 1
        
        text = "📄 *Контракты*\n\n"
        text += f"🔹 *Контракты, где вы поставщик:* {len(contracts_as_supplier)}\n"
        text += f"🔹 *Контракты, где вы заказчик:* {len(contracts_as_customer)}\n"
        text += f"🔹 *Принятые контракты:* {k}\n\n"
        text += "Выберите действие:"

        return text

    async def buttons_worker(self):
        self.row_width = 2
        data = self.scene.get_data('scene')
        company_id = data.get('company_id')
        contracts_as_supplier = await get_company_contracts(company_id=company_id, as_supplier=True)
        contracts_as_customer = await get_company_contracts(company_id=company_id, as_customer=True)
        buttons = []
        flag = True
        if len(contracts_as_supplier) > 0 or len(contracts_as_customer) > 0:
            for cas in contracts_as_supplier:
                if cas.get("who_create") != company_id and flag:
                    flag = False
                    buttons.append({
                    "text": "Предложения",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "to_page",
                        "contract-view-page"
                    )
                    })
                    break
            for cac in contracts_as_customer:
                if cac.get("who_create") != company_id and flag:
                    flag = False
                    buttons.append({
                    "text": "Предложения",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "to_page",
                        "contract-view-page"
                    )
                    })
        buttons.append({
            "text": "Создать",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "to_page",
                "contract-create-page"
            )
        })
        buttons.append({
            "text": "Выполнение контрактов",
            "callback_data": callback_generator(
                self.scene.__scene_name__,
                "to_page",
                "contract-execute-page"
            ),
            "ignore_row": True
        })
        
        return buttons

        # await create_contract(
        #     supplier_company_id = 7,
        # customer_company_id = 8,
        # session_id = "коток",
        # resource = "oil",
        # amount_per_turn = 2,
        # duration_turns = 3,
        # payment_amount = 1000,
        # who_creator = 7 
        # )
        # print(await get_contracts())
        # await accept_contract(4, 8) # or await cancel_contract(4, 8)
        # await execute_contract(4)