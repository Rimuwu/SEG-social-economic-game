from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery
from modules.ws_client import get_exchanges
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeMain(OneUserPage):
    """Главная страница биржи со списком предложений"""
    
    __page_name__ = "exchange-main-page"
    
    async def content_worker(self):
        """Генерация контента - список предложений"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        if not company_id or not session_id:
            return "❌ Ошибка: данные компании или сессии не найдены"
        
        success_message_text = scene_data.get('success_message', '')
        current_page = scene_data.get('list_page', 0)
        filter_resource = scene_data.get('filter_resource', None)
        
        # Формируем сообщение об успехе
        success_message = ""
        if success_message_text:
            success_message = f"✅ {success_message_text}\n\n"
            scene_data['success_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        # Формируем текст фильтра
        filter_text = ""
        if filter_resource:
            resource = RESOURCES.get_resource(filter_resource)
            if resource:
                filter_text = f"🔍 Поиск: {resource.emoji} {resource.label}\n\n"
            exchanges = await get_exchanges(
                session_id=session_id,
                sell_resource=filter_resource
            )
        else:
            filter_text = "📋 Все предложения:\n\n"
            exchanges = await get_exchanges(session_id=session_id)
        
        if isinstance(exchanges, str):
            return f"❌ Ошибка при получении предложений: {exchanges}"
        
        # Формируем текст предложений
        if not exchanges or len(exchanges) == 0:
            offers_text = "_Нет доступных предложений_\n\n"
            if filter_resource:
                offers_text += "Попробуйте сбросить фильтр или выбрать другой ресурс"
            
            return self.content.format(
                success_message=success_message,
                filter_text=filter_text,
                offers_text=offers_text
            )
        
        # Пагинация (5 предложений на страницу)
        items_per_page = 5
        total_pages = max(1, (len(exchanges) + items_per_page - 1) // items_per_page)
        
        # Нормализуем номер страницы
        current_page = current_page % total_pages
        scene_data['list_page'] = current_page
        scene_data['total_pages'] = total_pages
        await self.scene.set_data('scene', scene_data)
        
        # Получаем предложения для текущей страницы
        start_idx = current_page * items_per_page
        end_idx = start_idx + items_per_page
        page_exchanges = exchanges[start_idx:end_idx]
        
        offers_text = f"Найдено предложений: {len(exchanges)}\n"
        offers_text += f"Страница: {current_page + 1}/{total_pages}\n\n"
        
        # Отображаем предложения (краткая информация)
        for i, exchange in enumerate(page_exchanges, 1):
            sell_res = RESOURCES.get_resource(exchange.get('sell_resource', ''))
            if not sell_res:
                continue
            
            sell_amount = exchange.get('sell_amount_per_trade', 0)
            total_stock = exchange.get('total_stock', 0)
            offer_type = exchange.get('offer_type', 'money')
            
            offers_text += f"*{i}.* {sell_res.emoji} {sell_res.label} x{sell_amount}\n"
            offers_text += f"   Всего в наличии: {total_stock}\n"
            
            if offer_type == 'money':
                price = exchange.get('price', 0)
                offers_text += f"   💰 Цена: {price:,}".replace(",", " ") + "\n"
            elif offer_type == 'barter':
                barter_res = RESOURCES.get_resource(exchange.get('barter_resource', ''))
                barter_amount = exchange.get('barter_amount', 0)
                if barter_res:
                    offers_text += f"   ⇄ За: {barter_res.emoji} {barter_res.label} x{barter_amount}\n"
            
            offers_text += "\n"
        
        return self.content.format(
            success_message=success_message,
            filter_text=filter_text,
            offers_text=offers_text
        )
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('session')
        filter_resource = scene_data.get('filter_resource', None)
        
        buttons = []
        
        # Получаем предложения для генерации кнопок
        if filter_resource:
            exchanges = await get_exchanges(
                session_id=session_id,
                sell_resource=filter_resource
            )
        else:
            exchanges = await get_exchanges(session_id=session_id)
        
        if isinstance(exchanges, list) and len(exchanges) > 0:
            # Пагинация
            items_per_page = 5
            current_page = scene_data.get('list_page', 0)
            total_pages = scene_data.get('total_pages', 1)
            
            start_idx = current_page * items_per_page
            end_idx = start_idx + items_per_page
            page_exchanges = exchanges[start_idx:end_idx]
            
            # Кнопки предложений
            for exchange in page_exchanges:
                sell_res = RESOURCES.get_resource(exchange.get('sell_resource', ''))
                if not sell_res:
                    continue
                
                sell_amount = exchange.get('sell_amount_per_trade', 0)
                offer_type = exchange.get('offer_type', 'money')
                
                # Формируем текст кнопки
                if offer_type == 'money':
                    price = exchange.get('price', 0)
                    btn_text = f"{sell_res.emoji} {sell_res.label} x{sell_amount} → {price:,}💰".replace(",", " ")
                else:  # barter
                    barter_res = RESOURCES.get_resource(exchange.get('barter_resource', ''))
                    barter_amount = exchange.get('barter_amount', 0)
                    if barter_res:
                        btn_text = f"{sell_res.emoji} {sell_res.label} x{sell_amount} ⇄ {barter_res.emoji} x{barter_amount}"
                    else:
                        btn_text = f"{sell_res.emoji} {sell_res.label} x{sell_amount}"
                
                buttons.append({
                    'text': btn_text,
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'view_exchange',
                        str(exchange.get('id'))
                    )
                })
            
            # Навигация между страницами (если страниц больше одной)
            if total_pages > 1:
                prev_page = (current_page - 1) % total_pages
                buttons.append({
                    'text': '◀️ Назад',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'list_page',
                        str(prev_page)
                    )
                })
                
                # Кнопка фильтра посередине
                buttons.append({
                    'text': '🔍 Поиск',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'open_filter'
                    )
                })
                
                next_page = (current_page + 1) % total_pages
                buttons.append({
                    'text': 'Вперёд ▶️',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'list_page',
                        str(next_page)
                    )
                })
            else:
                # Если страница одна, просто показываем кнопку поиска
                buttons.append({
                    'text': '🔍 Поиск',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'open_filter'
                    ),
                    'next_line': True
                })
        else:
            # Нет предложений - показываем только поиск
            buttons.append({
                'text': '🔍 Поиск',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'open_filter'
                )
            })
        
        # Кнопка "Создать предложение"
        buttons.append({
            'text': '➕ Создать',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'create_offer'
            ),
            'next_line': True
        })
        
        # Кнопка "Назад в главное меню"
        buttons.append({
            'text': '↪️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_to_menu'
            ),
            'next_line': True
        })
        
        return buttons
    
    @OneUserPage.on_callback('view_exchange')
    async def view_exchange_handler(self, callback: CallbackQuery, args: list):
        """Просмотр детальной информации о предложении"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID предложения", show_alert=True)
            return
        
        exchange_id = int(args[1])
        scene_data = self.scene.get_data('scene')
        
        scene_data['selected_exchange_id'] = exchange_id
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('exchange-details-page')
        await callback.answer()
    
    @OneUserPage.on_callback('list_page')
    async def list_page_handler(self, callback: CallbackQuery, args: list):
        """Переключение страницы списка"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        page = int(args[1])
        scene_data = self.scene.get_data('scene')
        
        scene_data['list_page'] = page
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @OneUserPage.on_callback('open_filter')
    async def open_filter_handler(self, callback: CallbackQuery, args: list):
        """Открыть экран фильтра"""
        scene_data = self.scene.get_data('scene')
        scene_data['filter_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('exchange-filter-page')
        await callback.answer("🔍 Выберите ресурс для поиска")
    
    @OneUserPage.on_callback('create_offer')
    async def create_offer_handler(self, callback: CallbackQuery, args: list):
        """Начать создание нового предложения"""
        scene_data = self.scene.get_data('scene')
        
        # Очищаем предыдущие данные создания
        scene_data['create_offer_type'] = None
        scene_data['create_sell_resource'] = None
        scene_data['create_sell_amount'] = None
        scene_data['create_count_offers'] = None
        scene_data['create_price'] = None
        scene_data['create_barter_resource'] = None
        scene_data['create_barter_amount'] = None
        
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_page('exchange-create-page')
        await callback.answer("➕ Создание предложения")
    
    @OneUserPage.on_callback('back_to_menu')
    async def back_to_menu_handler(self, callback: CallbackQuery, args: list):
        """Возврат в главное меню"""
        # Очищаем состояние страницы
        scene_data = self.scene.get_data('scene')
        scene_data['list_page'] = 0
        scene_data['filter_page'] = 0
        scene_data['filter_resource'] = None
        scene_data['selected_exchange_id'] = None
        scene_data['success_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        # Переходим на страницу главного меню
        await self.scene.update_page('main-page')
        await callback.answer("↪️ Возврат в меню")
