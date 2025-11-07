from .oneuser_page import OneUserPage
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator


RESOURCES: Resources = ALL_CONFIGS["resources"]

class ItemFilter(OneUserPage):    
    
    async def data_preparate(self):
        await self.scene.update_key("scene", "page_filter_item", 0)
    
    async def content_worker(self):
        page = self.scene.get_key("scene", "page_filter_item")
        return f"Выберите нужный ресурс ниже:\n Текущая страница: {page + 1}/4"
    
    
    async def buttons_worker(self):
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
                "next_line": True
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
            ),
            "ignore_row": True
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
        return buttons

    @OneUserPage.on_callback("next_page")
    async def next_page(self):
        cur_page = self.scene.get_key("scene", "page_filter_item")
        if cur_page + 1 > 3:
            await self.scene.update_key("scene", "page_filter_item", 0)
        else:
            await self.scene.update_key("scene", "page_filter_item", cur_page + 1)
        await self.scene.update_message()
    
    
    @OneUserPage.on_callback("back_page")
    async def back_page(self):
        cur_page = self.scene.get_key("scene", "page_filter_item")
        if cur_page - 1 < 0:
            await self.scene.update_key("scene", "page_filter_item", 3)
        else:
            await self.scene.update_key("scene", "page_filter_item", cur_page - 1)
        await self.scene.update_message()