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
        
        # Формируем информацию о группе с ошибкой если есть
        group_info = ""
        if error_message:
            group_info = f"❌ *{error_message}*\n\n"
        group_info += f"Группа: {group_name}\n"
        
        return self.content.format(
            group_info=group_info,
            available=available_count
        )
    
    async def buttons_worker(self):
        """Кнопки с быстрым выбором количества"""
        scene_data = self.scene.get_data('scene')
        group_type = scene_data.get('rekit_group')
        company_id = scene_data.get('company_id')
        
        buttons = []
        
        # Получаем количество доступных заводов
        available_count = 0
        if company_id and group_type:
            factories = await get_factories(company_id)
            if factories and isinstance(factories, list):
                if group_type == 'idle':
                    available_count = sum(1 for f in factories if f.get('complectation') is None)
                else:
                    available_count = sum(1 for f in factories if f.get('complectation') == group_type)
        
        # Если есть заводы, добавляем кнопки быстрого выбора
        if available_count > 0:
            # Определяем количество кнопок (минимум available_count и 4)
            num_buttons = min(available_count, 4)
            
            for i in range(1, num_buttons + 1):
                # Рассчитываем количество: i/num_buttons от available_count
                count = int((available_count * i) / num_buttons)
                if count > 0:  # Добавляем только если count больше 0
                    buttons.append({
                        'text': str(count),
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'quick_select',
                            str(count)
                        )
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
        
        self.row_width = 4
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
    
    @Page.on_callback('quick_select')
    async def handle_quick_select(self, callback: CallbackQuery, args: list):
        """Обработка быстрого выбора количества через кнопки"""
        if not args or len(args) < 2:
            await callback.answer("❌ Ошибка: некорректные данные", show_alert=True)
            return
        
        try:
            count = int(args[1])
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка: некорректное количество", show_alert=True)
            return
        
        scene_data = self.scene.get_data('scene')
        
        # Сохраняем количество
        scene_data['rekit_count'] = str(count)
        await self.scene.set_data('scene', scene_data)
        
        # Переходим на страницу выбора ресурса
        await self.scene.update_page('factory-rekit-resource')
        await callback.answer()
    
    @Page.on_callback('back')
    async def back_to_groups(self, callback: CallbackQuery, args: list):
        """Возврат к выбору группы"""
        await self.scene.update_page('factory-rekit-groups')
        await callback.answer()
