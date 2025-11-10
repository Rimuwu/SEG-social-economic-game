from scenes.utils.oneuser_page import OneUserPage
from modules.utils import create_buttons
from aiogram.types import CallbackQuery
from modules.ws_client import get_company_contracts, get_contract, get_company, get_contracts
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ContractViewMyPage(OneUserPage):
    
    __page_name__ = "contract-view-my-page"
    __for_blocked_pages__ = ["contract-main-page"]
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "view") is None:
            await self.scene.update_key(self.__page_name__, "view", False)
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
        if self.scene.get_key(self.__page_name__, "selected_contract_id") is None:
            await self.scene.update_key(self.__page_name__, "selected_contract_id", None)
    
    async def content_worker(self):
        view = self.scene.get_key(self.__page_name__, "view")
        if view:
            contract_id = self.scene.get_key(self.__page_name__, "selected_contract_id")
            contract = await get_contract(id=int(contract_id))
            print(contract)
            who_create_id = contract.get("who_creator")
            if contract.get('supplier_company_id') == who_create_id:
                role_text = "Вы - поставщик"
                suplier = await get_company(who_create_id)
                customer = await get_company(contract.get('customer_company_id'))
            else:
                role_text = "Вы - покупатель"
                customer = await get_company(who_create_id)
                suplier = await get_company(contract.get('supplier_company_id'))
            suplier_name = suplier.get('name')
            customer_name = customer.get('name')
            resource = RESOURCES.get_resource(contract.get('resource'))
            
            text = ""
            if contract.get("accepted"):
                text = f"🚚 Доставлен: {'Да' if contract.get('delivered_this_turn') else 'Нет'}"
            return self.content.format(
                c_id=contract.get("id"),
                resource_label=f"{resource.emoji} {resource.label}",
                role_text=role_text,
                supplier_company_name=suplier_name,
                customer_company_name=customer_name,
                amount_text=contract.get('amount_per_turn'),
                duration_text=contract.get('duration_turns'),
                payment_text=contract.get('payment_amount'),
                accepted='Да' if contract.get("accepted") else "Нет"
                ) + text
        return "📋 Выберите контракт для просмотра"

    
    async def buttons_worker(self):
        view = self.scene.get_key(self.__page_name__, "view")
        page = self.scene.get_key(self.__page_name__, "page")
        buttons = []
        if view:
            buttons.append(create_buttons(self.scene.__scene_name__, "↪ К выбору", "back_to_s", ignore_row=True))
        else:
            company_id = self.scene.get_key("scene", "company_id")
            session_id = self.scene.get_key("scene", "session")
            contracts_list = await get_contracts(session_id=session_id)
            print(contracts_list)
            contracts = []
            for c in contracts_list:
                if c.get("supplier_company_id") == company_id or c.get("customer_company_id"):
                    contracts.append(c)
            items_per_page = 5
            total_pages = max(1, (len(contracts) + items_per_page - 1) // items_per_page)
            page %= total_pages
            await self.scene.update_key(self.__page_name__, "page", page)

            start = page * items_per_page
            end = start + items_per_page
            page_contracts = contracts[start:end]
            self.row_width = 3
            if not page_contracts:
                buttons.append(
                    {"text": "Контракты отсутствуют", "callback_data": "non", "ignore_row": True,})
                buttons.append(
                    {
                        "text": "↪️ В меню",
                        "callback_data": callback_generator(
                            self.scene.__scene_name__, "to_page", "contract-main-page"
                        ),
                        "ignore_row": True,
                    }
                )
            else:
                for contract in page_contracts:
                    text = (
                        f"• #{contract.get('id')} — {RESOURCES.get_resource(contract.get('resource')).emoji}  {RESOURCES.get_resource(contract.get('resource')).label}"
                    )
                    buttons.append(
                        {
                            "text": text,
                            "callback_data": callback_generator(
                                self.scene.__scene_name__,
                                "select_contract",
                                str(contract.get("id")),
                            ),
                            "ignore_row": True,
                        }
                    )
                if len(contracts) > items_per_page:
                    buttons.append(
                        {
                            "text": "◀️ Назад",
                            "callback_data": callback_generator(
                                self.scene.__scene_name__, "contracts_prev_page"
                            ),
                        }
                    )
                    buttons.append(
                        {
                            "text": f"📄 {page + 1}/{total_pages}",
                            "callback_data": callback_generator(
                                self.scene.__scene_name__, "contracts_page_info"
                            ),
                        }
                    )
                    buttons.append(
                        {
                            "text": "Вперёд ▶️",
                            "callback_data": callback_generator(
                                self.scene.__scene_name__, "contracts_next_page"
                            ),
                        }
                    )
                buttons.append(
                    {
                        "text": "↪️ В меню",
                        "callback_data": callback_generator(
                            self.scene.__scene_name__, "to_page", "contract-main-page"
                        ),
                        "ignore_row": True,
                    }
                )
        return buttons
    
    @OneUserPage.on_callback("contracts_next_page")
    async def next_page(self, callback: CallbackQuery, args):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        company_id = self.scene.get_key("scene", "company_id")
        session_id = self.scene.get_key("scene", "session")
        contracts_list = await get_contracts(session_id=session_id)
        contracts = []
        for c in contracts_list:
            if c.get("who_creator") == company_id:
                contracts.append(c)
        items_per_page = 5
        total_pages = max(1, (len(contracts) + items_per_page - 1) // items_per_page)
        await self.scene.update_key(
            self.__page_name__, "page", (page_index + 1) % total_pages
        )
        await self.scene.update_message()

    @OneUserPage.on_callback("contracts_prev_page")
    async def prev_page(self, callback: CallbackQuery, args):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        company_id = self.scene.get_key("scene", "company_id")
        session_id = self.scene.get_key("scene", "session")
        contracts_list = await get_contracts(session_id=session_id)
        contracts = []
        for c in contracts_list:
            if c.get("who_creator") == company_id:
                contracts.append(c)
        items_per_page = 5
        total_pages = max(1, (len(contracts) + items_per_page - 1) // items_per_page)
        await self.scene.update_key(
            self.__page_name__, "page", (page_index - 1) % total_pages
        )
        await self.scene.update_message()
    
    @OneUserPage.on_callback("select_contract")
    async def select_contract(self, callback: CallbackQuery, args):
        contract_id = args[1]
        await self.scene.update_key(self.__page_name__, "view", True)
        await self.scene.update_key(self.__page_name__, "selected_contract_id", contract_id)
        await self.scene.update_message()
    
    
    @OneUserPage.on_callback("back_to_s")
    async def back_to_s(self, callback: CallbackQuery, args):
        await self.scene.update_key(self.__page_name__, "view", False)
        await self.scene.update_key(self.__page_name__, "selected_contract_id", None)
        await self.scene.update_message()