from oms import Page
from aiogram.types import CallbackQuery
from oms.utils import callback_generator
from modules.ws_client import get_factories

class FactorySelectMode(Page):
    """Страница выбора режима заводов для перекомплектации"""
    
    __page_name__ = "factory-select-mode"
    
    async def content_worker(self):
        """Показать доступные режимы заводов"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        # Получаем все заводы компании
        factories = await get_factories(company_id)
        
        if not factories or not isinstance(factories, list):
            return "❌ Не удалось загрузить список заводов"
        
        # Подсчитываем заводы по режимам
        idle_count = sum(1 for f in factories if f.get('complectation') is None)
        auto_count = sum(1 for f in factories if f.get('is_auto') is True and f.get('complectation') is not None)
        manual_count = sum(1 for f in factories if f.get('is_auto') is False and f.get('complectation') is not None)
        
        content = "🏭 **Перекомплектация заводов**\n\n"
        content += "Выберите режим заводов для перекомплектации:\n\n"
        content += f"⚪️ **Простаивающие:** {idle_count} шт.\n"
        content += f"🤖 **Автоматические:** {auto_count} шт.\n"
        content += f"👤 **Неавтоматические:** {manual_count} шт.\n"
        
        return content
    
    async def buttons_worker(self):
        """Генерация кнопок выбора режима"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        buttons = []
        
        # Получаем заводы для подсчёта
        factories = await get_factories(company_id)
        
        if factories and isinstance(factories, list):
            # Считаем заводы по режимам
            idle_count = sum(1 for f in factories if f.get('complectation') is None)
            auto_count = sum(1 for f in factories if f.get('is_auto') is True and f.get('complectation') is not None)
            manual_count = sum(1 for f in factories if f.get('is_auto') is False and f.get('complectation') is not None)
            
            # Кнопка "Простаивающие"
            if idle_count > 0:
                buttons.append({
                    'text': f'⚪️ Простаивающие ({idle_count})',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'select_mode',
                        'idle'
                    ),
                    'ignore_row': True
                })
            
            # Кнопка "Автоматические"
            if auto_count > 0:
                buttons.append({
                    'text': f'🤖 Автоматические ({auto_count})',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'select_mode',
                        'auto'
                    ),
                    'ignore_row': True
                })
            
            # Кнопка "Неавтоматические"
            if manual_count > 0:
                buttons.append({
                    'text': f'👤 Неавтоматические ({manual_count})',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'select_mode',
                        'manual'
                    ),
                    'ignore_row': True
                })
        
        # Кнопка "Назад"
        buttons.append({
            'text': '↪️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_to_menu'
            ),
            'next_line': True
        })
        
        self.row_width = 1
        return buttons
    
    @Page.on_callback('select_mode')
    async def select_mode_handler(self, callback: CallbackQuery, args: list):
        """Обработка выбора режима"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        factory_mode = args[1]
        scene_data = self.scene.get_data('scene')
        
        # Сохраняем выбранный режим
        scene_data['factory_mode'] = factory_mode
        scene_data['factory_action'] = 'rekit'
        await self.scene.set_data('scene', scene_data)
        
        # Переходим к выбору группы ресурсов
        await self.scene.update_page('factory-rekit-groups')
    
    @Page.on_callback('back_to_menu')
    async def back_to_menu_handler(self, callback: CallbackQuery, args: list):
        """Возврат в меню заводов"""
        await self.scene.update_page('factory-menu')
