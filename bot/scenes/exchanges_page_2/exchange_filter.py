from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery
from modules.ws_client import get_exchanges
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources
from scenes.filters.item_filter import ItemFilter

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeFilter(OneUserPage):
    """Страница фильтра по ресурсам"""
    
    __page_name__ = "exchange-filter-page"
    
    def __after_init__(self):
        """Инициализация фильтра предметов"""
        super().__after_init__()
        # Создаём фильтр предметов для этой страницы
        self.item_filter = ItemFilter(
            scene_name='scene-manager',  # Будет установлено в __post_init__
            callback_prefix='filter_resource',
            items_per_page=5
        )
    
    def __post_init__(self):
        """Установка имени сцены для фильтра"""
        super().__post_init__()
        self.item_filter.scene_name = self.scene.__scene_name__
    
    async def content_worker(self):
        """Экран фильтра по ресурсам"""
        return self.content
    
    async def buttons_worker(self):
        """Кнопки фильтра"""
        scene_data = self.scene.get_data('scene')
        filter_page = scene_data.get('filter_page', 0)
        
        buttons = []
        self.row_width = 3
        
        # Получаем кнопки фильтра
        filter_buttons = self.item_filter.get_buttons(
            current_page=filter_page,
            add_reset_button=True,
            reset_callback='reset_filter'
        )
        buttons.extend(filter_buttons)
        
        # Кнопка "Назад к списку"
        buttons.append({
            'text': '↪️ Назад к списку',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_to_list'
            ),
            'next_line': True
        })
        
        return buttons
    
    @OneUserPage.on_callback('filter_page')
    async def filter_page_handler(self, callback: CallbackQuery, args: list):
        """Переключение страницы фильтра"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        page = int(args[1])
        scene_data = self.scene.get_data('scene')
        
        scene_data['filter_page'] = page
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @OneUserPage.on_callback('filter_resource')
    async def filter_resource_handler(self, callback: CallbackQuery, args: list):
        """Применение фильтра по ресурсу"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ресурс", show_alert=True)
            return
        
        resource_id = args[1]
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('session')
        
        # Проверяем существование ресурса
        if not self.item_filter.resource_exists(resource_id):
            await callback.answer("❌ Ресурс не найден", show_alert=True)
            return
        
        # Проверяем, есть ли предложения с этим ресурсом
        exchanges = await get_exchanges(
            session_id=session_id,
            sell_resource=resource_id
        )
        
        if isinstance(exchanges, str) or not exchanges or len(exchanges) == 0:
            resource_name = self.item_filter.get_resource_name(resource_id)
            await callback.answer(
                f"❌ Нет предложений с ресурсом {resource_name}",
                show_alert=True
            )
            return
        
        # Применяем фильтр
        scene_data['filter_resource'] = resource_id
        scene_data['list_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        resource_name = self.item_filter.get_resource_name(resource_id)
        await self.scene.update_page('exchange-main-page')
        await callback.answer(f"✅ Поиск: {resource_name}")
    
    @OneUserPage.on_callback('reset_filter')
    async def reset_filter_handler(self, callback: CallbackQuery, args: list):
        """Сброс фильтра"""
        scene_data = self.scene.get_data('scene')
        
        scene_data['filter_resource'] = None
        scene_data['list_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('exchange-main-page')
        await callback.answer("🔄 Поиск сброшен")
    
    @OneUserPage.on_callback('back_to_list')
    async def back_to_list_handler(self, callback: CallbackQuery, args: list):
        """Возврат к списку предложений"""
        await self.scene.update_page('exchange-main-page')
        await callback.answer()
