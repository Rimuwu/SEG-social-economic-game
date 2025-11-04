from oms import Page
from aiogram.types import Message, CallbackQuery
from oms.utils import callback_generator
from global_modules.logs import Logger
from global_modules.load_config import ALL_CONFIGS, Resources

bot_logger = Logger.get_logger("bot")
RESOURCES: Resources = ALL_CONFIGS["resources"]


class FactoryRekitResource(Page):
    __page_name__ = "factory-rekit-resource"
    
    async def content_worker(self):
        """Показать список ресурсов для перекомплектации"""
        scene_data = self.scene.get_data('scene')
        group_type = scene_data.get('rekit_group')
        count_str = scene_data.get('rekit_count')
        
        if not group_type or not count_str:
            return "❌ Ошибка: данные о перекомплектации не найдены"
        
        # Формируем текст
        if group_type == 'idle':
            group_name = "⚪️ Простаивающие заводы"
        else:
            resource = RESOURCES.get_resource(group_type)
            group_name = f"{resource.emoji} {resource.label}" if resource else group_type
        
        count_display = "все" if count_str == "all" else count_str
        
        content = "🔄 **Перекомплектация заводов**\n\n"
        content += f"Группа: {group_name}\n"
        content += f"Количество: **{count_display}**\n\n"
        content += "Выберите продукт для производства:\n"
        content += "⏳ _Перекомплектация займёт время согласно сложности производства_"
        
        return content
    
    async def buttons_worker(self):
        """Кнопки с доступными ресурсами (только производимые, без сырья)"""
        buttons = []
        
        # Получаем только производимые ресурсы (без raw=true)
        produced_resources = RESOURCES.get_produced_resources()
        
        # Добавляем кнопки компактно
        for resource_key in produced_resources:
            resource = RESOURCES.get_resource(resource_key)
            if resource:
                buttons.append({
                    'text': f'{resource.emoji} {resource.label}',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'rekit',
                        resource_key
                    ),
                    'next_line': True
                })
        
        # Кнопка назад
        buttons.append({
            'text': '↪️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back'
            ),
            'next_line': True
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
    
    @Page.on_callback('back')
    async def back_to_count(self, callback: CallbackQuery, args: list):
        """Возврат к вводу количества"""
        await self.scene.update_page('factory-rekit-count')
        await callback.answer()
