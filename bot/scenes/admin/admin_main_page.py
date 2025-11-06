from oms import Page
from modules.utils import create_buttons


class AdminMainPage(Page):
    __page_name__ = "admin-main-page"
    
    
    async def buttons_worker(self):
        self.row_width = 2
        buttons = [
            create_buttons(self.scene.__scene_name__, "↪️ Сессии", "to_pages", "admin-session-main-page"),
            create_buttons(self.scene.__scene_name__, "↪️ Компании", "to_pages", "admin-company-main-page"),
            create_buttons(self.scene.__scene_name__, "↪️ Пользователи", "to_pages", "admin-user-main-page"),
            create_buttons(self.scene.__scene_name__, "↪️ Обратно в игру", "back", ignore_row=True)
        ]
        return buttons
    
    
    @Page.on_callback("back")
    async def back_to_previous(self, callback, args: list):
        page = self.scene.get_key("scene", "previous_page")
        await self.scene.update_page(page)