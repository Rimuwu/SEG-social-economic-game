from oms import Page
from aiogram.types import Message, CallbackQuery
from modules.ws_client import get_company, get_company_contracts, get_company_warehouse, get_session, get_session_event, get_contracts
from global_modules.load_config import ALL_CONFIGS, Events


EVENT: Events = ALL_CONFIGS["events"]

class MainPage(Page):

    __page_name__ = 'main-page'

    async def data_preparate(self):
        session_id = self.scene.get_key("scene", "session")
        company_id = self.scene.get_key("scene", "company_id")
        # Загружаем все необходимые данные заранее
        s = await get_session(session_id=session_id)
        company = await get_company(id=company_id)
        warehouses = await get_company_warehouse(company_id=company_id)
        contracts = await get_contracts(session_id=session_id)
        ev = await get_session_event(session_id=session_id)

        # Сохраняем кэшированные данные
        await self.scene.update_key(self.__page_name__, "session_data", s)
        await self.scene.update_key(self.__page_name__, "company_data", company)
        await self.scene.update_key(self.__page_name__, "warehouses_data", warehouses)
        await self.scene.update_key(self.__page_name__, "contracts_data", contracts)
        await self.scene.update_key(self.__page_name__, "event_data", ev)

        # Отслеживаем максимум таймера до следующей стадии, чтобы строить прогресс-бар
        if self.scene.get_key(self.__page_name__, "max_time") is None:
            await self.scene.update_key(self.__page_name__, "max_time", s.get("time_to_next_stage"))
        else:
            await self.scene.update_key(
                self.__page_name__,
                "max_time",
                max(s.get("time_to_next_stage"), self.scene.get_key(self.__page_name__, "max_time"))
            )

    async def content_worker(self) -> str:
        company_id = self.scene.get_key("scene", "company_id")
        session_id = self.scene.get_key("scene", "session")
        s = self.scene.get_key(self.__page_name__, "session_data")
        company = self.scene.get_key(self.__page_name__, "company_data")
        warehouses = self.scene.get_key(self.__page_name__, "warehouses_data")
        contracts = self.scene.get_key(self.__page_name__, "contracts_data")
        contract_new = 0
        contract_not_delivered = 0
        for c in contracts:
            if c.get("who_creator") != company_id and c.get("accepted") == False:
                contract_new += 1
            if c.get("supplier_company_id") == company_id and c.get("accepted") == True and c.get("delivered_this_turn") == False and c.get("created_at_step") != s.get("step"):
                contract_not_delivered += 1
                
        balance = company.get("balance")
        reputation = company.get("reputation")
        tax = company.get("tax_debt")
        credit = len(company.get("credits"))
        inventory_capacity = f"{warehouses.get('resources_amount')}/{warehouses.get('max_warehouse_size')}"
        time_to_next_stage = s.get("time_to_next_stage")
        time = f"{time_to_next_stage // 60} мин {time_to_next_stage % 60} сек"
        max_time = self.scene.get_key(self.__page_name__, "max_time")
        field = int(((max_time - time_to_next_stage) / max_time) * 15)
        progress_bar = "█" * field + "░" * (15 - field)
        ev = self.scene.get_key(self.__page_name__, "event_data")
        event_text = "Нет"
        if ev["event"] != {}:
            event_text = ev["event"]["name"]
        return self.content.format(
            balance=balance,
            reputation=reputation,
            tax=tax,
            credit=credit,
            inventory_capacity=inventory_capacity,
            contract_new=contract_new,
            contract_not_delivered=contract_not_delivered,
            event_text=event_text,
            time=time,
            progress_bar=progress_bar
        )
        