from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_company, create_exchange_offer
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeCreateMain(OneUserPage):
    """Главная страница создания предложения"""
    
    __page_name__ = "exchange-create-page"
    
    async def data_preparate(self):
        """Инициализация данных"""
        # Инициализируем поля, если их нет
        if self.scene.get_key(self.__page_name__, 'offer_type') is None:
            await self.scene.update_key(self.__page_name__, 'offer_type', 'money')
    
    async def content_worker(self):
        """Генерация контента страницы"""
        sell_resource = self.scene.get_key(self.__page_name__, 'sell_resource')
        sell_amount = self.scene.get_key(self.__page_name__, 'sell_amount')
        count_offers = self.scene.get_key(self.__page_name__, 'count_offers')
        offer_type = self.scene.get_key(self.__page_name__, 'offer_type') or 'money'
        price = self.scene.get_key(self.__page_name__, 'price')
        barter_resource = self.scene.get_key(self.__page_name__, 'barter_resource')
        barter_amount = self.scene.get_key(self.__page_name__, 'barter_amount')
        error = self.scene.get_key(self.__page_name__, 'error')
        
        # Формируем текст товара
        if sell_resource:
            res = RESOURCES.get_resource(sell_resource)
            if res:
                sell_text = f"{res.emoji} {res.label}"
            else:
                sell_text = "Не выбран"
        else:
            sell_text = "Не выбран"
        
        sell_amount_text = str(sell_amount) if sell_amount else "Не установлено"
        count_offers_text = str(count_offers) if count_offers else "Не установлено"
        
        # Формируем текст типа
        type_text = "💰 За деньги" if offer_type == 'money' else "⇄ Бартер"
        
        # Формируем текст условий
        if offer_type == 'money':
            conditions_text = f"   Цена за сделку: {price if price else 'Не установлено'}"
        else:
            if barter_resource:
                res = RESOURCES.get_resource(barter_resource)
                if res:
                    barter_text = f"{res.emoji} {res.label}"
                else:
                    barter_text = "Не выбрано"
            else:
                barter_text = "Не выбрано"
            
            barter_amount_text = str(barter_amount) if barter_amount else "Не установлено"
            conditions_text = f"   За ресурс: {barter_text}\n   Количество за сделку: {barter_amount_text}"
        
        error_text = f"\n\n❌ Ошибка: {error}" if error else ""
        
        return self.content.format(
            sell_text=sell_text,
            sell_amount=sell_amount_text,
            count_offers=count_offers_text,
            type_text=type_text,
            conditions_text=conditions_text,
            error_text=error_text
        )
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        sell_resource = self.scene.get_key(self.__page_name__, 'sell_resource')
        sell_amount = self.scene.get_key(self.__page_name__, 'sell_amount')
        count_offers = self.scene.get_key(self.__page_name__, 'count_offers')
        offer_type = self.scene.get_key(self.__page_name__, 'offer_type') or 'money'
        price = self.scene.get_key(self.__page_name__, 'price')
        barter_resource = self.scene.get_key(self.__page_name__, 'barter_resource')
        barter_amount = self.scene.get_key(self.__page_name__, 'barter_amount')
        
        # Формируем текст товара для кнопки
        if sell_resource:
            res = RESOURCES.get_resource(sell_resource)
            if res:
                sell_text = f"{res.emoji} {res.label}"
            else:
                sell_text = "Не выбран"
        else:
            sell_text = "Не выбран"
        
        sell_amount_text = str(sell_amount) if sell_amount else "N"
        
        self.row_width = 2
        buttons = []
        
        # Кнопка выбора товара
        buttons.append({
            'text': f"📦 Товар: {sell_text} x{sell_amount_text}",
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'set_sell_resource'
            ),
            'ignore_row': True
        })
        
        # Кнопка выбора типа
        buttons.append({
            'text': f"{'💰 За монеты' if offer_type == 'money' else '⇄ Бартер'}",
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'change_offer_type'
            )
        })
        
        # Кнопка количества сделок
        buttons.append({
            'text': f"📊 Кол-во сделок: {count_offers if count_offers else 'N'}",
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'set_count_offers'
            )
        })
        
        # Кнопка условий
        if offer_type == 'money':
            price_text = str(price) if price else "N"
            buttons.append({
                'text': f"💰 Цена за сделку: {price_text}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'change_price'
                ),
                'ignore_row': True
            })
        else:
            if barter_resource:
                res = RESOURCES.get_resource(barter_resource)
                if res:
                    barter_text = f"{res.emoji} {res.label}"
                else:
                    barter_text = "Не выбрано"
            else:
                barter_text = "Не выбрано"
            
            barter_amount_text = str(barter_amount) if barter_amount else "N"
            buttons.append({
                'text': f"⇄ Бартер: {barter_text} x{barter_amount_text}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'set_barter_resource'
                ),
                'ignore_row': True
            })
        
        # Кнопки действий
        buttons.append({
            'text': '✅ Создать',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'create_exchange_offer'
            )
        })
        buttons.append({
            'text': '🔄 Очистить',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'clear_exchange_offer'
            )
        })
        
        return buttons
    
    @OneUserPage.on_text('int')
    async def input_handler(self, message: Message, value: int):
        """Обработка ввода чисел"""
        input_state = self.scene.get_key(self.__page_name__, 'input_state')
        
        # Сбрасываем ошибку
        await self.scene.update_key(self.__page_name__, 'error', None)
        
        # Ввод количества сделок
        if input_state == 'input_count_offers':
            if value <= 0:
                await self.scene.update_key(self.__page_name__, 'error', "Количество сделок должно быть больше нуля!")
                await self.scene.update_key(self.__page_name__, 'input_state', None)
                await self.scene.update_message()
                return
            
            sell_amount = self.scene.get_key(self.__page_name__, 'sell_amount')
            sell_resource = self.scene.get_key(self.__page_name__, 'sell_resource')
            total_needed = sell_amount * value
            
            # Проверяем наличие товара
            scene_data = self.scene.get_data('scene')
            company_id = scene_data.get('company_id')
            company_data = await get_company(id=company_id)
            
            if not isinstance(company_data, dict):
                await self.scene.update_key(self.__page_name__, 'error', "Не удалось получить данные компании")
                await self.scene.update_key(self.__page_name__, 'input_state', None)
                await self.scene.update_message()
                return
            
            warehouses = company_data.get('warehouses', {})
            available = warehouses.get(sell_resource, 0)
            
            if total_needed > available:
                await self.scene.update_key(self.__page_name__, 'error', f"Недостаточно товара! Требуется: {total_needed} ({sell_amount} x {value}), Доступно: {available}")
                await self.scene.update_key(self.__page_name__, 'input_state', None)
                await self.scene.update_message()
                return
            
            await self.scene.update_key(self.__page_name__, 'count_offers', value)
            await self.scene.update_key(self.__page_name__, 'input_state', None)
            await self.scene.update_message()
        
        # Ввод цены
        elif input_state == 'input_price':
            if value <= 0:
                await self.scene.update_key(self.__page_name__, 'error', "Цена должна быть больше нуля!")
                await self.scene.update_key(self.__page_name__, 'input_state', None)
                await self.scene.update_message()
                return
            
            await self.scene.update_key(self.__page_name__, 'price', value)
            await self.scene.update_key(self.__page_name__, 'input_state', None)
            await self.scene.update_message()
    
    @OneUserPage.on_callback('set_sell_resource')
    async def set_sell_resource_handler(self, callback: CallbackQuery, args: list):
        """Открыть выбор ресурса для продажи"""
        await self.scene.update_page('exchange-create-set-sell-page')
    
    @OneUserPage.on_callback('change_offer_type')
    async def change_offer_type_handler(self, callback: CallbackQuery, args: list):
        """Переключение типа предложения"""
        offer_type = self.scene.get_key(self.__page_name__, 'offer_type')
        
        if offer_type == 'money':
            await self.scene.update_key(self.__page_name__, 'offer_type', 'barter')
            await self.scene.update_key(self.__page_name__, 'price', None)
        else:
            await self.scene.update_key(self.__page_name__, 'offer_type', 'money')
            await self.scene.update_key(self.__page_name__, 'barter_resource', None)
            await self.scene.update_key(self.__page_name__, 'barter_amount', None)
        
        await self.scene.update_message()
    
    @OneUserPage.on_callback('set_count_offers')
    async def set_count_offers_handler(self, callback: CallbackQuery, args: list):
        """Начать ввод количества сделок"""
        await self.scene.update_key(self.__page_name__, 'error', None)
        
        sell_resource = self.scene.get_key(self.__page_name__, 'sell_resource')
        sell_amount = self.scene.get_key(self.__page_name__, 'sell_amount')
        
        if not sell_resource or not sell_amount:
            await self.scene.update_key(self.__page_name__, 'error', "Сначала выберите ресурс для продажи и количество за сделку!")
            await self.scene.update_message()
            await callback.answer()
            return
        
        await self.scene.update_key(self.__page_name__, 'input_state', 'input_count_offers')
        await callback.answer("Введите количество сделок в чат", show_alert=True)
    
    @OneUserPage.on_callback('change_price')
    async def change_price_handler(self, callback: CallbackQuery, args: list):
        """Начать ввод цены"""
        await self.scene.update_key(self.__page_name__, 'error', None)
        
        sell_resource = self.scene.get_key(self.__page_name__, 'sell_resource')
        
        if not sell_resource:
            await self.scene.update_key(self.__page_name__, 'error', "Сначала выберите ресурс для продажи!")
            await self.scene.update_message()
            await callback.answer()
            return
        
        await self.scene.update_key(self.__page_name__, 'input_state', 'input_price')
        await callback.answer("Введите цену в чат", show_alert=True)
    
    @OneUserPage.on_callback('set_barter_resource')
    async def set_barter_resource_handler(self, callback: CallbackQuery, args: list):
        """Открыть выбор ресурса для бартера"""
        await self.scene.update_page('exchange-create-set-barter-page')
    
    @OneUserPage.on_callback('create_exchange_offer')
    async def create_exchange_offer_handler(self, callback: CallbackQuery, args: list):
        """Создание предложения"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        sell_resource = self.scene.get_key(self.__page_name__, 'sell_resource')
        sell_amount = self.scene.get_key(self.__page_name__, 'sell_amount')
        count_offers = self.scene.get_key(self.__page_name__, 'count_offers')
        offer_type = self.scene.get_key(self.__page_name__, 'offer_type') or 'money'
        price = self.scene.get_key(self.__page_name__, 'price')
        barter_resource = self.scene.get_key(self.__page_name__, 'barter_resource')
        barter_amount = self.scene.get_key(self.__page_name__, 'barter_amount')
        
        # Проверка полей
        if not all([sell_resource, sell_amount, count_offers]):
            await callback.answer("❌ Заполните все обязательные поля", show_alert=True)
            return
        
        if offer_type == 'money' and not price:
            await callback.answer("❌ Укажите цену", show_alert=True)
            return
        
        if offer_type == 'barter' and not all([barter_resource, barter_amount]):
            await callback.answer("❌ Укажите условия бартера", show_alert=True)
            return
        
        # Создание предложения
        result = await create_exchange_offer(
            company_id=company_id,
            session_id=session_id,
            sell_resource=sell_resource,
            sell_amount_per_trade=sell_amount,
            count_offers=count_offers,
            offer_type=offer_type,
            price=price,
            barter_resource=barter_resource,
            barter_amount=barter_amount
        )
        
        if "error" in result:
            await callback.answer(f"{result['error']}", show_alert=True)
        else:
            # Очищаем данные
            await self.scene.update_key(self.__page_name__, 'sell_resource', None)
            await self.scene.update_key(self.__page_name__, 'sell_amount', None)
            await self.scene.update_key(self.__page_name__, 'count_offers', None)
            await self.scene.update_key(self.__page_name__, 'offer_type', 'money')
            await self.scene.update_key(self.__page_name__, 'price', None)
            await self.scene.update_key(self.__page_name__, 'barter_resource', None)
            await self.scene.update_key(self.__page_name__, 'barter_amount', None)
            await self.scene.update_key(self.__page_name__, 'error', None)
            await self.scene.update_key(self.__page_name__, 'input_state', None)
            
            await callback.answer("✅ Предложение создано!", show_alert=True)
            await self.scene.update_page('exchange-main-page')
    
    @OneUserPage.on_callback('clear_exchange_offer')
    async def clear_exchange_offer_handler(self, callback: CallbackQuery, args: list):
        """Очистка формы"""
        await self.scene.update_key(self.__page_name__, 'sell_resource', None)
        await self.scene.update_key(self.__page_name__, 'sell_amount', None)
        await self.scene.update_key(self.__page_name__, 'count_offers', None)
        await self.scene.update_key(self.__page_name__, 'offer_type', 'money')
        await self.scene.update_key(self.__page_name__, 'price', None)
        await self.scene.update_key(self.__page_name__, 'barter_resource', None)
        await self.scene.update_key(self.__page_name__, 'barter_amount', None)
        await self.scene.update_key(self.__page_name__, 'error', None)
        await self.scene.update_key(self.__page_name__, 'input_state', None)
        
        await self.scene.update_message()
        await callback.answer("🔄 Форма очищена")


class ExchangeCreateSetSell(OneUserPage):
    """Выбор ресурса для продажи"""
    
    __page_name__ = "exchange-create-set-sell-page"
    
    async def data_preparate(self):
        """Инициализация"""
        if self.scene.get_key(self.__page_name__, 'page') is None:
            await self.scene.update_key(self.__page_name__, 'page', 0)
        if self.scene.get_key(self.__page_name__, 'state') is None:
            await self.scene.update_key(self.__page_name__, 'state', 'select_resource')
        if self.scene.get_key(self.__page_name__, 'error') is None:
            await self.scene.update_key(self.__page_name__, 'error', None)
    
    async def content_worker(self):
        """Контент"""
        state = self.scene.get_key(self.__page_name__, 'state') or 'select_resource'
        error = self.scene.get_key(self.__page_name__, 'error')
        
        if state == 'select_resource':
            content_text = "📦 *Выбор товара для продажи*\n\nВыберите ресурс со склада, который хотите продать:"
        else:  # input_count
            selected_resource_id = self.scene.get_key(self.__page_name__, 'selected_resource')
            max_amount = self.scene.get_key(self.__page_name__, 'max_amount') or 0
            
            if selected_resource_id:
                resource = RESOURCES.get_resource(selected_resource_id)
                sell_emoji = resource.emoji if resource else ""
                sell_name = resource.label if resource else ""
            else:
                sell_emoji = ""
                sell_name = ""
            
            content_text = self.content.format(
                sell_emoji=sell_emoji,
                sell_name=sell_name,
                max_amount=max_amount
            )
        
        if error:
            content_text += f"\n\n❌ Ошибка: {error}"
        
        return content_text
    
    async def buttons_worker(self):
        """Кнопки"""
        state = self.scene.get_key(self.__page_name__, 'state') or 'select_resource'
        buttons = []
        
        if state == 'input_count':
            # Кнопки с долями
            max_amount = self.scene.get_key(self.__page_name__, 'max_amount') or 0
            
            self.row_width = 4
            fractions = [
                ("1/4", max_amount // 4),
                ("2/4", max_amount // 2),
                ("3/4", (max_amount * 3) // 4),
                ("4/4", max_amount)
            ]
            
            for label, amount in fractions:
                if amount > 0:
                    buttons.append({
                        'text': f"({amount})",
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'set_amount',
                            str(amount)
                        )
                    })
            
            return buttons
        
        # Список ресурсов
        cur_page = self.scene.get_key(self.__page_name__, 'page') or 0
        self.row_width = 1
        
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        company_data = await get_company(id=company_id)
        
        if not isinstance(company_data, dict):
            warehouse = {}
        else:
            warehouse = company_data.get('warehouses', {})
        
        # Фильтруем ресурсы
        all_resources = []
        for resource_id, resource in RESOURCES.resources.items():
            if resource_id in warehouse and warehouse[resource_id] > 0:
                all_resources.append({
                    'id': resource_id,
                    'name': resource.label,
                    'emoji': resource.emoji,
                    'level': resource.lvl,
                    'amount': warehouse[resource_id]
                })
        
        if len(all_resources) == 0:
            buttons.append({
                'text': '❌ На складе нет ресурсов',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'no_resources'
                ),
                'ignore_row': True
            })
            return buttons
        
        all_resources.sort(key=lambda x: (x['level'], x['name']))
        
        # Пагинация
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        cur_page = cur_page % total_pages
        await self.scene.update_key(self.__page_name__, 'page', cur_page)
        
        start_idx = cur_page * items_per_page
        end_idx = start_idx + items_per_page
        page_resources = all_resources[start_idx:end_idx]
        
        for resource in page_resources:
            buttons.append({
                'text': f"{resource['emoji']} {resource['name']} (x{resource['amount']})",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'select_resource',
                    resource['id']
                ),
                'ignore_row': True
            })
        
        # Навигация
        self.row_width = 3
        buttons.append({
            'text': '◀️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_page'
            )
        })
        buttons.append({
            'text': f"📄 {cur_page + 1}/{total_pages}",
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'page_info'
            )
        })
        buttons.append({
            'text': 'Вперёд ▶️',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'next_page'
            )
        })
        
        return buttons
    
    @OneUserPage.on_callback('select_resource')
    async def select_resource_handler(self, callback: CallbackQuery, args: list):
        """Выбор ресурса"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка")
            return
        
        resource_id = args[1]
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        company_data = await get_company(id=company_id)
        if not isinstance(company_data, dict):
            await callback.answer("❌ Ошибка получения данных")
            return
        
        warehouses = company_data.get('warehouses', {})
        max_amount = warehouses.get(resource_id, 0)
        
        if max_amount <= 0:
            await callback.answer("❌ Ресурса нет на складе")
            return
        
        await self.scene.update_key(self.__page_name__, 'selected_resource', resource_id)
        await self.scene.update_key(self.__page_name__, 'max_amount', max_amount)
        await self.scene.update_key(self.__page_name__, 'state', 'input_count')
        
        await self.scene.update_message()
        await callback.answer("✅ Ресурс выбран")
    
    @OneUserPage.on_callback('set_amount')
    async def set_amount_handler(self, callback: CallbackQuery, args: list):
        """Установка количества"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка")
            return
        
        amount = int(args[1])
        max_amount = self.scene.get_key(self.__page_name__, 'max_amount') or 0
        
        if amount <= 0 or amount > max_amount:
            await callback.answer(f"❌ Некорректное количество")
            return
        
        resource_id = self.scene.get_key(self.__page_name__, 'selected_resource')
        await self.scene.update_key('exchange-create-page', 'sell_resource', resource_id)
        await self.scene.update_key('exchange-create-page', 'sell_amount', amount)
        await self.scene.update_key(self.__page_name__, 'state', 'select_resource')
        
        await self.scene.update_page('exchange-create-page')
        await callback.answer(f"✅ Выбрано: {amount} шт.")
    
    @OneUserPage.on_text('int')
    async def input_count_handler(self, message: Message, value: int):
        """Ввод количества"""
        state = self.scene.get_key(self.__page_name__, 'state')
        
        await self.scene.update_key(self.__page_name__, 'error', None)
        
        if state != 'input_count':
            await self.scene.update_key(self.__page_name__, 'error', "Сначала выберите ресурс!")
            await self.scene.update_message()
            return
        
        max_amount = self.scene.get_key(self.__page_name__, 'max_amount') or 0
        
        if value <= 0:
            await self.scene.update_key(self.__page_name__, 'error', "Количество должно быть больше нуля!")
            await self.scene.update_message()
            return
        
        if value > max_amount:
            await self.scene.update_key(self.__page_name__, 'error', f"У вас нет столько! Доступно: {max_amount}")
            await self.scene.update_message()
            return
        
        resource_id = self.scene.get_key(self.__page_name__, 'selected_resource')
        await self.scene.update_key('exchange-create-page', 'sell_resource', resource_id)
        await self.scene.update_key('exchange-create-page', 'sell_amount', value)
        await self.scene.update_key(self.__page_name__, 'state', 'select_resource')
        
        await self.scene.update_page('exchange-create-page')
    
    @OneUserPage.on_callback('next_page')
    async def next_page_handler(self, callback: CallbackQuery, args: list):
        """Следующая страница"""
        cur_page = self.scene.get_key(self.__page_name__, 'page') or 0
        
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        company_data = await get_company(id=company_id)
        warehouse = company_data.get('warehouses', {}) if isinstance(company_data, dict) else {}
        
        all_resources = [r for r in RESOURCES.resources.items() if r[0] in warehouse and warehouse[r[0]] > 0]
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        await self.scene.update_key(self.__page_name__, 'page', (cur_page + 1) % total_pages)
        await self.scene.update_message()
    
    @OneUserPage.on_callback('back_page')
    async def back_page_handler(self, callback: CallbackQuery, args: list):
        """Предыдущая страница"""
        cur_page = self.scene.get_key(self.__page_name__, 'page') or 0
        
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        company_data = await get_company(id=company_id)
        warehouse = company_data.get('warehouses', {}) if isinstance(company_data, dict) else {}
        
        all_resources = [r for r in RESOURCES.resources.items() if r[0] in warehouse and warehouse[r[0]] > 0]
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        await self.scene.update_key(self.__page_name__, 'page', (cur_page - 1) % total_pages)
        await self.scene.update_message()
    
    @OneUserPage.on_callback('page_info')
    async def page_info_handler(self, callback: CallbackQuery, args: list):
        """Информация о странице"""
        await callback.answer("Информация о странице")


class ExchangeCreateSetBarter(OneUserPage):
    """Выбор ресурса для бартера"""
    
    __page_name__ = "exchange-create-set-barter-page"
    
    async def data_preparate(self):
        """Инициализация"""
        if self.scene.get_key(self.__page_name__, 'page') is None:
            await self.scene.update_key(self.__page_name__, 'page', 0)
        if self.scene.get_key(self.__page_name__, 'state') is None:
            await self.scene.update_key(self.__page_name__, 'state', 'select_resource')
        if self.scene.get_key(self.__page_name__, 'error') is None:
            await self.scene.update_key(self.__page_name__, 'error', None)
    
    async def content_worker(self):
        """Контент"""
        state = self.scene.get_key(self.__page_name__, 'state') or 'select_resource'
        error = self.scene.get_key(self.__page_name__, 'error')
        
        if state == 'select_resource':
            content_text = "⇄ *Выбор ресурса для бартера*\n\nВыберите ресурс, который покупатель должен отдать в обмен:"
        else:  # input_count
            selected_resource_id = self.scene.get_key(self.__page_name__, 'selected_resource')
            
            if selected_resource_id:
                resource = RESOURCES.get_resource(selected_resource_id)
                barter_emoji = resource.emoji if resource else ""
                barter_name = resource.label if resource else ""
            else:
                barter_emoji = ""
                barter_name = ""
            
            content_text = self.content.format(
                barter_emoji=barter_emoji,
                barter_name=barter_name
            )
        
        if error:
            content_text += f"\n\n❌ Ошибка: {error}"
        
        return content_text
    
    async def buttons_worker(self):
        """Кнопки"""
        state = self.scene.get_key(self.__page_name__, 'state') or 'select_resource'
        
        if state == 'input_count':
            return []
        
        # Список ресурсов
        cur_page = self.scene.get_key(self.__page_name__, 'page') or 0
        self.row_width = 1
        
        all_resources = []
        for resource_id, resource in RESOURCES.resources.items():
            all_resources.append({
                'id': resource_id,
                'name': resource.label,
                'emoji': resource.emoji,
                'level': resource.lvl
            })
        
        all_resources.sort(key=lambda x: (x['level'], x['name']))
        
        # Пагинация
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        cur_page = cur_page % total_pages
        await self.scene.update_key(self.__page_name__, 'page', cur_page)
        
        start_idx = cur_page * items_per_page
        end_idx = start_idx + items_per_page
        page_resources = all_resources[start_idx:end_idx]
        
        buttons = []
        for resource in page_resources:
            buttons.append({
                'text': f"{resource['emoji']} {resource['name']}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'select_resource',
                    resource['id']
                ),
                'ignore_row': True
            })
        
        # Навигация
        self.row_width = 3
        buttons.append({
            'text': '◀️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_page'
            )
        })
        buttons.append({
            'text': f"📄 {cur_page + 1}/{total_pages}",
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'page_info'
            )
        })
        buttons.append({
            'text': 'Вперёд ▶️',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'next_page'
            )
        })
        
        return buttons
    
    @OneUserPage.on_callback('select_resource')
    async def select_resource_handler(self, callback: CallbackQuery, args: list):
        """Выбор ресурса"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка")
            return
        
        resource_id = args[1]
        
        await self.scene.update_key(self.__page_name__, 'selected_resource', resource_id)
        await self.scene.update_key(self.__page_name__, 'state', 'input_count')
        
        await self.scene.update_message()
        await callback.answer("✅ Ресурс выбран! Введите количество в чат")
    
    @OneUserPage.on_text('int')
    async def input_count_handler(self, message: Message, value: int):
        """Ввод количества"""
        state = self.scene.get_key(self.__page_name__, 'state')
        
        await self.scene.update_key(self.__page_name__, 'error', None)
        
        if state != 'input_count':
            await self.scene.update_key(self.__page_name__, 'error', "Сначала выберите ресурс!")
            await self.scene.update_message()
            return
        
        if value <= 0:
            await self.scene.update_key(self.__page_name__, 'error', "Количество должно быть больше нуля!")
            await self.scene.update_message()
            return
        
        resource_id = self.scene.get_key(self.__page_name__, 'selected_resource')
        await self.scene.update_key('exchange-create-page', 'barter_resource', resource_id)
        await self.scene.update_key('exchange-create-page', 'barter_amount', value)
        await self.scene.update_key(self.__page_name__, 'state', 'select_resource')
        
        await self.scene.update_page('exchange-create-page')
    
    @OneUserPage.on_callback('next_page')
    async def next_page_handler(self, callback: CallbackQuery, args: list):
        """Следующая страница"""
        cur_page = self.scene.get_key(self.__page_name__, 'page') or 0
        
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        await self.scene.update_key(self.__page_name__, 'page', (cur_page + 1) % total_pages)
        await self.scene.update_message()
    
    @OneUserPage.on_callback('back_page')
    async def back_page_handler(self, callback: CallbackQuery, args: list):
        """Предыдущая страница"""
        cur_page = self.scene.get_key(self.__page_name__, 'page') or 0
        
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        await self.scene.update_key(self.__page_name__, 'page', (cur_page - 1) % total_pages)
        await self.scene.update_message()
    
    @OneUserPage.on_callback('page_info')
    async def page_info_handler(self, callback: CallbackQuery, args: list):
        """Информация о странице"""
        await callback.answer("Информация о странице")
