from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_exchange, update_exchange_offer
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeUpdate(OneUserPage):
    """Страница изменения предложения на бирже"""
    
    __page_name__ = "exchange-update-page"
    __for_blocked_pages__ = ["exchange-main-page"]
    
    async def data_preparate(self):
        """Инициализация данных из выбранного предложения"""
        scene_data = self.scene.get_data('scene')
        exchange_id = scene_data.get('selected_exchange_id')
        
        if not exchange_id:
            return
        
        # Проверяем, загружены ли уже данные
        if self.scene.get_key(self.__page_name__, 'offer_id') is not None:
            return
        
        # Получаем данные предложения
        exchange = await get_exchange(id=exchange_id)
        
        if isinstance(exchange, str) or not exchange:
            return
        
        # Сохраняем данные для редактирования
        await self.scene.update_key(self.__page_name__, 'offer_id', exchange_id)
        await self.scene.update_key(self.__page_name__, 'sell_resource', exchange.get('sell_resource'))
        await self.scene.update_key(self.__page_name__, 'sell_amount_per_trade', exchange.get('sell_amount_per_trade'))
        await self.scene.update_key(self.__page_name__, 'offer_type', exchange.get('offer_type'))
        await self.scene.update_key(self.__page_name__, 'price', exchange.get('price'))
        await self.scene.update_key(self.__page_name__, 'barter_resource', exchange.get('barter_resource'))
        await self.scene.update_key(self.__page_name__, 'barter_amount', exchange.get('barter_amount'))
    
    async def content_worker(self):
        """Генерация контента страницы"""
        sell_resource = self.scene.get_key(self.__page_name__, 'sell_resource')
        sell_amount_per_trade = self.scene.get_key(self.__page_name__, 'sell_amount_per_trade')
        offer_type = self.scene.get_key(self.__page_name__, 'offer_type')
        price = self.scene.get_key(self.__page_name__, 'price')
        barter_resource = self.scene.get_key(self.__page_name__, 'barter_resource')
        barter_amount = self.scene.get_key(self.__page_name__, 'barter_amount')
        error = self.scene.get_key(self.__page_name__, 'error')
        
        # Формируем текст товара
        if sell_resource:
            res = RESOURCES.get_resource(sell_resource)
            if res:
                sell_text = f"{res.emoji} {res.label} x{sell_amount_per_trade}"
            else:
                sell_text = "Неизвестный товар"
        else:
            sell_text = "Не загружено"
        
        # Формируем текст условий
        if offer_type == 'money':
            conditions_text = f"   💰 Цена за сделку: {price if price else 'Не установлено'}"
        elif offer_type == 'barter':
            if barter_resource:
                res = RESOURCES.get_resource(barter_resource)
                if res:
                    barter_text = f"{res.emoji} {res.label}"
                else:
                    barter_text = "Неизвестный ресурс"
            else:
                barter_text = "Не установлено"
            
            barter_amount_text = str(barter_amount) if barter_amount else "Не установлено"
            conditions_text = f"   ⇄ За ресурс: {barter_text}\n   ⇄ Количество за сделку: {barter_amount_text}"
        else:
            conditions_text = "   Неизвестный тип предложения"
        
        error_text = f"\n\n❌ Ошибка: {error}" if error else ""
        
        return self.content.format(
            sell_text=sell_text,
            conditions_text=conditions_text,
            error_text=error_text
        )
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        sell_amount_per_trade = self.scene.get_key(self.__page_name__, 'sell_amount_per_trade')
        offer_type = self.scene.get_key(self.__page_name__, 'offer_type')
        price = self.scene.get_key(self.__page_name__, 'price')
        barter_amount = self.scene.get_key(self.__page_name__, 'barter_amount')
        
        self.row_width = 1
        buttons = []
        
        # Кнопка изменения количества товара за сделку
        buttons.append({
            'text': f"📦 Кол-во за сделку: {sell_amount_per_trade if sell_amount_per_trade else 'N'}",
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'change_sell_amount'
            ),
            'ignore_row': True
        })
        
        # Кнопки в зависимости от типа предложения
        if offer_type == 'money':
            # Кнопка изменения цены
            price_text = str(price) if price else "N"
            buttons.append({
                'text': f"💰 Цена за сделку: {price_text}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'change_price'
                ),
                'ignore_row': True
            })
        elif offer_type == 'barter':
            # Кнопка изменения количества бартерного ресурса
            barter_amount_text = str(barter_amount) if barter_amount else "N"
            buttons.append({
                'text': f"⇄ Кол-во бартера: {barter_amount_text}",
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'change_barter_amount'
                ),
                'ignore_row': True
            })
        
        # Кнопка сохранения изменений
        buttons.append({
            'text': '✅ Сохранить изменения',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'save_changes'
            ),
            'ignore_row': True
        })
        
        return buttons
    
    @OneUserPage.on_text('int')
    async def input_handler(self, message: Message, value: int):
        """Обработка ввода чисел"""
        input_state = self.scene.get_key(self.__page_name__, 'input_state')
        
        # Сбрасываем ошибку
        await self.scene.update_key(self.__page_name__, 'error', None)
        
        # Ввод количества товара за сделку
        if input_state == 'input_sell_amount':
            if value <= 0:
                await self.scene.update_key(self.__page_name__, 'error', "Количество должно быть больше нуля!")
                await self.scene.update_key(self.__page_name__, 'input_state', None)
                await self.scene.update_message()
                return
            
            await self.scene.update_key(self.__page_name__, 'sell_amount_per_trade', value)
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
        
        # Ввод количества бартерного ресурса
        elif input_state == 'input_barter_amount':
            if value <= 0:
                await self.scene.update_key(self.__page_name__, 'error', "Количество должно быть больше нуля!")
                await self.scene.update_key(self.__page_name__, 'input_state', None)
                await self.scene.update_message()
                return
            
            await self.scene.update_key(self.__page_name__, 'barter_amount', value)
            await self.scene.update_key(self.__page_name__, 'input_state', None)
            await self.scene.update_message()
    
    @OneUserPage.on_callback('change_sell_amount')
    async def change_sell_amount_handler(self, callback: CallbackQuery, args: list):
        """Начать ввод количества товара за сделку"""
        await self.scene.update_key(self.__page_name__, 'error', None)
        await self.scene.update_key(self.__page_name__, 'input_state', 'input_sell_amount')
        await callback.answer("Введите новое количество товара за сделку в чат", show_alert=True)
    
    @OneUserPage.on_callback('change_price')
    async def change_price_handler(self, callback: CallbackQuery, args: list):
        """Начать ввод цены"""
        await self.scene.update_key(self.__page_name__, 'error', None)
        await self.scene.update_key(self.__page_name__, 'input_state', 'input_price')
        await callback.answer("Введите новую цену в чат", show_alert=True)
    
    @OneUserPage.on_callback('change_barter_amount')
    async def change_barter_amount_handler(self, callback: CallbackQuery, args: list):
        """Начать ввод количества бартерного ресурса"""
        await self.scene.update_key(self.__page_name__, 'error', None)
        await self.scene.update_key(self.__page_name__, 'input_state', 'input_barter_amount')
        await callback.answer("Введите новое количество бартерного ресурса в чат", show_alert=True)
    
    @OneUserPage.on_callback('save_changes')
    async def save_changes_handler(self, callback: CallbackQuery, args: list):
        """Сохранение изменений"""
        offer_id = self.scene.get_key(self.__page_name__, 'offer_id')
        sell_amount_per_trade = self.scene.get_key(self.__page_name__, 'sell_amount_per_trade')
        price = self.scene.get_key(self.__page_name__, 'price')
        barter_amount = self.scene.get_key(self.__page_name__, 'barter_amount')
        
        if not offer_id:
            await callback.answer("❌ Ошибка: ID предложения не найден", show_alert=True)
            return
        
        # Обновление предложения
        result = await update_exchange_offer(
            offer_id=offer_id,
            sell_amount_per_trade=sell_amount_per_trade,
            price=price,
            barter_amount=barter_amount
        )
        
        if isinstance(result, dict) and "error" in result:
            await callback.answer(f"❌ {result['error']}", show_alert=True)
            return
        
        # Очищаем данные страницы
        await self.scene.update_key(self.__page_name__, 'offer_id', None)
        await self.scene.update_key(self.__page_name__, 'sell_resource', None)
        await self.scene.update_key(self.__page_name__, 'sell_amount_per_trade', None)
        await self.scene.update_key(self.__page_name__, 'offer_type', None)
        await self.scene.update_key(self.__page_name__, 'price', None)
        await self.scene.update_key(self.__page_name__, 'barter_resource', None)
        await self.scene.update_key(self.__page_name__, 'barter_amount', None)
        await self.scene.update_key(self.__page_name__, 'error', None)
        await self.scene.update_key(self.__page_name__, 'input_state', None)
        
        # Очищаем кеш деталей предложения
        scene_data = self.scene.get_data('scene')
        cache_key = f'exchange_details_{offer_id}'
        if cache_key in scene_data:
            del scene_data[cache_key]
            await self.scene.set_data('scene', scene_data)
        
        await callback.answer("✅ Предложение обновлено!", show_alert=True)
        await self.scene.update_page('exchange-details-page')
