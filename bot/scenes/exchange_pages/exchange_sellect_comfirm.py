from scenes.utils.oneuser_page import OneUserPage
from modules.ws_client import get_exchange, get_company, buy_exchange_offer
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator
from aiogram.types import CallbackQuery


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeSellectConfirm(OneUserPage):
    __for_blocked_pages__ = ["exchange-main-page", "exchange-create-page"]
    __page_name__ = "exchange-sellect-confirm-page"
    
    
    async def data_preparate(self):
        """Инициализация данных"""
        pass
    
    
    async def content_worker(self):
        """Генерация контента с деталями предложения"""
        exchange_id = self.scene.get_key("exchange-sellect-confirm-page", "selected_exchange")
        
        if not exchange_id:
            return "❌ Ошибка: предложение не выбрано"
        
        # Получаем детальную информацию о предложении
        exchange = await get_exchange(id=exchange_id)
        
        if isinstance(exchange, str):
            return f"❌ Ошибка при получении предложения: {exchange}"
        
        if not exchange:
            return "❌ Предложение не найдено"
        
        # Получаем информацию о компании-продавце
        seller_company_id = exchange.get('company_id')
        seller_company = await get_company(id=seller_company_id)
        seller_name = "Неизвестная компания"
        if isinstance(seller_company, dict):
            seller_name = seller_company.get('name', seller_name)
        
        # Формируем детальное описание
        text = "📋 *Детали предложения*\n\n"
        
        # Информация о продавце
        text += f"🏢 *Продавец:* {seller_name}\n\n"
        
        # Информация о товаре
        sell_res = RESOURCES.get_resource(exchange.get('sell_resource', ''))
        if sell_res:
            sell_amount = exchange.get('sell_amount_per_trade', 0)
            total_stock = exchange.get('total_stock', 0)
            
            text += f"📦 *Товар:* {sell_res.emoji} {sell_res.label}\n"
            text += f"   За одну сделку: {sell_amount} ед.\n"
            text += f"   Всего в наличии: {total_stock} ед.\n"
            text += f"   Доступно сделок: {total_stock // sell_amount if sell_amount > 0 else 0}\n\n"
        
        # Условия сделки
        offer_type = exchange.get('offer_type', 'money')
        
        if offer_type == 'money':
            price = exchange.get('price', 0)
            text += f"💰 *Цена за сделку:* {price} монет\n"
            text += f"   За единицу: {price / sell_amount:.2f} монет\n\n"
        elif offer_type == 'barter':
            barter_res = RESOURCES.get_resource(exchange.get('barter_resource', ''))
            barter_amount = exchange.get('barter_amount_per_trade', 0)
            if barter_res:
                text += f"⇄ *Бартер:* {barter_res.emoji} {barter_res.label}\n"
                text += f"   За одну сделку: {barter_amount} ед.\n\n"
        
        return text
    
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        data = self.scene.get_data("scene")
        company_id = data.get("company_id")
        exchange_id = self.scene.get_key("exchange-sellect-confirm-page", "selected_exchange")
        
        buttons = []
        self.row_width = 2
        
        # Получаем информацию о предложении
        exchange = await get_exchange(id=exchange_id)
        
        if isinstance(exchange, dict):
            seller_company_id = exchange.get('company_id')
            
            # Если это не наше предложение - показываем кнопку покупки
            if seller_company_id != company_id:
                buttons.append({
                    "text": "💰 Купить",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "buy_exchange",
                        exchange_id
                    ),
                    "ignore_row": True
                })
            else:
                # Если это наше предложение - показываем кнопку удаления
                buttons.append({
                    "text": "🗑️ Удалить предложение",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__,
                        "delete_exchange",
                        exchange_id
                    ),
                    "ignore_row": True
                })
        
        # Кнопка возврата
        buttons.append({
            "text": "↩️ Назад к списку",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_to_list"),
            "ignore_row": True
        })
        
        return buttons
    
    @OneUserPage.on_callback("buy_exchange")
    async def buy_exchange(self, callback: CallbackQuery, args: list):
        """Покупка предложения"""
        exchange_id = args[1]
        data = self.scene.get_data("scene")
        company_id = data.get("company_id")
        
        # Совершаем покупку
        result = await buy_exchange_offer(
            exchange_id=exchange_id,
            buyer_company_id=company_id
        )
        
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
        else:
            await callback.answer("✅ Покупка совершена!", show_alert=True)
            await self.scene.update_page("exchange-main-page")
    
    @OneUserPage.on_callback("delete_exchange")
    async def delete_exchange(self, callback: CallbackQuery, args: list):
        """Удаление своего предложения"""
        # TODO: Реализовать удаление предложения через API
        await callback.answer("⚠️ Функция удаления в разработке", show_alert=True)
    
    @OneUserPage.on_callback("back_to_list")
    async def back_to_list(self, callback: CallbackQuery, args: list):
        """Возврат к списку предложений"""
        await self.scene.update_page("exchange-main-page")