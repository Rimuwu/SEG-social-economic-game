from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from modules.ws_client import get_city, get_company, sell_to_city
from global_modules.load_config import ALL_CONFIGS, Resources

RESOURCE: Resources = ALL_CONFIGS["resources"]


class CitySell(OneUserPage):
    __page_name__ = "city-sell-page"
    __for_blocked_pages__ = ["city-main-page"]
    
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "bool") is None:
            await self.scene.update_key(self.__page_name__, "bool", False)
        if self.scene.get_key(self.__page_name__, "is_company_have") is None:
            await self.scene.update_key(self.__page_name__, "is_company_have", False)
        if self.scene.get_key(self.__page_name__, "error") is None:
            await self.scene.update_key(self.__page_name__, "error", "")

    async def content_worker(self):
        city_id = self.scene.get_key("city-main-page", "select_city_id")
        company_id = self.scene.get_key("scene", "company_id")
        resource_id = self.scene.get_key("city-view-page", "selected_resource")
        session_id = self.scene.get_key("scene", "session")
        city_data = await get_city(id=int(city_id), session_id=session_id)

        resource = RESOURCE.get_resource(resource_id)
        demand = city_data.get("demands").get(resource_id)
        max_amount = demand.get("amount")
        price = demand.get("price")
        city_name = city_data.get("name")
        company_data = await get_company(id=company_id)
        company_amount = 0
        if company_data.get("warehouses").get(resource_id) is not None:
            company_amount = company_data.get("warehouses").get(resource_id)
            await self.scene.update_key(self.__page_name__, "is_company_have", True)
        else:
            await self.scene.update_key(self.__page_name__, "is_company_have", False)

        label = resource.label 
        emoji = resource.emoji
        resource = f"{emoji} {label}"
        content = self.content.format(
            city_name=city_name,
            resource=resource,
            max_amount=max_amount,
            price=price,
            сompany_amount=company_amount
        )
        if self.scene.get_key(self.__page_name__, "bool"):
            content += "\n\nВведите количество товара для продажи или выберите с помощью кнопок:"
    
        return content
    async def buttons_worker(self):
        city_id = self.scene.get_key("city-main-page", "select_city_id")
        resource_id = self.scene.get_key("city-view-page", "selected_resource")
        company_id = self.scene.get_key("scene", "company_id")
        session_id = self.scene.get_key("scene", "session")
        buttons = []
        bool_val = self.scene.get_key(self.__page_name__, "bool")
        is_company_have = self.scene.get_key(self.__page_name__, "is_company_have")
        if is_company_have:
            if not bool_val:
                buttons.append({
                    "text": "💰 Продать",
                    "callback_data": callback_generator(self.scene.__scene_name__, "sell_start")
                })
            else:
                self.row_width = 4
                city_data = await get_city(id=int(city_id), session_id=session_id)
                company_data = await get_company(id=company_id)
                demand = city_data.get("demands").get(resource_id)
                max_amount = demand.get("amount")
                company_amount = company_data.get("warehouses").get(resource_id)
                cur_count = min(4, company_amount)
                cur_count = min(cur_count, max_amount)
                cur_warehouses = min(max_amount, company_amount)
                
                for i in range(1, cur_count + 1):
                    amount = (cur_warehouses * i) // cur_count
                    text = f"{amount}"
                    buttons.append({
                        "text": text,
                        "callback_data": callback_generator(self.scene.__scene_name__, "sell_confirm", str(amount))
                    })
        buttons.append({
            "text": "⬅️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "back"),
            "ignore_row": True
        })
    
        return buttons

    @OneUserPage.on_callback("sell_start")
    async def sell_start(self, callback, args):
        await self.scene.update_key(self.__page_name__, "bool", True)
        await self.scene.update_message()

    @OneUserPage.on_callback("sell_confirm")
    async def sell_confirm(self, callback, args):
        amount = int(args[1])
        city_id = self.scene.get_key("city-main-page", "select_city_id")
        resource_id = self.scene.get_key("city-view-page", "selected_resource")
        company_id = self.scene.get_key("scene", "company_id")
        result = await sell_to_city(
            city_id=int(city_id),
            company_id=company_id,
            resource_id=resource_id,
            amount=amount
        )
        if not result:
            await callback.answer("❌ Ошибка при продаже товара", show_alert=True)
            return
        await callback.answer("✅ Товар успешно продан!", show_alert=True)
        await self.scene.update_key(self.__page_name__, "bool", False)
        await self.scene.update_key(self.__page_name__, "error", "")
        await self.scene.update_page("city-view-page")
    
    @OneUserPage.on_callback("back")
    async def back_callback(self, callback, args: list):
        await self.scene.update_key(self.__page_name__, "error", "")
        await self.scene.update_key(self.__page_name__, "bool", False)
        await self.scene.update_key(self.__page_name__, "is_company_have", False)
        await self.scene.update_page("city-view-page")

    @OneUserPage.on_text("int")
    async def handle_int(self, message, value: int):
        amount = value
        city_id = self.scene.get_key("city-main-page", "select_city_id")
        resource_id = self.scene.get_key("city-view-page", "selected_resource")
        company_id = self.scene.get_key("scene", "company_id")
        result = await sell_to_city(
            city_id=int(city_id),
            company_id=company_id,
            resource_id=resource_id,
            amount=amount
        )
        if not result:
            await self.scene.update_key(self.__page_name__, "error", "❌ Ошибка при продаже товара")
            await self.scene.update_message()
            return
        await self.scene.update_key(self.__page_name__, "error", "✅ Товар успешно продан!")
        await self.scene.update_key(self.__page_name__, "bool", False)
        await self.scene.update_message()