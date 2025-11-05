from oms import Page
from aiogram.types import Message, CallbackQuery
from oms.utils import callback_generator
from global_modules.logs import Logger
from modules.ws_client import get_factories
from modules.resources import RESOURCES, get_resource_name
bot_logger = Logger.get_logger("bot")


class FactoryRekitCount(Page):
    __page_name__ = "factory-rekit-count"
    
    async def content_worker(self):
        """Показать запрос количества заводов"""
        scene_data = self.scene.get_data('scene')
        group_type = scene_data.get('rekit_group')
        error_message = scene_data.get('rekit_count_error')
        
        # Очищаем ошибку после отображения
        if error_message:
            scene_data.pop('rekit_count_error', None)
            await self.scene.set_data('scene', scene_data)
        
        if not group_type:
            return "❌ Ошибка: группа заводов не выбрана"
        
        # Получаем список заводов для подсчёта
        company_id = scene_data.get('company_id')
        available_count = 0
        
        if company_id:
            factories = await get_factories(company_id)
            # Проверяем, что получили корректный ответ (список)
            if factories and isinstance(factories, list):
                # Считаем заводы в выбранной группе
                if group_type == 'idle':
                    available_count = sum(1 for f in factories if f.get('complectation') is None)
                else:
                    available_count = sum(1 for f in factories if f.get('complectation') == group_type)
        
        # Формируем текст в зависимости от выбранной группы
        if group_type == 'idle':
            group_name = "⚪️ Простаивающие заводы"
        else:
            group_name = get_resource_name(group_type)
        
        content = "🔄 **Перекомплектация заводов**\n\n"
        
        # Показываем ошибку, если она есть
        if error_message:
            content += f"❌ **{error_message}**\n\n"
        
        content += f"Группа: {group_name}\n"
        content += f"Доступно заводов: **{available_count}**\n\n"
        content += "Введите количество заводов для перекомплектации:"
        
        return content
    
    async def buttons_worker(self):
        """Кнопки с быстрым выбором количества"""
        buttons = [
            {
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'back'
                )
            }
        ]
        
        self.row_width = 1
        return buttons
    
    @Page.on_text('int')
    async def handle_text_input(self, message: Message, value: int):
        """Обработка текстового ввода количества"""
        scene_data = self.scene.get_data('scene')
        
        if value <= 0:
            # Сохраняем ошибку и обновляем страницу
            scene_data['rekit_count_error'] = "Количество должно быть больше 0"
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Получаем данные о заводах для проверки
        group_type = scene_data.get('rekit_group')
        company_id = scene_data.get('company_id')
        
        if not company_id or not group_type:
            # Сохраняем ошибку и обновляем страницу
            scene_data['rekit_count_error'] = "Недостаточно данных"
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Проверяем доступное количество заводов
        factories = await get_factories(company_id)
        # get_factories возвращает список напрямую
        if factories and isinstance(factories, list):
            if group_type == 'idle':
                available_count = sum(1 for f in factories if f.get('complectation') is None)
            else:
                available_count = sum(1 for f in factories if f.get('complectation') == group_type)
            
            if value > available_count:
                # Сохраняем ошибку и обновляем страницу
                scene_data['rekit_count_error'] = f"Недостаточно заводов! Доступно: {available_count}, запрошено: {value}"
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
        
        # Сохраняем количество
        scene_data['rekit_count'] = str(value)
        await self.scene.set_data('scene', scene_data)
        
        # Переходим на страницу выбора ресурса
        await self.scene.update_page('factory-rekit-resource')
    
    @Page.on_callback('back')
    async def back_to_groups(self, callback: CallbackQuery, args: list):
        """Возврат к выбору группы"""
        await self.scene.update_page('factory-rekit-groups')
        await callback.answer()
