from oms import Page
from aiogram.types import Message, CallbackQuery
from oms.utils import callback_generator
from global_modules.logs import Logger
from global_modules.load_config import ALL_CONFIGS, Resources

bot_logger = Logger.get_logger("bot")
RESOURCES: Resources = ALL_CONFIGS["resources"]


class FactoryRekitResource(Page):
    __page_name__ = "factory-rekit-resource"
    
    async def data_preparate(self):
        """Инициализация данных пагинации"""
        scene_data = self.scene.get_data('scene')
        if 'rekit_resource_page' not in scene_data:
            scene_data['rekit_resource_page'] = 0
            await self.scene.set_data('scene', scene_data)
    
    async def content_worker(self):
        """Показать список ресурсов для перекомплектации"""
        scene_data = self.scene.get_data('scene')
        group_type = scene_data.get('rekit_group')
        count_str = scene_data.get('rekit_count')
        
        if not group_type or not count_str:
            return "❌ Ошибка: данные о перекомплектации не найдены"
        
        # Формируем текст о текущей группе
        if group_type == 'idle':
            group_name = "⚪️ Простаивающие заводы"
        else:
            resource = RESOURCES.get_resource(group_type)
            group_name = f"{resource.emoji} {resource.label}" if resource else group_type
        
        count_display = "все" if count_str == "all" else count_str
        
        current_group_text = f"Группа: {group_name}\nКоличество: *{count_display}*\n"
        
        return self.content.format(current_group_text=current_group_text)
    
    async def buttons_worker(self):
        """Кнопки с доступными ресурсами (только производимые, без сырья) с пагинацией"""
        scene_data = self.scene.get_data('scene')
        cur_page = scene_data.get('rekit_resource_page', 0)
        
        buttons = []
        self.row_width = 1
        
        # Получаем только производимые ресурсы (без raw=true)
        produced_resources_keys = RESOURCES.get_produced_resources()
        
        # Формируем список ресурсов с данными для сортировки
        all_resources = []
        for resource_key in produced_resources_keys:
            resource = RESOURCES.get_resource(resource_key)
            if resource:
                all_resources.append({
                    "id": resource_key,
                    "name": resource.label,
                    "emoji": resource.emoji,
                    "level": resource.lvl if hasattr(resource, 'lvl') else 0
                })
        
        # Сортируем по уровню и имени
        all_resources.sort(key=lambda x: (x["level"], x["name"]))
        
        # Пагинация: 4 элемента на странице
        items_per_page = 4
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Нормализуем номер страницы (цикличность)
        cur_page = cur_page % total_pages
        scene_data['rekit_resource_page'] = cur_page
        await self.scene.set_data('scene', scene_data)
        
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
                    "rekit",
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
            'text': '↪️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back'
            ),
            'ignore_row': True
        })
        
        return buttons
    
    @Page.on_callback('rekit')
    async def select_resource(self, callback: CallbackQuery, args: list):
        """Выбрать ресурс и перейти к выбору режима производства"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: ресурс не указан", show_alert=True)
            return
        
        new_resource = args[1]
        
        # Сохраняем выбранный ресурс
        scene_data = self.scene.get_data('scene')
        scene_data['rekit_resource'] = new_resource
        await self.scene.set_data('scene', scene_data)
        
        # Переходим на страницу выбора режима производства
        await self.scene.update_page('factory-rekit-produce')
        await callback.answer()
    
    @Page.on_callback('next_page')
    async def next_page(self, callback: CallbackQuery, args: list):
        """Следующая страница"""
        scene_data = self.scene.get_data('scene')
        cur_page = scene_data.get('rekit_resource_page', 0)
        
        # Вычисляем общее количество страниц
        produced_resources_keys = RESOURCES.get_produced_resources()
        items_per_page = 4
        total_pages = max(1, (len(produced_resources_keys) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: после последней страницы идет первая
        new_page = (cur_page + 1) % total_pages
        scene_data['rekit_resource_page'] = new_page
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('back_page')
    async def back_page(self, callback: CallbackQuery, args: list):
        """Предыдущая страница"""
        scene_data = self.scene.get_data('scene')
        cur_page = scene_data.get('rekit_resource_page', 0)
        
        # Вычисляем общее количество страниц
        produced_resources_keys = RESOURCES.get_produced_resources()
        items_per_page = 4
        total_pages = max(1, (len(produced_resources_keys) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: перед первой страницей идет последняя
        new_page = (cur_page - 1) % total_pages
        scene_data['rekit_resource_page'] = new_page
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('page_info')
    async def page_info(self, callback: CallbackQuery, args: list):
        """Информация о странице (заглушка)"""
        await callback.answer("📄 Навигация по ресурсам")
    
    @Page.on_callback('back')
    async def back_to_count(self, callback: CallbackQuery, args: list):
        """Возврат к вводу количества"""
        await self.scene.update_page('factory-rekit-count')
        await callback.answer()
