from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from modules.ws_client import get_city
from global_modules.load_config import ALL_CONFIGS, Resources


RESOURCE: Resources = ALL_CONFIGS["resources"]


class CityView(OneUserPage):
    
    __page_name__ = "city-view-page"
    __for_blocked_pages__ = ["city-main-page"]
    
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
        if self.scene.get_key(self.__page_name__, "selected_resource") is None:
            await self.scene.update_key(self.__page_name__, "selected_resource", None)
    
    async def content_worker(self):
        city_id = self.scene.get_key("city-main-page", "select_city_id")
        session_id = self.scene.get_key("scene", "session")
        city_data = await get_city(id=int(city_id), session_id=session_id)

        name = city_data.get("name")
        branch_id = city_data.get("branch")
        branch_data = RESOURCE.get_resource(branch_id)
        
        branch = f"{branch_data.emoji} {branch_data.label}"
        demands = city_data.get("demands", {})
        return self.content.format(
           city_name=name,
           branch=branch,
           count_demand=len(demands)
        )
    
    async def buttons_worker(self):
        buttons = []
        self.row_width = 3
        city_id = self.scene.get_key("city-main-page", "select_city_id")
        session_id = self.scene.get_key("scene", "session")
        city_data = await get_city(int(city_id), session_id)
        demands = city_data.get("demands")
        demand_keys = list(demands.keys())
        resource_chunks = [demand_keys[i:i + 4] for i in range(0, len(demand_keys), 4)]
        current_page = self.scene.get_key(self.__page_name__, "page")
        for resource_key in resource_chunks[current_page]:
            resource = RESOURCE.get_resource(resource_key)
            demand = demands.get(resource_key, {})
            amount = demand.get("amount", 0)
            label = resource.label if resource else resource_key
            emoji = resource.emoji if resource else "📦"
            buttons.append({
                "text": f"{emoji} {label} ({amount})",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_view_product", resource_key),
                "ignore_row": True
            })
        if len(resource_chunks) > 1:
            buttons.append({
                "text": "◀️",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_products_prev")
            })
            buttons.append({
                "text": f"{current_page + 1}/{len(resource_chunks)}",
                "callback_data": callback_generator(self.scene.__scene_name__, "noop")
            })
            buttons.append({
                "text": "▶️",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_products_next")
            })

        buttons.append({
            "text": "⬅️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_main_page")
        })
        
        return buttons
    
    @OneUserPage.on_callback("city_view_product")
    async def on_city_view_product(self, callback, args):
        resource_key = args[1]
        await self.scene.update_key(self.__page_name__, "selected_resource", resource_key)
        await self.scene.update_page("city-sell-page")
    
    @OneUserPage.on_callback('city_products_prev')
    async def city_products_prev_callback(self, callback, args: list):
        page = self.scene.get_key(self.__page_name__, "page")
        if page - 1 < 0:
            await callback.answer()
            return
        await self.scene.update_key(self.__page_name__, "page", page - 1)
        await self.scene.update_message()
        

    @OneUserPage.on_callback('city_products_next')
    async def city_products_next_callback(self, callback, args: list):
        page = self.scene.get_key(self.__page_name__, "page")
        if page + 1 > 3:
            await callback.answer()
            return
        await self.scene.update_key(self.__page_name__, "page", page + 1)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("back_main_page")
    async def back_main_page_callback(self, callback, args: list):
        await self.scene.update_key("city-main-page", "select_city_id", None)
        await self.scene.update_page("city-main-page")