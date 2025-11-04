from scenes.utils.filter_item import ItemFilter
from oms.utils import callback_generator
from modules.ws_client import create_contract, get_companies
from modules.utils import create_buttons
from aiogram.types import CallbackQuery, Message
from global_modules.load_config import ALL_CONFIGS, Resources
import json


RESOURCES: Resources = ALL_CONFIGS["resources"]

class ContractCreatePage(ItemFilter):
    __page_name__ = "contract-create-page"
    
    
    async def data_preparate(self):
        data = self.scene.get_data("scene")
        if self.scene.get_key("contract-create-page", "state") is None:
            await self.scene.update_key("contract-create-page", "settings", json.dumps({
                "supplier_company_id": None,
                "customer_company_id": None,
                "session_id": data["session"],
                "resource": None,
                "amount_per_turn": None,
                "duration_turns": None,
                "payment_amount": None,
                "who_creator": data["company_id"],
            }))
        if self.scene.get_key("contract-create-page", "state") is None:
            await self.scene.update_key("contract-create-page", "state", "select_role")
        if self.scene.get_key("contract-create-page", "page_company") is None:
            await self.scene.update_key("contract-create-page", "page_company", 0)
        if self.scene.get_key("contract-create-page", "max_page_company") is None:
            await self.scene.update_key("contract-create-page", "max_page_company", 0)
        if self.scene.get_key("contract-create-page", "page_resource") is None:
            await self.scene.update_key("contract-create-page", "page_resource", 0)
        if self.scene.get_key("contract-create-page", "max_page_resource") is None:
            await self.scene.update_key("contract-create-page", "max_page_resource", 0)
        if self.scene.get_key("contract-create-page", "error") is None:
            await self.scene.update_key("contract-create-page", "error", "")
        if self.scene.get_key("scene", "page_filter_item") is None:
            await self.scene.update_key("scene", "page_filter_item", 0)
    
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
                page = self.scene.get_key("scene", "page_filter_item")
                return f"Выберите нужный ресурс ниже:\n Текущая страница: {page + 1}/5"
            return "Выберите ресурс для контракта:"
        if state == "input_amount_per_turn":
            text = "Введите количество ресурса, которое будет передаваться за ход:"
            if error != "":
                return f"{text}{error}"
            await self.scene.update_key("contract-create-page", "error", "")
            return text
        if state == "input_duration_turns":
            return "Введите длительность контракта в ходах:"
        if state == "input_payment_amount":
            return "Введите сумму оплаты за выполнение контракта:"
    
    
    async def buttons_worker(self):
        state = self.scene.get_key("contract-create-page", "state")
        page = self.scene.get_key("contract-create-page", "page_company")
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        buttons = []
        self.row_width = 2
        if state == "select_role":
            buttons.append(create_buttons(self.scene.__scene_name__, "Поставщик", "contract_create_select_role", "supplier"))
            buttons.append(create_buttons(self.scene.__scene_name__, "Покупатель", "contract_create_select_role", "customer"))
        elif state == "select_company":
            container = []
            companies = await get_companies(session_id=settings.get("session_id"))
            for company in companies:
                company_id = company.get("id")
                company_name = company.get("name")
                if company_id != settings.get("who_creator"):
                    container.append(create_buttons(self.scene.__scene_name__, company_name, "contract_create_select_company", company_id, ignore_row=True))
            await self.scene.update_key("contract-create-page", "max_page_company", ((((len(container)) // 5) + 1) if (len(container)) % 5 != 0 else (len(container)) // 5) - 1)
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
                self.row_width = 3
                buttons = []
                page_buttons = []
                container = []
                page_container = 0
                cur_page = self.scene.get_key("scene", "page_filter_item")
                for key, res in RESOURCES.get_raw_resources().items():
                    container.append({
                        "text": f"{res.emoji} {res.label}",
                        "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "item_select",
                        key
                        ),
                        "ignore_row": True
                        })
                    page_container += 1
                    if page_container == 4:
                        page_container = 0
                        page_buttons.append(container)
                        container = []

                for key, res in RESOURCES.get_produced_resources().items():
                    container.append({
                        "text": f"{res.emoji} {res.label}",
                        "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "item_select",
                        key
                        ),
                        "ignore_row": True
                        })
                    page_container += 1
                    if page_container == 4:
                        page_container = 0
                        page_buttons.append(container)
                        container = []
                for i in page_buttons[cur_page]:
                    buttons.append(i)
                
                buttons.append({
                    "text": "⬅️ Назад",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "back_page"
                    )
                    })
                buttons.append({
                    "text": f"{cur_page + 1}/{len(page_buttons)}",
                    "callback_data": "ignore"
                })
                buttons.append({
                    "text": "Вперёд ➡️",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "next_page"
                    )})
            elif settings.get("who_creator") == settings.get("customer_company_id"):
                pass
        
        buttons.append(create_buttons(self.scene.__scene_name__, "↩️ Сбросить", "reset", ignore_row=True))
        if state == "select_role":
            buttons.append(create_buttons(self.scene.__scene_name__, "↩️ Назад", "to_page", "contract-main-page", ignore_row=True))
        return buttons
    
    @ItemFilter.on_text('int')
    async def int_input(self, message: Message, value: int):
        state = self.scene.get_key("contract-create-page", "state")
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        
        if state == "input_amount_per_turn":
            if value <= 0:
                await self.scene.update_key("contract-create-page", "error", "\nКоличество должно быть больше нуля. Повторите ввод.")
                await self.scene.update_message()

    @ItemFilter.on_callback("next_page")
    async def next_page(self, callback: CallbackQuery, args: list):
        state = self.scene.get_key("contract-create-page", "state")
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        if state == "select_resource":
            if settings.get("who_creator") == settings.get("supplier_company_id"):
                cur_page = self.scene.get_key("scene", "page_filter_item")
                if cur_page + 1 > 4:
                    await self.scene.update_key("scene", "page_filter_item", 0)
                else:
                    await self.scene.update_key("scene", "page_filter_item", cur_page + 1)
                await self.scene.update_message()
        elif state == "select_company":
            page = self.scene.get_key("contract-create-page", "page_company")
            max_page = self.scene.get_key("contract-create-page", "max_page_company")
            if page + 1 > max_page:
                await self.scene.update_key("contract-create-page", "page_company", 0)
            else:
                await self.scene.update_key("contract-create-page", "page_company", page + 1)
    
    @ItemFilter.on_callback("back_page")
    async def back_page(self, callback: CallbackQuery, args: list):
        state = self.scene.get_key("contract-create-page", "state")
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        if state == "select_resource":
            if settings.get("who_creator") == settings.get("supplier_company_id"):
                cur_page = self.scene.get_key("scene", "page_filter_item")
                if cur_page - 1 < 0:
                    await self.scene.update_key("scene", "page_filter_item", 3)
                else:
                    await self.scene.update_key("scene", "page_filter_item", cur_page - 1)
                await self.scene.update_message()
        elif state == "select_company":
            page = self.scene.get_key("contract-create-page", "page_company")
            max_page = self.scene.get_key("contract-create-page", "max_page_company")
            if page - 1 < 0:
                await self.scene.update_key("contract-create-page", "page_company", max_page)
            else:
                await self.scene.update_key("contract-create-page", "page_company", page - 1)

    @ItemFilter.on_callback("contract_create_select_role")
    async def select_role(self, callback: CallbackQuery, args: list):
        role = args[1]
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        if role == "supplier":
            settings["supplier_company_id"] = settings["who_creator"]
        elif role == "customer":
            settings["customer_company_id"] = settings["who_creator"]
        await self.scene.update_key("contract-create-page", "settings", json.dumps(settings))
        await self.scene.update_key("contract-create-page", "state", "select_company")
        await self.scene.update_message()
    
    @ItemFilter.on_callback("contract_create_select_company")
    async def select_company(self, callback: CallbackQuery, args: list):
        company_id = args[1]
        settings = json.loads(self.scene.get_key("contract-create-page", "settings"))
        if settings.get("who_creator") == settings.get("supplier_company_id"):
            settings["customer_company_id"] = company_id
        elif settings.get("who_creator") == settings.get("customer_company_id"):
            settings["supplier_company_id"] = company_id
        await self.scene.update_key("contract-create-page", "settings", json.dumps(settings))
        await self.scene.update_key("contract-create-page", "state", "select_resource")
        await self.scene.update_message()
            
    
    @ItemFilter.on_callback("reset")
    async def reset(self, callback: CallbackQuery, args: list):
        data = self.scene.get_data("scene")
        await self.scene.update_key("contract-create-page", "settings", json.dumps({
            "supplier_company_id": None,
            "customer_company_id": None,
            "session_id": data["session"],
            "resource": None,
            "amount_per_turn": None,
            "duration_turns": None,
            "payment_amount": None,
            "who_creator": data["company_id"],
        }))
        await self.scene.update_key("contract-create-page", "state", "select_role")
        await self.scene.update_key("contract-create-page", "page_company", 0)
        await self.scene.update_key("contract-create-page", "max_page_company", 0)
        await self.scene.update_key("contract-create-page", "page_resource", 0)
        await self.scene.update_key("contract-create-page", "max_page_resource", 0)
        await self.scene.update_key("contract-create-page", "error", "")
        await self.scene.update_key("scene", "page_filter_item", 0)