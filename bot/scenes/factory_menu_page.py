
from aiogram.types import Message, CallbackQuery
from modules.ws_client import get_factories
from oms.utils import callback_generator
from global_modules.logs import Logger
from modules.resources import get_resource_name
from .oneuser_page import OneUserPage

bot_logger = Logger.get_logger("bot")


Page = OneUserPage

class FactoryMenu(Page):
    
    __for_blocked_pages__ = ['factory-start-groups', 'factory-rekit-groups', 'factory-rekit-count', 'factory-rekit-resource', 'factory-rekit-produce', 'factory-select-mode', 'factory-change-mode']
    __page_name__ = "factory-menu"
    
    def get_resource_name(self, resource_key: str) -> str:
        """Получить русское название ресурса"""
        return get_resource_name(resource_key)
    
    async def content_worker(self):
        """Показать статистику всех заводов"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        try:
            # Получаем все заводы
            factories = await get_factories(company_id=company_id)
            bot_logger.info(f"get_factories response: {factories}")
            
            # get_factories возвращает список напрямую
            if not factories or not isinstance(factories, list):
                return "❌ Не удалось загрузить список заводов"
            
            total = len(factories)
            
            # Классификация заводов
            idle_factories = []  # Простаивающие (complectation is None)
            auto_factories = {}  # Автоматические (is_auto = True) по ресурсам
            manual_factories = {}  # Не автоматические (is_auto = False, complectation not None) по ресурсам
            recomplecting_factories = {}  # Заводы в процессе перекомплектации (complectation_stages > 0)
            
            for factory in factories:
                complectation = factory.get('complectation')
                is_auto = factory.get('is_auto', False)
                complectation_stages = factory.get('complectation_stages', 0)
                
                # Сначала проверяем, не в процессе ли перекомплектации
                if complectation_stages > 0:
                    # Завод перекомплектуется
                    if complectation not in recomplecting_factories:
                        recomplecting_factories[complectation] = []
                    recomplecting_factories[complectation].append(factory)
                elif complectation is None:
                    idle_factories.append(factory)
                elif is_auto:
                    # Автоматический завод
                    if complectation not in auto_factories:
                        auto_factories[complectation] = []
                    auto_factories[complectation].append(factory)
                else:
                    # Не автоматический завод
                    if complectation not in manual_factories:
                        manual_factories[complectation] = []
                    manual_factories[complectation].append(factory)
            
            # Формируем текст
            content = "🏭 **Меню управления заводами**\n\n"
            content += f"📊 **Всего заводов:** {total}\n\n"
            
            # Заводы в процессе перекомплектации
            if recomplecting_factories:
                content += "⏳ **Перекомплектуются:**\n"
                for resource_key, factories_list in recomplecting_factories.items():
                    resource_display = self.get_resource_name(resource_key)
                    # Показываем максимальное количество оставшихся ходов
                    max_stages = max(f.get('complectation_stages', 0) for f in factories_list)
                    content += f"  {resource_display}: **{len(factories_list)}** шт. (осталось {max_stages} ход(-ов))\n"
                content += "\n"
            
            # Автоматические заводы
            if auto_factories:
                content += "🔄 **Автоматические заводы** (производят каждый ход):\n"
                for resource_key, factories_list in auto_factories.items():
                    resource_display = self.get_resource_name(resource_key)
                    content += f"  {resource_display}: **{len(factories_list)}** шт.\n"
                content += "\n"
            
            # Не автоматические заводы
            if manual_factories:
                content += "⚡ **Не автоматические заводы:**\n"
                for resource_key, factories_list in manual_factories.items():
                    resource_display = self.get_resource_name(resource_key)
                    # Считаем работающие и остановленные
                    working = sum(1 for f in factories_list if f.get('is_working', False))
                    stopped = len(factories_list) - working
                    
                    status_text = ""
                    if working > 0 and stopped > 0:
                        status_text = f" (▶️ {working} работает, ⏸️ {stopped} остановлено)"
                    elif working > 0:
                        status_text = f" (▶️ все работают)"
                    elif stopped > 0:
                        status_text = f" (⏸️ все остановлены)"
                    
                    content += f"  {resource_display}: **{len(factories_list)}** шт.{status_text}\n"
                content += "\n"
            
            # Простаивающие заводы
            if idle_factories:
                content += f"⚪️ **Простаивают:** {len(idle_factories)} шт.\n\n"
            else:
                content += "⚪️ **Простаивают:** 0 шт.\n\n"
            
            if not auto_factories and not manual_factories and not idle_factories:
                content += "У вас пока нет активных заводов."
            
            return content
            
        except Exception as e:
            bot_logger.error(f"Ошибка при получении заводов: {e}")
            return f"❌ Ошибка при загрузке данных: {str(e)}"
    
    async def buttons_worker(self):
        """Кнопки управления заводами"""
        buttons = [
            {
                'text': '▶️ Запустить заводы',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'start_factories'
                )
            },
            {
                'text': '🔄 Перекомплектовать',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'rekit'
                )
            },
            {
                'text': '🔀 Изменить режим',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'change_mode'
                )
            }
        ]
        
        self.row_width = 2
        return buttons
    
    @Page.on_callback('start_factories')
    async def show_start_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу запуска заводов"""
        await self.scene.update_page('factory-start-groups')
        await callback.answer()
    
    @Page.on_callback('buy_factories')
    async def show_buy_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу покупки заводов"""
        # TODO: Реализовать страницу покупки заводов
        await callback.answer("🚧 Страница покупки заводов в разработке", show_alert=True)
        # await self.scene.update_page('factory-buy')
    
    @Page.on_callback('change_mode')
    async def show_change_mode_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу изменения режима производства"""
        await self.scene.update_page('factory-change-mode')
        await callback.answer()
    
    @Page.on_callback('rekit')
    async def show_rekit_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу выбора группы заводов для перекомплектации"""
        await self.scene.update_page('factory-rekit-groups')
        await callback.answer()
