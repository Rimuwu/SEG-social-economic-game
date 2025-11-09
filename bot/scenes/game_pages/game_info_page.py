from oms import Page
from aiogram.types import Message, CallbackQuery
from oms.utils import callback_generator
from oms import scene_manager
from bot_instance import bot


class GameInfo(Page):
    __page_name__ = 'game-info-page'
    
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
        current_page = self.scene.get_key(self.__page_name__, "page")
        images = ["img/about_turn.png", "img/cellselect_start.png", "img/main_company.png", "img/inventory.png", "img/contracts.png", "img/upgrade.png", "img/cities.png", "img/exchange.png", "img/bank.png", "img/prison.png", "img/mejturn.png"]
        self.image = images[current_page]
    
    
    async def content_worker(self):
        pages = self.content.split("|||")
        current_page = self.scene.get_key(self.__page_name__, "page")
        return pages[current_page]

    
    async def buttons_worker(self):
        current_page = self.scene.get_key(self.__page_name__, "page")
        total_pages = len(self.content.split("|||"))
        self.row_width = 2
        buttons = []
        
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'game_info_prev'
            )
        })
    
        buttons.append({
            'text': '➡️ Вперёд',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'game_info_next'
            )
        })
        
        buttons.append({
            'text': '🎮 Подключиться к игре',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'connect_game'
            )
        })
        
        return buttons

    @Page.on_callback('game_info_prev')
    async def game_info_prev(self, callback: CallbackQuery, args: list):
        """Переход на предыдущую страницу информации об игре"""
        current_page = self.scene.get_key(self.__page_name__, "page")
        if current_page > 0:
            await self.scene.update_key(self.__page_name__, "page", current_page - 1)
            await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('game_info_next')
    async def game_info_next(self, callback: CallbackQuery, args: list):
        """Переход на следующую страницу информации об игре"""
        current_page = self.scene.get_key(self.__page_name__, "page")
        total_pages = len(self.content.split("|||"))
        if current_page < total_pages - 1:
            await self.scene.update_key(self.__page_name__, "page", current_page + 1)
            await self.scene.update_message()
        await callback.answer()
    
    
    @Page.on_callback('connect_game')
    async def connect_game_handler(self, callback: CallbackQuery, args: list):
        """Обработчик подключения к игре"""
        from scenes.game_scenario import GameManager
        
        # Переходим на страницу ввода кода сессии
        await self.scene.end()
        n_scene = scene_manager.create_scene(
        callback.from_user.id,
        GameManager,
        bot
        )
        await n_scene.start()
        await callback.answer()