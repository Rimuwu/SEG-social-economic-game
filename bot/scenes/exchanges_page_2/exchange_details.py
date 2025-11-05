from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery
from modules.ws_client import get_exchange, get_company, buy_exchange_offer
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeDetails(OneUserPage):
    """Страница детального просмотра предложения"""
    
    __page_name__ = "exchange-details-page"
    
    async def content_worker(self):
        """Детальная информация о предложении"""
        scene_data = self.scene.get_data('scene')
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
        
        # Получаем информацию о товаре
        sell_res = RESOURCES.get_resource(exchange.get('sell_resource', ''))
        if not sell_res:
            return "❌ Ошибка: ресурс не найден"
        
        sell_amount = exchange.get('sell_amount_per_trade', 0)
        total_stock = exchange.get('total_stock', 0)
        
        # Количество доступных сделок
        available_trades = total_stock // sell_amount if sell_amount > 0 else 0
        
        # Условия сделки
        offer_type = exchange.get('offer_type', 'money')
        
        if offer_type == 'money':
            price = exchange.get('price', 0)
            offer_conditions = f"💰 *Тип:* За монеты\n💰 *Цена за сделку:* {price:,}".replace(",", " ")
        elif offer_type == 'barter':
            barter_res = RESOURCES.get_resource(exchange.get('barter_resource', ''))
            barter_amount = exchange.get('barter_amount', 0)
            if barter_res:
                offer_conditions = f"⇄ *Тип:* Бартер\n⇄ *Требуется:* {barter_res.emoji} {barter_res.label} x{barter_amount}"
            else:
                offer_conditions = "⇄ *Тип:* Бартер"
        else:
            offer_conditions = ""
        
        # Информация о времени создания
        created_at = exchange.get('created_at', 0)
        
        return self.content.format(
            seller_name=seller_name,
            sell_emoji=sell_res.emoji,
            sell_name=sell_res.label,
            sell_amount=sell_amount,
            total_stock=total_stock,
            available_trades=available_trades,
            offer_conditions=offer_conditions,
            created_at=created_at
        )
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        exchange_id = scene_data.get('selected_exchange_id')
        
        buttons = []
        
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
        
        return buttons
    
    @OneUserPage.on_callback('buy_exchange')
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
        scene_data['selected_exchange_id'] = None
        scene_data['success_message'] = 'Сделка успешно совершена!'
        
        # Очищаем кеш
        cache_key = f'exchange_details_{exchange_id}'
        if cache_key in scene_data:
            del scene_data[cache_key]
        
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('exchange-main-page')
        await callback.answer("✅ Сделка совершена!", show_alert=True)
    
    @OneUserPage.on_callback('own_offer')
    async def own_offer_handler(self, callback: CallbackQuery, args: list):
        """Обработка нажатия на своё предложение"""
        await callback.answer(
            "ℹ️ Это ваше предложение. Вы не можете купить его.",
            show_alert=False
        )
    
    @OneUserPage.on_callback('back_to_list')
    async def back_to_list_handler(self, callback: CallbackQuery, args: list):
        """Возврат к списку предложений"""
        scene_data = self.scene.get_data('scene')
        
        # Очищаем кеш деталей предложения
        exchange_id = scene_data.get('selected_exchange_id')
        if exchange_id:
            cache_key = f'exchange_details_{exchange_id}'
            if cache_key in scene_data:
                del scene_data[cache_key]
        
        scene_data['selected_exchange_id'] = None
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('exchange-main-page')
        await callback.answer()
