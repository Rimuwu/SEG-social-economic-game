from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from modules.ws_client import create_exchange_offer, get_company
from global_modules.load_config import ALL_CONFIGS, Resources
from aiogram.types import CallbackQuery
import json


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeCreate(OneUserPage):
    __for_blocked_pages__ = ["exchange-sellect-confirm", "exchange-main-page"]
    __page_name__ = "exchange-create-page"
    
    async def data_preparate(self):
        """Инициализация данных для создания предложения"""
        if self.scene.get_key("exchange-create-page", "settings") is None:
            await self.scene.update_key("exchange-create-page", "settings", json.dumps({
                "sell_resource": None,
                "sell_amount_per_trade": None,
                "count_offers": None,
                "offer_type": "money",
                "price": None,
                "barter_resource": None,
                "barter_amount": None
            }))
        
        # Инициализация ключа для ошибок
        if self.scene.get_key("exchange-create-page", "error") is None:
            await self.scene.update_key("exchange-create-page", "error", None)
    
    async def content_worker(self):
        """Генерация контента страницы"""
        data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(data)
        error = self.scene.get_key("exchange-create-page", "error")
        
        sell_resource = "Не выбран"
        barter_resource = "Не выбрано"
        
        if settings["sell_resource"] is not None:
            res1 = RESOURCES.get_resource(settings["sell_resource"])
            sell_resource = f"{res1.emoji} {res1.label}"
        
        if settings["barter_resource"] is not None:
            res2 = RESOURCES.get_resource(settings["barter_resource"])
            barter_resource = f"{res2.emoji} {res2.label}"
        
        # Формируем текст в зависимости от типа предложения
        text = "➕ *Создание предложения*\n\n"
        text += f"📦 Товар: {sell_resource}\n"
        text += f"   Количество за сделку: {settings['sell_amount_per_trade'] or 'Не установлено'}\n"
        text += f"   Количество сделок: {settings['count_offers'] or 'Не установлено'}\n\n"
        
        text += f"💼 Тип: {'💰 За деньги' if settings['offer_type'] == 'money' else '⇄ Бартер'}\n"
        
        if settings["offer_type"] == "money":
            text += f"   Цена за сделку: {settings['price'] or 'Не установлено'}\n"
        else:
            text += f"   За ресурс: {barter_resource}\n"
            text += f"   Количество за сделку: {settings['barter_amount'] or 'Не установлено'}\n"
        
        # Добавляем ошибку, если она есть
        if error:
            text += f"\n\n❌ Ошибка: {error}"
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(data)
        
        sell_resource = "Не выбран"
        barter_resource = "Не выбрано"
        sell_amount_per_trade = settings["sell_amount_per_trade"] if settings["sell_amount_per_trade"] else "N"
        price = settings["price"] if settings["price"] else "N"
        
        if settings["sell_resource"] is not None:
            res1 = RESOURCES.get_resource(settings["sell_resource"])
            sell_resource = f"{res1.emoji} {res1.label}"
        
        if settings["barter_resource"] is not None:
            res2 = RESOURCES.get_resource(settings["barter_resource"])
            barter_resource = f"{res2.emoji} {res2.label}"
        
        self.row_width = 2
        buttons = []
        
        # Кнопка выбора ресурса для продажи
        buttons.append({
            "text": f"📦 Товар: {sell_resource} x{sell_amount_per_trade}",
            "callback_data": callback_generator(self.scene.__scene_name__, "set_sell_resource"),
            "ignore_row": True
        })
        
        # Кнопка выбора типа предложения
        buttons.append({
            "text": f"{'💰 За монеты' if settings['offer_type'] == 'money' else '⇄ Бартер'}",
            "callback_data": callback_generator(self.scene.__scene_name__, "change_offer_type")
        })
        
        # Кнопка количества сделок
        buttons.append({
            "text": f"📊 Кол-во сделок: {settings['count_offers'] if settings['count_offers'] else 'N'}",
            "callback_data": callback_generator(self.scene.__scene_name__, "set_count_offers"),
        })
        
        # Кнопка настройки условий (цена или бартер)
        if settings["offer_type"] == "money":
            buttons.append({
                "text": f"💰 Цена за сделку: {price}",
                "callback_data": callback_generator(self.scene.__scene_name__, "change_price"),
                "ignore_row": True
            })
        else:
            buttons.append({
                "text": f"⇄ Бартер: {barter_resource} x{settings['barter_amount'] if settings['barter_amount'] else 'N'}",
                "callback_data": callback_generator(self.scene.__scene_name__, "set_barter_resource"),
                "ignore_row": True
            })
        
        # Кнопки действий
        buttons.append({
            "text": "✅ Создать",
            "callback_data": callback_generator(self.scene.__scene_name__, "create_exchange_offer")
        })
        buttons.append({
            "text": "🔄 Очистить",
            "callback_data": callback_generator(self.scene.__scene_name__, "clear_exchange_offer")
        })
        buttons.append({
            "text": "↩️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "to_page", "exchange-main-page"),
            "ignore_row": True
        })
        
        return buttons


    @OneUserPage.on_text('int')
    async def input_count(self, message, value):
        state = self.scene.get_key("exchange-create-set-barter-page", "state")
        
        # Сбрасываем ошибку при вводе
        await self.scene.update_key("exchange-create-page", "error", None)
        
        # Обработка ввода количества сделок
        if state == "input_count_offers":
            settings_data = self.scene.get_key("exchange-create-page", "settings")
            settings = json.loads(settings_data)
            
            # Проверяем корректность количества сделок
            if value <= 0:
                await self.scene.update_key("exchange-create-page", "error", "Количество сделок должно быть больше нуля!")
                await self.scene.update_key("exchange-create-set-barter-page", "state", None)
                await self.scene.update_message()
                return
            
            sell_count = settings.get("sell_amount_per_trade")
            total_needed = sell_count * value
            
            # Получаем склад компании
            company_id = self.scene.get_key("scene", "company_id")
            company_data = await get_company(id=company_id)
            
            if not isinstance(company_data, dict):
                await self.scene.update_key("exchange-create-page", "error", "Не удалось получить данные компании")
                await self.scene.update_key("exchange-create-set-barter-page", "state", None)
                await self.scene.update_message()
                return
            
            warehouses = company_data.get("warehouses", {})
            available = warehouses.get(settings["sell_resource"], 0)
            
            # Проверяем, достаточно ли товара на складе
            if total_needed > available:
                await self.scene.update_key(
                    "exchange-create-page", 
                    "error", 
                    f"Недостаточно товара на складе! Требуется: {total_needed} ({sell_count} x {value}), Доступно: {available}"
                )
                await self.scene.update_key("exchange-create-set-barter-page", "state", None)
                await self.scene.update_message()
                return
            
            # Сохраняем количество сделок
            settings["count_offers"] = value
            await self.scene.update_key("exchange-create-page", "settings", json.dumps(settings))
            await self.scene.update_key("exchange-create-set-barter-page", "state", None)
            await self.scene.update_message()
        
        # Обработка ввода цены
        elif state == "input_price":
            settings_data = self.scene.get_key("exchange-create-page", "settings")
            settings = json.loads(settings_data)
            
            # Проверяем корректность цены
            if value <= 0:
                await self.scene.update_key("exchange-create-page", "error", "Цена должна быть больше нуля!")
                await self.scene.update_key("exchange-create-set-barter-page", "state", None)
                await self.scene.update_message()
                return
            
            # Сохраняем цену
            settings["price"] = value
            await self.scene.update_key("exchange-create-page", "settings", json.dumps(settings))
            await self.scene.update_key("exchange-create-set-barter-page", "state", None)
            await self.scene.update_message()


    @OneUserPage.on_callback("set_sell_resource")
    async def set_sell_resource(self, callback: CallbackQuery, args: list):
        """Открыть страницу выбора ресурса для продажи"""
        await self.scene.update_page("exchange-create-set-sell-page")
    
    @OneUserPage.on_callback("change_offer_type")
    async def change_offer_type(self, callback: CallbackQuery, args: list):
        """Переключить тип предложения"""
        data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(data)
        
        if settings["offer_type"] == "money":
            settings["offer_type"] = "barter"
            settings["price"] = None
        else:
            settings["offer_type"] = "money"
            settings["barter_resource"] = None
            settings["barter_amount"] = None
        
        await self.scene.update_key("exchange-create-page", "settings", json.dumps(settings))
        await self.scene.update_message()
    
    @OneUserPage.on_callback("set_count_offers")
    async def set_count_offers(self, callback: CallbackQuery, args: list):
        # Сбрасываем ошибку
        await self.scene.update_key("exchange-create-page", "error", None)
        
        settings_data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(settings_data)
        
        # Проверяем, что выбран ресурс для продажи и количество за сделку
        if not settings.get("sell_resource") or not settings.get("sell_amount_per_trade"):
            await self.scene.update_key("exchange-create-page", "error", "Сначала выберите ресурс для продажи и количество за сделку!")
            await self.scene.update_message()
            await callback.answer()
            return
        
        await self.scene.update_key("exchange-create-set-barter-page", "state", "input_count_offers")
        await callback.answer("Введите количество сделок в чат", show_alert=True)
    
    @OneUserPage.on_callback("change_price")
    async def change_price(self, callback: CallbackQuery, args: list):
        # Сбрасываем ошибку
        await self.scene.update_key("exchange-create-page", "error", None)
        
        settings_data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(settings_data)
        
        # Проверяем, что выбран ресурс для продажи
        if not settings.get("sell_resource"):
            await self.scene.update_key("exchange-create-page", "error", "Сначала выберите ресурс для продажи!")
            await self.scene.update_message()
            await callback.answer()
            return
        
        await self.scene.update_key("exchange-create-set-barter-page", "state", "input_price")
        await callback.answer("Введите цену в чат", show_alert=True)
    
    @OneUserPage.on_callback("set_barter_resource")
    async def set_barter_resource(self, callback: CallbackQuery, args: list):
        """Открыть страницу выбора ресурса для бартера"""
        await self.scene.update_page("exchange-create-set-barter-page")
    
    @OneUserPage.on_callback("create_exchange_offer")
    async def create_exchange_offer_handler(self, callback: CallbackQuery, args: list):
        """Создать предложение"""
        data = self.scene.get_data("scene")
        company_id = data.get("company_id")
        session_id = data.get("session")
        
        settings_data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(settings_data)
        
        # Проверяем заполненность полей
        if not all([
            settings["sell_resource"],
            settings["sell_amount_per_trade"],
            settings["count_offers"]
        ]):
            await callback.answer("❌ Заполните все обязательные поля", show_alert=True)
            return
        
        if settings["offer_type"] == "money" and not settings["price"]:
            await callback.answer("❌ Укажите цену", show_alert=True)
            return
        
        if settings["offer_type"] == "barter" and not all([
            settings["barter_resource"],
            settings["barter_amount"]
        ]):
            await callback.answer("❌ Укажите условия бартера", show_alert=True)
            return
        
        # Создаем предложение
        result = await create_exchange_offer(
            company_id=company_id,
            session_id=session_id,
            sell_resource=settings["sell_resource"],
            sell_amount_per_trade=settings["sell_amount_per_trade"],
            count_offers=settings["count_offers"],
            offer_type=settings["offer_type"],
            price=settings.get("price"),
            barter_resource=settings.get("barter_resource"),
            barter_amount=settings.get("barter_amount")
        )
        
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
        else:
            await callback.answer("✅ Предложение создано!", show_alert=True)
            # Очищаем данные
            await self.scene.update_key("exchange-create-page", "settings", None)
            await self.scene.update_page("exchange-main-page")
    
    @OneUserPage.on_callback("clear_exchange_offer")
    async def clear_exchange_offer(self, callback: CallbackQuery, args: list):
        """Очистить форму"""
        await self.scene.update_key("exchange-create-page", "settings", None)
        await self.data_preparate()
        await self.scene.update_message()
    
    @OneUserPage.on_callback("to_page")
    async def to_page(self, callback: CallbackQuery, args: list):
        """Переход на другую страницу"""
        page_name = args[1]
        await self.scene.update_page(page_name)