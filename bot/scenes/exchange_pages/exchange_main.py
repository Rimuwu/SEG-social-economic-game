from scenes.utils.oneuser_page import OneUserPage
from modules.ws_client import get_exchanges
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator
from aiogram.types import CallbackQuery


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeMain(OneUserPage):
    __for_blocked_pages__ = ["exchange-sellect-confirm", "exchange-create-page"]
    __page_name__ = "exchange-main-page"
    
    
    async def data_preparate(self):
        await self.scene.update_key("exchange-main-page", "page_number", 0)
        await self.scene.update_key("exchange-main-page", "state", "all")  # all, our
        await self.scene.update_key("exchange-main-page", "filter_resource", None)
    
    
    async def content_worker(self):
        """Генерация контента страницы"""
        data = self.scene.get_data("scene")
        session = data.get("session")
        state = self.scene.get_key("exchange-main-page", "state")
        filter_resource = self.scene.get_key("exchange-main-page", "filter_resource")
        
        text = "📈 *Биржа*\n\n"
        
        # Показываем активный фильтр
        if filter_resource:
            resource = RESOURCES.get_resource(filter_resource)
            if resource:
                text += f"🔍 Фильтр: {resource.emoji} {resource.label}\n\n"
        
        # Показываем режим (все/свои предложения)
        text += f"📋 {'Все предложения' if state == 'all' else 'Ваши предложения'}\n"
        
        return text
    
    
    async def buttons_worker(self):
        data = self.scene.get_data("scene")
        session = data.get("session")
        company = data.get("company_id")
        state = self.scene.get_key("exchange-main-page", "state")
        filter_resource = self.scene.get_key("exchange-main-page", "filter_resource")
        self.row_width = 3
        buttons = []
        all_ex_page_container = []
        our_ex_page_container = []
        cur_page = self.scene.get_key("exchange-main-page", "page_number")
        
        # Получаем предложения с учетом фильтра
        if filter_resource:
            exchanges = await get_exchanges(session_id=session, sell_resource=filter_resource)
        else:
            exchanges = await get_exchanges(session_id=session)
        
        if len(exchanges) != 0:
            for ex in exchanges:
                text = None
                callback = None
                sell_res = RESOURCES.get_resource(ex["sell_resource"])
                
                if ex["offer_type"] == "barter":
                    bart_res = RESOURCES.get_resource(ex["barter_resource"])
                    text = f"{ex['sell_amount_per_trade']}x {sell_res.emoji} {sell_res.label} ⇄ {ex['barter_amount_per_trade']}x {bart_res.emoji} {bart_res.label}"
                    callback = callback_generator(
                        self.scene.__scene_name__,
                        "select_exchange",
                        ex["id"]
                    )
                elif ex["offer_type"] == "money":
                    text = f"{ex['sell_amount_per_trade']}x {sell_res.emoji} {sell_res.label} ⇄ {ex['price']}💰"
                    callback = callback_generator(
                        self.scene.__scene_name__,
                        "select_exchange",
                        ex["id"]
                    )
                
                if ex["company_id"] != company:
                    all_ex_page_container.append({
                        "text": text,
                        "callback_data": callback,
                        "ignore_row": True
                    })
                elif ex["company_id"] == company:
                    our_ex_page_container.append({
                        "text": text,
                        "callback_data": callback,
                        "ignore_row": True
                    })
        
        # Выбираем нужный контейнер
        container = all_ex_page_container if state == "all" else our_ex_page_container
        
        # Пагинация: 5 элементов на странице
        items_per_page = 5
        total_pages = max(1, (len(container) + items_per_page - 1) // items_per_page)
        
        # Нормализуем номер страницы
        cur_page = cur_page % total_pages
        await self.scene.update_key("exchange-main-page", "page_number", cur_page)
        
        # Получаем элементы для текущей страницы
        start_idx = cur_page * items_per_page
        end_idx = start_idx + items_per_page
        buttons.extend(container[start_idx:end_idx])
        
        # Добавляем навигацию, если есть предложения
        if len(buttons) > 0:
            # Кнопки навигации по страницам
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
            
            # Кнопка переключения режима
            buttons.append({
                "text": f"{'📊 Наши предложения' if state == 'all' else '🌐 Все предложения'}",
                "callback_data": callback_generator(self.scene.__scene_name__, "change_state"),
                "next_line": True
            })
            
            # Кнопка фильтра
            if filter_resource:
                buttons.append({
                    "text": "🔄 Сбросить фильтр",
                    "callback_data": callback_generator(self.scene.__scene_name__, "reset_filter"),
                })
            else:
                buttons.append({
                    "text": "🔍 Фильтр по ресурсу",
                    "callback_data": callback_generator(self.scene.__scene_name__, "open_filter"),
                })
            
            # Кнопка создания предложения
            buttons.append({
                "text": "➕ Создать предложение",
                "callback_data": callback_generator(self.scene.__scene_name__, "create_offer"),
                "ignore_row": True
            })
        else:
            # Если предложений нет
            buttons.append({
                "text": f"{'📊 Наши предложения' if state == 'all' else '🌐 Все предложения'}",
                "callback_data": callback_generator(self.scene.__scene_name__, "change_state"),
                "ignore_row": True
            })
            if filter_resource:
                buttons.append({
                    "text": "🔄 Сбросить фильтр",
                    "callback_data": callback_generator(self.scene.__scene_name__, "reset_filter"),
                    "ignore_row": True
                })
            else:
                buttons.append({
                    "text": "🔍 Фильтр по ресурсу",
                    "callback_data": callback_generator(self.scene.__scene_name__, "open_filter"),
                    "ignore_row": True
                })
            buttons.append({
                "text": "➕ Создать предложение",
                "callback_data": callback_generator(self.scene.__scene_name__, "create_offer"),
                "ignore_row": True
            })
        
        return buttons
    
    @OneUserPage.on_callback("select_exchange")
    async def select_exchange(self, callback: CallbackQuery, args: list):
        """Выбор предложения для просмотра деталей"""
        await self.scene.update_key("exchange-sellect-confirm-page", "selected_exchange", args[1])
        await self.scene.update_page("exchange-sellect-confirm-page")
    
    @OneUserPage.on_callback("change_state")
    async def change_state(self, callback: CallbackQuery, args: list):
        """Переключение между всеми и своими предложениями"""
        state = self.scene.get_key("exchange-main-page", "state")
        if state == "all":
            await self.scene.update_key("exchange-main-page", "state", "our")
        else:
            await self.scene.update_key("exchange-main-page", "state", "all")
        await self.scene.update_key("exchange-main-page", "page_number", 0)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("next_page")
    async def next_page(self, callback: CallbackQuery, args: list):
        """Следующая страница"""
        cur_page = self.scene.get_key("exchange-main-page", "page_number")
        await self.scene.update_key("exchange-main-page", "page_number", cur_page + 1)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("back_page")
    async def back_page(self, callback: CallbackQuery, args: list):
        """Предыдущая страница"""
        cur_page = self.scene.get_key("exchange-main-page", "page_number")
        if cur_page > 0:
            await self.scene.update_key("exchange-main-page", "page_number", cur_page - 1)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("page_info")
    async def page_info(self, callback: CallbackQuery, args: list):
        """Информация о странице (заглушка)"""
        await callback.answer("Информация о странице")
    
    @OneUserPage.on_callback("open_filter")
    async def open_filter(self, callback: CallbackQuery, args: list):
        """Открыть страницу фильтра"""
        await self.scene.update_page("exchange-filter-page")
    
    @OneUserPage.on_callback("reset_filter")
    async def reset_filter(self, callback: CallbackQuery, args: list):
        """Сбросить фильтр"""
        await self.scene.update_key("exchange-main-page", "filter_resource", None)
        await self.scene.update_key("exchange-main-page", "page_number", 0)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("create_offer")
    async def create_offer(self, callback: CallbackQuery, args: list):
        """Создать новое предложение"""
        await self.scene.update_page("exchange-create-page")