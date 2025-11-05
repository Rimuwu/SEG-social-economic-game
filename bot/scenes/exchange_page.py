from oms import Page
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_exchanges, get_exchange, buy_exchange_offer, get_company, create_exchange_offer, get_item_price
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources
from .filters.item_filter import ItemFilter
from .oneuser_page import OneUserPage

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangePage(OneUserPage):
    
    __page_name__ = "exchange-page"
    
    def __after_init__(self):
        """Инициализация фильтра предметов"""
        super().__after_init__()
        # Создаём фильтр предметов для этой страницы
        self.item_filter = ItemFilter(
            scene_name='scene-manager',  # Будет установлено в __post_init__
            callback_prefix='filter_resource',
            items_per_page=5
        )
    
    def __post_init__(self):
        """Установка имени сцены для фильтра"""
        super().__post_init__()
        self.item_filter.scene_name = self.scene.__scene_name__
    
    async def content_worker(self):
        """Генерация контента страницы"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        if not company_id or not session_id:
            return "❌ Ошибка: данные компании или сессии не найдены"
        
        # Получаем состояние страницы
        exchange_state = scene_data.get('exchange_state', 'list')
        
        # Список предложений
        if exchange_state == 'list':
            return await self._list_screen(scene_data, session_id, company_id)
        
        # Фильтр по предмету
        elif exchange_state == 'filter':
            return await self._filter_screen(scene_data)
        
        # Детальная информация о предложении
        elif exchange_state == 'details':
            return await self._details_screen(scene_data)
        
        # Создание предложения - выбор типа
        elif exchange_state == 'create_select_type':
            return await self._create_select_type_screen(scene_data)
        
        # Создание предложения - выбор товара для продажи
        elif exchange_state == 'create_select_sell_resource':
            return await self._create_select_sell_resource_screen(scene_data, company_id)
        
        # Создание предложения - ввод количества за сделку
        elif exchange_state == 'create_input_amount':
            return await self._create_input_amount_screen(scene_data)
        
        # Создание предложения - ввод количества сделок
        elif exchange_state == 'create_input_count':
            return await self._create_input_count_screen(scene_data)
        
        # Создание предложения - ввод цены (для money)
        elif exchange_state == 'create_input_price':
            return await self._create_input_price_screen(scene_data)
        
        # Создание предложения - выбор ресурса для бартера
        elif exchange_state == 'create_select_barter_resource':
            return await self._create_select_barter_resource_screen(scene_data)
        
        # Создание предложения - ввод количества ресурса для бартера
        elif exchange_state == 'create_input_barter_amount':
            return await self._create_input_barter_amount_screen(scene_data)
        
        # Создание предложения - подтверждение
        elif exchange_state == 'create_confirm':
            return await self._create_confirm_screen(scene_data)
        
        return "❌ Неизвестное состояние"
    
    async def _list_screen(self, scene_data: dict, session_id: str, company_id: int):
        """Основной экран со списком предложений"""
        success_message = scene_data.get('success_message', '')
        current_page = scene_data.get('list_page', 0)
        filter_resource = scene_data.get('filter_resource', None)
        
        text = "📈 *Биржа*\n\n"
        
        # Показываем успешное сообщение
        if success_message:
            text += f"✅ {success_message}\n\n"
            scene_data['success_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        # Получаем предложения
        if filter_resource:
            resource = RESOURCES.get_resource(filter_resource)
            if resource:
                text += f"🔍 Поиск: {resource.emoji} {resource.label}\n\n"
            exchanges = await get_exchanges(
                session_id=session_id,
                sell_resource=filter_resource
            )
        else:
            text += "📋 Все предложения:\n\n"
            exchanges = await get_exchanges(session_id=session_id)
        
        if isinstance(exchanges, str):
            return f"❌ Ошибка при получении предложений: {exchanges}"
        
        if not exchanges or len(exchanges) == 0:
            text += "_Нет доступных предложений_\n\n"
            if filter_resource:
                text += "Попробуйте сбросить фильтр или выбрать другой ресурс"
            return text
        
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
        
        text += f"Найдено предложений: {len(exchanges)}\n"
        text += f"Страница: {current_page + 1}/{total_pages}\n\n"
        
        # Отображаем предложения (краткая информация)
        for i, exchange in enumerate(page_exchanges, 1):
            sell_res = RESOURCES.get_resource(exchange.get('sell_resource', ''))
            if not sell_res:
                continue
            
            sell_amount = exchange.get('sell_amount_per_trade', 0)
            total_stock = exchange.get('total_stock', 0)
            offer_type = exchange.get('offer_type', 'money')
            
            text += f"*{i}.* {sell_res.emoji} {sell_res.label} x{sell_amount}\n"
            text += f"   Всего в наличии: {total_stock}\n"
            
            if offer_type == 'money':
                price = exchange.get('price', 0)
                text += f"   💰 Цена: {price:,}".replace(",", " ") + "\n"
            elif offer_type == 'barter':
                barter_res = RESOURCES.get_resource(exchange.get('barter_resource', ''))
                barter_amount = exchange.get('barter_amount', 0)
                if barter_res:
                    text += f"   ⇄ За: {barter_res.emoji} {barter_res.label} x{barter_amount}\n"
            
            text += "\n"
        
        return text
    
    async def _filter_screen(self, scene_data: dict):
        """Экран фильтра по ресурсам"""
        text = "🔍 *Выберите ресурс для поиска*\n\n"
        text += "Выберите ресурс, чтобы увидеть только предложения с этим товаром:"
        return text
    
    async def _details_screen(self, scene_data: dict):
        """Детальная информация о предложении"""
        exchange_id = scene_data.get('selected_exchange_id')
        
        if not exchange_id:
            return "❌ Ошибка: предложение не выбрано"
        
        # Проверяем кеш для избежания повторных запросов
        cache_key = f'exchange_details_{exchange_id}'
        cached_data = scene_data.get(cache_key)
        
        if cached_data:
            # Используем закешированные данные
            exchange = cached_data.get('exchange')
            seller_name = cached_data.get('seller_name', 'Неизвестная компания')
        else:
            # Получаем детальную информацию о предложении
            exchange = await get_exchange(id=exchange_id)
            
            if isinstance(exchange, str):
                return f"❌ Ошибка при получении информации: {exchange}"
            
            if not exchange:
                return "❌ Предложение не найдено"
            
            # Получаем информацию о компании-продавце
            seller_company_id = exchange.get('company_id')
            seller_company = await get_company(id=seller_company_id)
            seller_name = "Неизвестная компания"
            if isinstance(seller_company, dict):
                seller_name = seller_company.get('name', 'Неизвестная компания')
            
            # Кешируем данные
            scene_data[cache_key] = {
                'exchange': exchange,
                'seller_name': seller_name
            }
            await self.scene.set_data('scene', scene_data)
        
        # Формируем детальное описание
        text = "📋 *Детали предложения*\n\n"
        
        # Информация о продавце
        text += f"🏢 *Продавец:* {seller_name}\n\n"
        
        # Информация о товаре
        sell_res = RESOURCES.get_resource(exchange.get('sell_resource', ''))
        if sell_res:
            sell_amount = exchange.get('sell_amount_per_trade', 0)
            total_stock = exchange.get('total_stock', 0)
            
            text += f"*Товар:* {sell_res.emoji} {sell_res.label}\n"
            text += f"*За одну сделку:* {sell_amount} шт.\n"
            text += f"*Всего в наличии:* {total_stock} шт.\n"
            
            # Количество доступных сделок
            available_trades = total_stock // sell_amount if sell_amount > 0 else 0
            text += f"*Доступно сделок:* {available_trades}\n\n"
        
        # Условия сделки
        offer_type = exchange.get('offer_type', 'money')
        
        if offer_type == 'money':
            price = exchange.get('price', 0)
            text += f"💰 *Тип:* За монеты\n"
            text += f"💰 *Цена за сделку:* {price:,}".replace(",", " ") + "\n"
        elif offer_type == 'barter':
            barter_res = RESOURCES.get_resource(exchange.get('barter_resource', ''))
            barter_amount = exchange.get('barter_amount', 0)
            if barter_res:
                text += f"⇄ *Тип:* Бартер\n"
                text += f"⇄ *Требуется:* {barter_res.emoji} {barter_res.label} x{barter_amount}\n"
        
        # Информация о времени создания
        created_at = exchange.get('created_at', 0)
        if created_at:
            text += f"\n⏰ *Создано на ходу:* {created_at}\n"
        
        return text
    
    async def _create_select_type_screen(self, scene_data: dict):
        """Экран выбора типа предложения"""
        text = "➕ *Создание предложения*\n\n"
        text += "Выберите тип предложения:\n\n"
        text += "💰 *За деньги* - покупатель заплатит монетами\n"
        text += "⇄ *Бартер* - обмен товара на товар\n"
        return text
    
    async def _create_select_sell_resource_screen(self, scene_data: dict, company_id: int):
        """Экран выбора товара для продажи"""
        text = "➕ *Создание предложения*\n\n"
        
        offer_type = scene_data.get('create_offer_type', 'money')
        type_text = "💰 За деньги" if offer_type == 'money' else "⇄ Бартер"
        text += f"Тип: {type_text}\n\n"
        
        text += "Выберите товар для продажи со склада:"
        return text
    
    async def _create_input_amount_screen(self, scene_data: dict):
        """Экран ввода количества за сделку"""
        text = "➕ *Создание предложения*\n\n"
        
        sell_resource = scene_data.get('create_sell_resource')
        if sell_resource:
            resource = RESOURCES.get_resource(sell_resource)
            if resource:
                text += f"Товар: {resource.emoji} {resource.label}\n\n"
        
        text += "💬 *Введите количество товара за одну сделку*\n\n"
        text += "Пример: `10` - за одну сделку будет продаваться 10 единиц товара"
        return text
    
    async def _create_input_count_screen(self, scene_data: dict):
        """Экран ввода количества сделок"""
        text = "➕ *Создание предложения*\n\n"
        
        sell_resource = scene_data.get('create_sell_resource')
        sell_amount = scene_data.get('create_sell_amount', 0)
        
        if sell_resource:
            resource = RESOURCES.get_resource(sell_resource)
            if resource:
                text += f"Товар: {resource.emoji} {resource.label} x{sell_amount} за сделку\n\n"
        
        text += "💬 *Введите количество сделок*\n\n"
        text += f"Пример: `5` - будет создано 5 сделок по {sell_amount} единиц\n"
        text += f"Всего будет выставлено на продажу: {sell_amount} × 5 = {sell_amount * 5} единиц"
        return text
    
    async def _create_input_price_screen(self, scene_data: dict):
        """Экран ввода цены"""
        text = "➕ *Создание предложения*\n\n"
        
        sell_resource = scene_data.get('create_sell_resource')
        sell_amount = scene_data.get('create_sell_amount', 0)
        count_offers = scene_data.get('create_count_offers', 1)
        
        if sell_resource:
            resource = RESOURCES.get_resource(sell_resource)
            if resource:
                text += f"Товар: {resource.emoji} {resource.label}\n"
                text += f"За сделку: {sell_amount} шт.\n"
                text += f"Количество сделок: {count_offers}\n\n"

        text += "💬 *Введите цену за одну сделку*\n\n"
        text += "Пример: `1000` - покупатель заплатит 1000 монет за одну сделку"

        if sell_resource:
            item_price = await get_item_price(
                scene_data.get('session', ''),
                sell_resource
            )
            if item_price:
                text += f"\nСредняя цена за 1 товар: {item_price['price']}"

        return text
    
    async def _create_select_barter_resource_screen(self, scene_data: dict):
        """Экран выбора ресурса для бартера"""
        text = "➕ *Создание предложения*\n\n"
        
        sell_resource = scene_data.get('create_sell_resource')
        sell_amount = scene_data.get('create_sell_amount', 0)
        count_offers = scene_data.get('create_count_offers', 1)
        
        if sell_resource:
            resource = RESOURCES.get_resource(sell_resource)
            if resource:
                text += f"Продаёте: {resource.emoji} {resource.label} x{sell_amount}\n"
                text += f"Количество сделок: {count_offers}\n\n"
        
        text += "Выберите ресурс, который хотите получить в обмен:"
        return text
    
    async def _create_input_barter_amount_screen(self, scene_data: dict):
        """Экран ввода количества ресурса для бартера"""
        text = "➕ *Создание предложения*\n\n"
        
        sell_resource = scene_data.get('create_sell_resource')
        sell_amount = scene_data.get('create_sell_amount', 0)
        barter_resource = scene_data.get('create_barter_resource')
        
        if sell_resource:
            sell_res = RESOURCES.get_resource(sell_resource)
            if sell_res:
                text += f"Продаёте: {sell_res.emoji} {sell_res.label} x{sell_amount}\n"
        
        if barter_resource:
            barter_res = RESOURCES.get_resource(barter_resource)
            if barter_res:
                text += f"В обмен на: {barter_res.emoji} {barter_res.label}\n\n"
        
        text += "💬 *Введите количество ресурса для обмена*\n\n"
        text += "Пример: `5` - покупатель отдаст 5 единиц ресурса за одну сделку"
        return text
    
    async def _create_confirm_screen(self, scene_data: dict):
        """Экран подтверждения создания предложения"""
        text = "➕ *Подтверждение создания предложения*\n\n"
        
        sell_resource = scene_data.get('create_sell_resource')
        sell_amount = scene_data.get('create_sell_amount', 0)
        count_offers = scene_data.get('create_count_offers', 1)
        offer_type = scene_data.get('create_offer_type', 'money')
        
        # Информация о продаваемом товаре
        if sell_resource:
            resource = RESOURCES.get_resource(sell_resource)
            if resource:
                text += f"*Продаёте:*\n"
                text += f"└ {resource.emoji} {resource.label} x{sell_amount} за сделку\n"
                text += f"└ Количество сделок: {count_offers}\n"
                text += f"└ Всего: {sell_amount * count_offers} единиц\n\n"
        
        # Информация об условиях
        if offer_type == 'money':
            price = scene_data.get('create_price', 0)
            text += f"*Условия:*\n"
            text += f"└ 💰 За деньги: {price:,}".replace(",", " ") + " монет за сделку\n"
            text += f"└ Всего получите: {price * count_offers:,}".replace(",", " ") + " монет\n"
        elif offer_type == 'barter':
            barter_resource = scene_data.get('create_barter_resource')
            barter_amount = scene_data.get('create_barter_amount', 0)
            if barter_resource:
                barter_res = RESOURCES.get_resource(barter_resource)
                if barter_res:
                    text += f"*Условия:*\n"
                    text += f"└ ⇄ Бартер: {barter_res.emoji} {barter_res.label} x{barter_amount} за сделку\n"
                    text += f"└ Всего получите: {barter_amount * count_offers} единиц\n"
        
        text += "\n⚠️ *Подтвердите создание предложения*"
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        exchange_state = scene_data.get('exchange_state', 'list')
        
        buttons = []
        
        # Кнопки для списка предложений
        if exchange_state == 'list':
            filter_resource = scene_data.get('filter_resource', None)
            
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
                    nav_row = []
                    
                    prev_page = (current_page - 1) % total_pages
                    nav_row.append({
                        'text': '◀️ Назад',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'list_page',
                            str(prev_page)
                        )
                    })
                    
                    # Кнопка фильтра посередине
                    nav_row.append({
                        'text': '🔍 Поиск',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'open_filter'
                        )
                    })
                    
                    next_page = (current_page + 1) % total_pages
                    nav_row.append({
                        'text': 'Вперёд ▶️',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'list_page',
                            str(next_page)
                        )
                    })
                    
                    # Добавляем навигацию
                    for i, btn in enumerate(nav_row):
                        buttons.append(btn)
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
            
            # Кнопка "Создать предложение" (будет реализована позже)
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
        
        # Кнопки для экрана фильтра
        elif exchange_state == 'filter':
            self.row_width = 3
            filter_page = scene_data.get('filter_page', 0)
            
            # Получаем кнопки фильтра
            filter_buttons = self.item_filter.get_buttons(
                current_page=filter_page,
                add_reset_button=True,
                reset_callback='reset_filter'
            )
            buttons.extend(filter_buttons)
            
            # Кнопка "Назад к списку"
            buttons.append({
                'text': '↪️ Назад к списку',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'back_to_list'
                ),
                'next_line': True
            })
        
        # Кнопки для детального просмотра
        elif exchange_state == 'details':
            exchange_id = scene_data.get('selected_exchange_id')
            
            # Используем кеш, если доступен
            cache_key = f'exchange_details_{exchange_id}'
            cached_data = scene_data.get(cache_key)
            
            if cached_data:
                exchange = cached_data.get('exchange')
            else:
                # Если кеш недоступен, делаем запрос
                exchange = await get_exchange(id=exchange_id)
            
            # Проверяем, не является ли это предложением текущей компании
            if isinstance(exchange, dict):
                seller_id = exchange.get('company_id')
                
                if seller_id != company_id:
                    # Кнопка покупки (если это не наше предложение)
                    buttons.append({
                        'text': '💰 Купить',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'buy_exchange',
                            str(exchange_id)
                        )
                    })
                else:
                    # Информация о том, что это наше предложение
                    buttons.append({
                        'text': '⚠️ Ваше предложение',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'own_offer'
                        )
                    })
            
            # Кнопка "Назад к списку"
            buttons.append({
                'text': '↪️ Назад к списку',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'back_to_list'
                ),
                'next_line': True
            })
        
        # Кнопки для выбора типа предложения
        elif exchange_state == 'create_select_type':
            buttons.append({
                'text': '💰 За деньги',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_type',
                    'money'
                ),
                'ignore_row': True
            })
            
            buttons.append({
                'text': '⇄ Бартер',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_type',
                    'barter'
                ),
                'ignore_row': True
            })
            
            buttons.append({
                'text': '↪️ Отмена',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'cancel_create'
                ),
                'next_line': True
            })
        
        # Кнопки для выбора товара для продажи
        elif exchange_state == 'create_select_sell_resource':
            # Получаем инвентарь компании
            company_data = await get_company(id=company_id)
            
            # В API инвентарь называется 'warehouses', а не 'inventory'
            if isinstance(company_data, dict) and 'warehouses' in company_data:
                inv_items = company_data['warehouses']
                
                # Проверяем, есть ли товары в инвентаре
                has_items = False
                for resource_key, amount in inv_items.items():
                    if amount > 0:
                        resource = RESOURCES.get_resource(resource_key)
                        if resource:
                            has_items = True
                            buttons.append({
                                'text': f'{resource.emoji} {resource.label} ({amount})',
                                'callback_data': callback_generator(
                                    self.scene.__scene_name__,
                                    'create_sell_res',
                                    resource_key
                                ),
                                'ignore_row': True
                            })
                
                # Если нет товаров, показываем предупреждение
                if not has_items:
                    buttons.append({
                        'text': '⚠️ Склад пуст',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'inventory_empty'
                        ),
                        'ignore_row': True
                    })
            else:
                # Если не удалось получить инвентарь
                buttons.append({
                    'text': '⚠️ Не удалось загрузить склад',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'inventory_error'
                    ),
                    'ignore_row': True
                })
            
            buttons.append({
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'cancel_create'
                ),
                'next_line': True
            })
        
        # Кнопки для ввода количества за сделку
        elif exchange_state == 'create_input_amount':
            buttons.append({
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_back_to_sell_select'
                ),
                'next_line': True
            })
        
        # Кнопки для ввода количества сделок
        elif exchange_state == 'create_input_count':
            buttons.append({
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_back_to_amount'
                ),
                'next_line': True
            })
        
        # Кнопки для ввода цены
        elif exchange_state == 'create_input_price':
            buttons.append({
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_back_to_count'
                ),
                'next_line': True
            })
        
        # Кнопки для выбора ресурса для бартера
        elif exchange_state == 'create_select_barter_resource':
            # Показываем все ресурсы для выбора
            for resource_key, resource in RESOURCES.resources.items():
                buttons.append({
                    'text': f'{resource.emoji} {resource.label}',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'create_barter_res',
                        resource_key
                    ),
                    'ignore_row': True
                })
            
            buttons.append({
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_back_to_count'
                ),
                'next_line': True
            })
        
        # Кнопки для ввода количества ресурса для бартера
        elif exchange_state == 'create_input_barter_amount':
            
            buttons.append({
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_back_to_barter_select'
                ),
                'next_line': True
            })
        
        # Кнопки подтверждения
        elif exchange_state == 'create_confirm':
            buttons.append({
                'text': '✅ Подтвердить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'create_confirm_final'
                ),
                'ignore_row': True
            })
            
            buttons.append({
                'text': '↪️ Отмена',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'cancel_create'
                ),
                'next_line': True
            })
        
        # self.row_width = 1
        return buttons
    
    # Обработчики callback'ов
    
    @Page.on_callback('view_exchange')
    async def view_exchange_handler(self, callback: CallbackQuery, args: list):
        """Просмотр детальной информации о предложении"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID предложения", show_alert=True)
            return
        
        exchange_id = int(args[1])
        scene_data = self.scene.get_data('scene')
        
        scene_data['exchange_state'] = 'details'
        scene_data['selected_exchange_id'] = exchange_id
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
    
    @Page.on_callback('list_page')
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
    
    @Page.on_callback('open_filter')
    async def open_filter_handler(self, callback: CallbackQuery, args: list):
        """Открыть экран фильтра"""
        scene_data = self.scene.get_data('scene')
        
        scene_data['exchange_state'] = 'filter'
        scene_data['filter_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer("🔍 Выберите ресурс для поиска")
    
    @Page.on_callback('filter_page')
    async def filter_page_handler(self, callback: CallbackQuery, args: list):
        """Переключение страницы фильтра"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        page = int(args[1])
        scene_data = self.scene.get_data('scene')
        
        scene_data['filter_page'] = page
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
    
    @Page.on_callback('filter_resource')
    async def filter_resource_handler(self, callback: CallbackQuery, args: list):
        """Применение фильтра по ресурсу"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ресурс", show_alert=True)
            return
        
        resource_id = args[1]
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('session')
        
        # Проверяем существование ресурса
        if not self.item_filter.resource_exists(resource_id):
            await callback.answer("❌ Ресурс не найден", show_alert=True)
            return
        
        # Проверяем, есть ли предложения с этим ресурсом
        exchanges = await get_exchanges(
            session_id=session_id,
            sell_resource=resource_id
        )
        
        if isinstance(exchanges, str) or not exchanges or len(exchanges) == 0:
            resource_name = self.item_filter.get_resource_name(resource_id)
            await callback.answer(
                f"❌ Нет предложений с ресурсом {resource_name}",
                show_alert=True
            )
            return
        
        # Применяем фильтр
        scene_data['filter_resource'] = resource_id
        scene_data['exchange_state'] = 'list'
        scene_data['list_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        resource_name = self.item_filter.get_resource_name(resource_id)
        await self.scene.update_message()
        await callback.answer(f"✅ Поиск: {resource_name}")
    
    @Page.on_callback('reset_filter')
    async def reset_filter_handler(self, callback: CallbackQuery, args: list):
        """Сброс фильтра"""
        scene_data = self.scene.get_data('scene')
        
        scene_data['filter_resource'] = None
        scene_data['exchange_state'] = 'list'
        scene_data['list_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer("🔄 Поиск сброшен")
    
    @Page.on_callback('back_to_list')
    async def back_to_list_handler(self, callback: CallbackQuery, args: list):
        """Возврат к списку предложений"""
        scene_data = self.scene.get_data('scene')
        
        # Очищаем кеш деталей предложения
        exchange_id = scene_data.get('selected_exchange_id')
        if exchange_id:
            cache_key = f'exchange_details_{exchange_id}'
            if cache_key in scene_data:
                del scene_data[cache_key]
        
        scene_data['exchange_state'] = 'list'
        scene_data['selected_exchange_id'] = None
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
    
    @Page.on_callback('buy_exchange')
    async def buy_exchange_handler(self, callback: CallbackQuery, args: list):
        """Покупка предложения"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID предложения", show_alert=True)
            return
        
        exchange_id = int(args[1])
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        # Попытка покупки (количество = 1 сделка)
        result = await buy_exchange_offer(
            offer_id=exchange_id,
            buyer_company_id=company_id,
            quantity=1
        )
        
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
            return
        
        if isinstance(result, dict) and 'error' in result:
            await callback.answer(f"❌ {result['error']}", show_alert=True)
            return
        
        # Успешная покупка
        scene_data['exchange_state'] = 'list'
        scene_data['selected_exchange_id'] = None
        scene_data['success_message'] = 'Сделка успешно совершена!'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer("✅ Сделка совершена!", show_alert=True)
    
    @Page.on_callback('create_offer')
    async def create_offer_handler(self, callback: CallbackQuery, args: list):
        """Начать создание нового предложения"""
        scene_data = self.scene.get_data('scene')
        
        # Очищаем предыдущие данные создания
        scene_data['exchange_state'] = 'create_select_type'
        scene_data['create_offer_type'] = None
        scene_data['create_sell_resource'] = None
        scene_data['create_sell_amount'] = None
        scene_data['create_count_offers'] = None
        scene_data['create_price'] = None
        scene_data['create_barter_resource'] = None
        scene_data['create_barter_amount'] = None
        
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
        await callback.answer("➕ Создание предложения")
    
    @Page.on_callback('own_offer')
    async def own_offer_handler(self, callback: CallbackQuery, args: list):
        """Обработка нажатия на своё предложение"""
        await callback.answer(
            "ℹ️ Это ваше предложение. Вы не можете купить его.",
            show_alert=False
        )
    
    @Page.on_callback('create_type')
    async def create_type_handler(self, callback: CallbackQuery, args: list):
        """Выбор типа предложения"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        offer_type = args[1]
        scene_data = self.scene.get_data('scene')
        
        scene_data['create_offer_type'] = offer_type
        scene_data['exchange_state'] = 'create_select_sell_resource'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        type_text = "💰 За деньги" if offer_type == 'money' else "⇄ Бартер"
        await callback.answer(f"Выбрано: {type_text}")
    
    @Page.on_callback('create_sell_res')
    async def create_sell_res_handler(self, callback: CallbackQuery, args: list):
        """Выбор товара для продажи"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        resource_id = args[1]
        scene_data = self.scene.get_data('scene')
        
        resource = RESOURCES.get_resource(resource_id)
        if not resource:
            await callback.answer("❌ Ресурс не найден", show_alert=True)
            return
        
        scene_data['create_sell_resource'] = resource_id
        scene_data['exchange_state'] = 'create_input_amount'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer(f"Выбрано: {resource.emoji} {resource.label}")
    
    @Page.on_text('int')
    async def handle_text_input(self, message: Message, value: int):
        """Обработка текстовых сообщений - ввод чисел"""
        scene_data = self.scene.get_data('scene')
        exchange_state = scene_data.get('exchange_state', 'list')
        
        # Проверка на положительное число
        if value <= 0:
            await message.answer("❌ Количество должно быть больше 0")
            return
        
        # Ввод количества за сделку
        if exchange_state == 'create_input_amount':
            scene_data['create_sell_amount'] = value
            scene_data['exchange_state'] = 'create_input_count'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        
        # Ввод количества сделок
        elif exchange_state == 'create_input_count':
            scene_data['create_count_offers'] = value
            
            # Переход к следующему шагу в зависимости от типа
            offer_type = scene_data.get('create_offer_type', 'money')
            if offer_type == 'money':
                scene_data['exchange_state'] = 'create_input_price'
            else:
                scene_data['exchange_state'] = 'create_select_barter_resource'
            
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        
        # Ввод цены
        elif exchange_state == 'create_input_price':
            scene_data['create_price'] = value
            scene_data['exchange_state'] = 'create_confirm'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        
        # Ввод количества ресурса для бартера
        elif exchange_state == 'create_input_barter_amount':
            scene_data['create_barter_amount'] = value
            scene_data['exchange_state'] = 'create_confirm'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        else:
            # Если состояние не поддерживает ввод текста
            await message.answer("❌ Ввод текста не поддерживается в текущем состоянии")
    
    @Page.on_callback('create_barter_res')
    async def create_barter_res_handler(self, callback: CallbackQuery, args: list):
        """Выбор ресурса для бартера"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка", show_alert=True)
            return
        
        resource_id = args[1]
        scene_data = self.scene.get_data('scene')
        
        resource = RESOURCES.get_resource(resource_id)
        if not resource:
            await callback.answer("❌ Ресурс не найден", show_alert=True)
            return
        
        scene_data['create_barter_resource'] = resource_id
        scene_data['exchange_state'] = 'create_input_barter_amount'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer(f"Выбрано: {resource.emoji} {resource.label}")
    
    @Page.on_callback('create_confirm_final')
    async def create_confirm_final_handler(self, callback: CallbackQuery, args: list):
        """Финальное подтверждение и создание предложения"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        # Собираем все данные
        sell_resource = scene_data.get('create_sell_resource')
        sell_amount = scene_data.get('create_sell_amount')
        count_offers = scene_data.get('create_count_offers')
        offer_type = scene_data.get('create_offer_type')
        price = scene_data.get('create_price')
        barter_resource = scene_data.get('create_barter_resource')
        barter_amount = scene_data.get('create_barter_amount')
        
        # Проверяем все необходимые данные
        if not all([sell_resource, sell_amount, count_offers, offer_type]):
            await callback.answer("❌ Не все данные заполнены", show_alert=True)
            return
        
        if offer_type == 'money' and not price:
            await callback.answer("❌ Не указана цена", show_alert=True)
            return
        
        if offer_type == 'barter' and (not barter_resource or not barter_amount):
            await callback.answer("❌ Не указаны условия бартера", show_alert=True)
            return
        
        # Создаём предложение
        result = await create_exchange_offer(
            company_id=company_id,
            session_id=session_id,
            sell_resource=sell_resource,
            sell_amount_per_trade=sell_amount,
            count_offers=count_offers,
            offer_type=offer_type,
            price=price if offer_type == 'money' else None,
            barter_resource=barter_resource if offer_type == 'barter' else None,
            barter_amount=barter_amount if offer_type == 'barter' else None
        )
        
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
            return
        
        if isinstance(result, dict) and 'error' in result:
            await callback.answer(f"❌ {result['error']}", show_alert=True)
            return
        
        # Успешное создание
        scene_data['exchange_state'] = 'list'
        scene_data['list_page'] = 0
        scene_data['success_message'] = 'Предложение успешно создано!'
        
        # Очищаем данные создания
        scene_data['create_offer_type'] = None
        scene_data['create_sell_resource'] = None
        scene_data['create_sell_amount'] = None
        scene_data['create_count_offers'] = None
        scene_data['create_price'] = None
        scene_data['create_barter_resource'] = None
        scene_data['create_barter_amount'] = None
        
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
        await callback.answer("✅ Предложение создано!", show_alert=True)
    
    @Page.on_callback('cancel_create')
    async def cancel_create_handler(self, callback: CallbackQuery, args: list):
        """Отмена создания предложения"""
        scene_data = self.scene.get_data('scene')
        
        scene_data['exchange_state'] = 'list'
        
        # Очищаем данные создания
        scene_data['create_offer_type'] = None
        scene_data['create_sell_resource'] = None
        scene_data['create_sell_amount'] = None
        scene_data['create_count_offers'] = None
        scene_data['create_price'] = None
        scene_data['create_barter_resource'] = None
        scene_data['create_barter_amount'] = None
        
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
        await callback.answer("❌ Создание отменено")
    
    @Page.on_callback('create_back_to_sell_select')
    async def create_back_to_sell_select_handler(self, callback: CallbackQuery, args: list):
        """Назад к выбору товара"""
        scene_data = self.scene.get_data('scene')
        scene_data['exchange_state'] = 'create_select_sell_resource'
        scene_data['create_sell_resource'] = None
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    @Page.on_callback('create_back_to_amount')
    async def create_back_to_amount_handler(self, callback: CallbackQuery, args: list):
        """Назад к вводу количества за сделку"""
        scene_data = self.scene.get_data('scene')
        scene_data['exchange_state'] = 'create_input_amount'
        scene_data['create_sell_amount'] = None
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    @Page.on_callback('create_back_to_count')
    async def create_back_to_count_handler(self, callback: CallbackQuery, args: list):
        """Назад к вводу количества сделок"""
        scene_data = self.scene.get_data('scene')
        scene_data['exchange_state'] = 'create_input_count'
        scene_data['create_count_offers'] = None
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    @Page.on_callback('create_back_to_barter_select')
    async def create_back_to_barter_select_handler(self, callback: CallbackQuery, args: list):
        """Назад к выбору ресурса для бартера"""
        scene_data = self.scene.get_data('scene')
        scene_data['exchange_state'] = 'create_select_barter_resource'
        scene_data['create_barter_resource'] = None
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    @Page.on_callback('inventory_empty')
    async def inventory_empty_handler(self, callback: CallbackQuery, args: list):
        """Обработка пустого инвентаря"""
        await callback.answer(
            "❌ На вашем складе нет товаров для продажи",
            show_alert=True
        )
    
    @Page.on_callback('inventory_error')
    async def inventory_error_handler(self, callback: CallbackQuery, args: list):
        """Обработка ошибки загрузки инвентаря"""
        await callback.answer(
            "❌ Не удалось загрузить склад. Попробуйте позже",
            show_alert=True
        )
        await self.scene.update_message()
    
    @Page.on_callback('page_info')
    async def page_info_handler(self, callback: CallbackQuery, args: list):
        """Информация о странице (ничего не делает, просто индикатор)"""
        pass
    
    @Page.on_callback('back_to_menu')
    async def back_to_menu_handler(self, callback: CallbackQuery, args: list):
        """Возврат в главное меню"""
        # Очищаем состояние страницы
        scene_data = self.scene.get_data('scene')
        scene_data['exchange_state'] = 'list'
        scene_data['list_page'] = 0
        scene_data['filter_page'] = 0
        scene_data['filter_resource'] = None
        scene_data['selected_exchange_id'] = None
        scene_data['success_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        # Переходим на страницу главного меню
        await self.scene.update_page('main-page')
        await callback.answer("↪️ Возврат в меню")
