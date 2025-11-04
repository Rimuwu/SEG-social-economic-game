from oms import Page
from aiogram.types import Message, CallbackQuery
from oms.utils import callback_generator
from scenes.game_scenario import GameManager
from oms import scene_manager
from bot_instance import bot


class GameInfo(Page):
    __page_name__ = 'game-info-page'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_page = 1
        self.total_pages = 4
    
    async def content_worker(self) -> str:
        """Генерация контента в зависимости от текущей страницы"""
        func = [self._get_welcome_content(), self._get_gameplay_content(), self._get_resources_content(), self._get_authors_content()]
        return func[self.current_page - 1]
    
    def _get_welcome_content(self) -> str:
        return (
            "🎮 **SEG - Social Economic Game**\n\n"
            "Добро пожаловать в экономическую стратегию!\n\n"
            "📋 **Основы игры:**\n"
            "• Создайте или присоединитесь к компании\n"
            "• Выберите клетку на карте 7x7 для размещения\n"
            "• Добывайте ресурсы и производите товары\n"
            "• Торгуйте с другими игроками\n"
            "• Стройте улучшения и развивайтесь\n\n"
            "🎯 **Цель:** Стать самой успешной компанией по итогам игры!\n\n"
            f"📄 Страница {self.current_page}/{self.total_pages}"
        )
    
    def _get_gameplay_content(self) -> str:
        return (
            "🏗️ **Игровой процесс:**\n\n"
            "⏰ **Ходы игры:**\n"
            "• Игра состоит из 5-15 циклов\n"
            "• Каждый цикл = 4 хода (производство → торговля)\n"
            "• События происходят каждые 2-3 хода\n\n"
            "🗺️ **Карта и локации:**\n"
            "• 🏔️ Горы - добыча металла\n"
            "• 💧 Воды - добыча нефти\n"
            "• 🌲 Леса - добыча дерева\n"
            "• 🌾 Поля - добыча хлопка\n"
            "• 🏢 Города - торговля продуктами\n"
            "• 🏦 Банк - кредиты и депозиты\n\n"
            f"📄 Страница {self.current_page}/{self.total_pages}"
        )
    
    def _get_resources_content(self) -> str:
        return (
            "💰 **Ресурсы и производство:**\n\n"
            "🔧 **Базовые ресурсы:**\n"
            "• ⚡ Нефть - энергия для производства\n"
            "• ⚙️ Металл - для оборудования\n"
            "• 🌲 Дерево - строительный материал\n"
            "• 🧵 Хлопок - текстильное сырье\n\n"
            "🏭 **Производство:**\n"
            "• Перерабатывайте ресурсы в продукты\n"
            "• Стройте улучшения для эффективности\n"
            "• Заключайте контракты на поставки\n\n"
            "💳 **Банковская система:**\n"
            "• Берите кредиты под проценты\n"
            "• Делайте депозиты для дохода\n"
            "• Следите за репутацией\n\n"
            f"📄 Страница {self.current_page}/{self.total_pages}"
        )
    
    def _get_authors_content(self) -> str:
        return (
            "👥 **Авторы проекта:**\n\n"
            "🎨 **Разработка игры:**\n"
            "• Rimuwu - ведущий разработчик\n"
            "• Команда SEG - геймдизайн и балансировка\n\n"
            "💡 **Особые благодарности:**\n"
            "• Всем тестировщикам игры\n"
            "• Сообществу за фидбек\n\n"
            "📅 **Версия:** n.seg - not... SnEG\n"
            "🔗 **GitHub:** SEG-simple-economic-game\n\n"
            "Готовы начать игру?\n"
            "Нажмите \"🚀 Подключиться к игре\" чтобы ввести код сессии!\n\n"
            f"📄 Страница {self.current_page}/{self.total_pages}"
        )
    
    async def buttons_worker(self):
        """Генерация кнопок в зависимости от текущей страницы"""
        buttons = []
        
        # Кнопки навигации
        nav_row = []
        
        if self.current_page > 1:
            nav_row.append({
                'text': '⬅️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'prev_page'
                )
            })
        
        if self.current_page < self.total_pages:
            nav_row.append({
                'text': 'Далее ➡️',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'next_page'
                )
            })
        
        if nav_row:
            buttons.extend(nav_row)
        
        # Кнопка подключения к игре (только на последней странице)
        if self.current_page == self.total_pages:
            buttons.append({
                'text': '🚀 Подключиться к игре',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'connect_game'
                )
            })
        
        self.row_width = 2  # По 2 кнопки в ряд
        return buttons
    
    @Page.on_callback('prev_page')
    async def prev_page_handler(self, callback: CallbackQuery, args: list):
        """Обработчик перехода на предыдущую страницу"""
        if self.current_page > 1:
            self.current_page -= 1
            await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('next_page')
    async def next_page_handler(self, callback: CallbackQuery, args: list):
        """Обработчик перехода на следующую страницу"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('connect_game')
    async def connect_game_handler(self, callback: CallbackQuery, args: list):
        """Обработчик подключения к игре"""
        # Переходим на страницу ввода кода сессии
        await self.scene.end()
        n_scene = scene_manager.create_scene(
        callback.from_user.id,
        GameManager,
        bot
        )
        await n_scene.start()
        await callback.answer()