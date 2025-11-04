from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources
from aiogram.types import CallbackQuery


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeFilter(OneUserPage):
    __for_blocked_pages__ = ["exchange-sellect-confirm", "exchange-create-page"]
    __page_name__ = "exchange-filter-page"
    
    
    async def data_preparate(self):
        """Инициализация данных фильтра"""
        if self.scene.get_key("exchange-filter-page", "page_number") is None:
            await self.scene.update_key("exchange-filter-page", "page_number", 0)
    
    
    async def content_worker(self):
        """Генерация контента страницы фильтра"""
        text = "🔍 *Фильтр по ресурсам*\n\n"
        text += "Выберите ресурс, чтобы увидеть только предложения с этим товаром:"
        return text
    
    
    async def buttons_worker(self):
        """Генерация кнопок с ресурсами и пагинацией"""
        cur_page = self.scene.get_key("exchange-filter-page", "page_number")
        self.row_width = 1
        buttons = []
        
        # Получаем все ресурсы и сортируем их
        all_resources = []
        for resource_id, resource in RESOURCES.resources.items():
            all_resources.append({
                "id": resource_id,
                "name": resource.label,
                "emoji": resource.emoji,
                "level": resource.lvl
            })
        
        # Сортируем по уровню и имени
        all_resources.sort(key=lambda x: (x["level"], x["name"]))
        
        # Пагинация: 10 элементов на странице
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Нормализуем номер страницы
        cur_page = cur_page % total_pages
        await self.scene.update_key("exchange-filter-page", "page_number", cur_page)
        
        # Получаем элементы для текущей страницы
        start_idx = cur_page * items_per_page
        end_idx = start_idx + items_per_page
        page_resources = all_resources[start_idx:end_idx]
        
        # Создаем кнопки с ресурсами
        for resource in page_resources:
            buttons.append({
                "text": f"{resource['emoji']} {resource['name']}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "select_resource",
                    resource["id"]
                ),
                "ignore_row": True
            })
        
        # Добавляем навигацию
        self.row_width = 3
        buttons.append({
            "text": "◀️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_page"),
        })
        buttons.append({
            "text": f"📄 {cur_page + 1}/{total_pages}",
            "callback_data": callback_generator(self.scene.__scene_name__, "page_info"),
        })
        buttons.append({
            "text": "Вперёд ▶️",
            "callback_data": callback_generator(self.scene.__scene_name__, "next_page"),
        })
        
        # Кнопка возврата
        buttons.append({
            "text": "↩️ Назад к биржам",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_to_main"),
            "ignore_row": True
        })
        
        return buttons
    
    @OneUserPage.on_callback("select_resource")
    async def select_resource(self, callback: CallbackQuery, args: list):
        """Выбор ресурса для фильтрации"""
        resource_id = args[1]
        await self.scene.update_key("exchange-main-page", "filter_resource", resource_id)
        await self.scene.update_key("exchange-main-page", "page_number", 0)
        await self.scene.update_page("exchange-main-page")
    
    @OneUserPage.on_callback("next_page")
    async def next_page(self, callback: CallbackQuery, args: list):
        """Следующая страница"""
        cur_page = self.scene.get_key("exchange-filter-page", "page_number")
        
        # Вычисляем общее количество страниц
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: после последней страницы идет первая
        new_page = (cur_page + 1) % total_pages
        await self.scene.update_key("exchange-filter-page", "page_number", new_page)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("back_page")
    async def back_page(self, callback: CallbackQuery, args: list):
        """Предыдущая страница"""
        cur_page = self.scene.get_key("exchange-filter-page", "page_number")
        
        # Вычисляем общее количество страниц
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: перед первой страницей идет последняя
        new_page = (cur_page - 1) % total_pages
        await self.scene.update_key("exchange-filter-page", "page_number", new_page)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("page_info")
    async def page_info(self, callback: CallbackQuery, args: list):
        """Информация о странице (заглушка)"""
        await callback.answer("Информация о странице")
    
    @OneUserPage.on_callback("back_to_main")
    async def back_to_main(self, callback: CallbackQuery, args: list):
        """Возврат на главную страницу биржи"""
        await self.scene.update_page("exchange-main-page")
