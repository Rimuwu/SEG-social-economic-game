from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources
from modules.ws_client import get_company
from aiogram.types import CallbackQuery
import json


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeCreateSetSell(OneUserPage):
    __for_blocked_pages__ = ["exchange-sellect-confirm", "exchange-main-page"]
    __page_name__ = "exchange-create-set-sell-page"
    
    
    async def data_preparate(self):
        """Инициализация данных"""
        if self.scene.get_key("exchange-create-set-sell-page", "page_number") is None:
            await self.scene.update_key("exchange-create-set-sell-page", "page_number", 0)
        
        # Инициализация состояния (select_resource или input_count)
        if self.scene.get_key("exchange-create-set-sell-page", "state") is None:
            await self.scene.update_key("exchange-create-set-sell-page", "state", "select_resource")
        
        # Инициализация ключа для ошибок
        if self.scene.get_key("exchange-create-set-sell-page", "error") is None:
            await self.scene.update_key("exchange-create-set-sell-page", "error", None)
    
    
    async def content_worker(self):
        """Генерация контента"""
        state = self.scene.get_key("exchange-create-set-sell-page", "state")
        error = self.scene.get_key("exchange-create-set-sell-page", "error")
        
        if state == "select_resource":
            text = "📦 Выбор ресурса для продажи\n\n"
            text += "Выберите ресурс, который хотите продать на бирже:"
        
        elif state == "input_count":
            selected_resource_id = self.scene.get_key("exchange-create-set-sell-page", "selected_resource_id")
            max_amount = self.scene.get_key("exchange-create-set-sell-page", "max_amount")
            
            resource = RESOURCES.resources.get(selected_resource_id)
            
            text = "🔢 Выбор количества\n\n"
            text += f"Ресурс: {resource.emoji} {resource.label}\n"
            text += f"Доступно на складе: {max_amount}\n\n"
            text += "💬 Введите количество ресурса для продажи или выберите одну из кнопок:"
        
        else:
            text = "❌ Неизвестное состояние"
        
        # Добавляем ошибку, если она есть
        if error:
            text += f"\n\n❌ Ошибка: {error}"
        
        return text
    
    
    async def buttons_worker(self):
        """Генерация кнопок с ресурсами и пагинацией"""
        state = self.scene.get_key("exchange-create-set-sell-page", "state")
        buttons = []
        
        # Если состояние ввода количества - показываем кнопки с долями
        if state == "input_count":
            max_amount = self.scene.get_key("exchange-create-set-sell-page", "max_amount")
            
            # Кнопки с долями от количества
            self.row_width = 4
            fractions = [
                ("1/4", max_amount // 4),
                ("2/4", max_amount // 2),
                ("3/4", (max_amount * 3) // 4),
                ("4/4", max_amount)
            ]
            
            for label, amount in fractions:
                if amount > 0:  # Показываем только если количество > 0
                    buttons.append({
                        "text": f"({amount})",
                        "callback_data": callback_generator(
                            self.scene.__scene_name__,
                            "set_amount",
                            amount
                        )
                    })
            
            # Кнопка отмены
            buttons.append({
                "text": "↩️ Назад к выбору ресурса",
                "callback_data": callback_generator(self.scene.__scene_name__, "cancel_input"),
                "ignore_row": True
            })
            
            return buttons
        
        # Если состояние выбора ресурса - показываем список ресурсов
        cur_page = self.scene.get_key("exchange-create-set-sell-page", "page_number")
        self.row_width = 1
        
        # Получаем ID компании
        company_id = self.scene.get_key("scene", "company_id")
        
        # Получаем данные компании, чтобы узнать, какие ресурсы есть на складе
        company_data = await get_company(id=company_id)
        
        if not isinstance(company_data, dict):
            # Если не удалось получить данные компании, показываем все ресурсы
            warehouse = {}
        else:
            warehouse = company_data.get("warehouses", {})
        
        # Получаем только те ресурсы, которые есть на складе
        all_resources = []
        for resource_id, resource in RESOURCES.resources.items():
            # Проверяем, есть ли ресурс на складе и его количество больше 0
            if resource_id in warehouse and warehouse[resource_id] > 0:
                all_resources.append({
                    "id": resource_id,
                    "name": resource.label,
                    "emoji": resource.emoji,
                    "level": resource.lvl,
                    "amount": warehouse[resource_id]
                })
        
        # Если на складе нет ресурсов
        if len(all_resources) == 0:
            buttons.append({
                "text": "❌ На складе нет ресурсов",
                "callback_data": callback_generator(self.scene.__scene_name__, "no_resources"),
                "ignore_row": True
            })
            buttons.append({
                "text": "↩️ Назад к созданию",
                "callback_data": callback_generator(self.scene.__scene_name__, "back_to_create"),
                "ignore_row": True
            })
            return buttons
        
        # Сортируем по уровню и имени
        all_resources.sort(key=lambda x: (x["level"], x["name"]))
        
        # Пагинация: 5 элементов на странице
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Нормализуем номер страницы
        cur_page = cur_page % total_pages
        await self.scene.update_key("exchange-create-set-sell-page", "page_number", cur_page)
        
        # Получаем элементы для текущей страницы
        start_idx = cur_page * items_per_page
        end_idx = start_idx + items_per_page
        page_resources = all_resources[start_idx:end_idx]
        
        # Создаем кнопки с ресурсами
        for resource in page_resources:
            buttons.append({
                "text": f"{resource['emoji']} {resource['name']} (x{resource['amount']})",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "select_resource",
                    resource["id"]
                ),
                "ignore_row": True
            })
        
        # Добавляем навигацию
        self.row_width = 3
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
        
        # Кнопка возврата
        buttons.append({
            "text": "↩️ Назад к созданию",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_to_create"),
            "ignore_row": True
        })
        
        return buttons
    
    @OneUserPage.on_callback("select_resource")
    async def select_resource(self, callback: CallbackQuery, args: list):
        """Выбор ресурса для продажи"""
        if not args or len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID ресурса")
            return
        
        resource_id = args[1]
        
        # Получаем количество ресурса на складе
        company_id = self.scene.get_key("scene", "company_id")
        company_data = await get_company(id=company_id)
        
        if not isinstance(company_data, dict):
            await callback.answer("❌ Ошибка: не удалось получить данные компании")
            return
        
        warehouses = company_data.get("warehouses", {})
        max_amount = warehouses.get(resource_id, 0)
        
        if max_amount <= 0:
            await callback.answer("❌ Этого ресурса нет на складе")
            return
        
        # Сохраняем выбранный ресурс и максимальное количество
        await self.scene.update_key("exchange-create-set-sell-page", "selected_resource_id", resource_id)
        await self.scene.update_key("exchange-create-set-sell-page", "max_amount", max_amount)
        
        # Переключаем состояние на ввод количества
        await self.scene.update_key("exchange-create-set-sell-page", "state", "input_count")
        
        # Обновляем страницу
        await self.scene.update_message()
        await callback.answer("✅ Ресурс выбран! Теперь выберите количество")
    
    @OneUserPage.on_callback("next_page")
    async def next_page(self, callback: CallbackQuery, args: list):
        """Следующая страница"""
        cur_page = self.scene.get_key("exchange-create-set-sell-page", "page_number")
        
        # Вычисляем общее количество страниц
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: после последней страницы идет первая
        new_page = (cur_page + 1) % total_pages
        await self.scene.update_key("exchange-create-set-sell-page", "page_number", new_page)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("back_page")
    async def back_page(self, callback: CallbackQuery, args: list):
        """Предыдущая страница"""
        cur_page = self.scene.get_key("exchange-create-set-sell-page", "page_number")
        
        # Вычисляем общее количество страниц
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: перед первой страницей идет последняя
        new_page = (cur_page - 1) % total_pages
        await self.scene.update_key("exchange-create-set-sell-page", "page_number", new_page)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("page_info")
    async def page_info(self, callback: CallbackQuery, args: list):
        """Информация о странице (заглушка)"""
        await callback.answer("Информация о странице")
    
    @OneUserPage.on_callback("back_to_create")
    async def back_to_create(self, callback: CallbackQuery, args: list):
        """Возврат на страницу создания предложения"""
        # Сбрасываем состояние
        await self.scene.update_key("exchange-create-set-sell-page", "state", "select_resource")
        
        await self.scene.update_page("exchange-create-page")
    
    @OneUserPage.on_callback("set_amount")
    async def set_amount(self, callback: CallbackQuery, args: list):
        """Обработка выбора количества через кнопку"""
        if not args or len(args) < 2:
            await callback.answer("❌ Ошибка: не указано количество")
            return
        
        amount = int(args[1])
        max_amount = self.scene.get_key("exchange-create-set-sell-page", "max_amount")
        
        # Проверяем корректность количества
        if amount <= 0 or amount > max_amount:
            await callback.answer(f"❌ Некорректное количество! Доступно: {max_amount}")
            return
        
        # Сохраняем данные
        resource_id = self.scene.get_key("exchange-create-set-sell-page", "selected_resource_id")
        
        # Получаем текущие настройки
        settings_data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(settings_data)
        
        # Обновляем настройки
        settings["sell_resource"] = resource_id
        settings["sell_amount_per_trade"] = amount
        
        # Сохраняем настройки
        await self.scene.update_key("exchange-create-page", "settings", json.dumps(settings))
        
        # Сбрасываем состояние
        await self.scene.update_key("exchange-create-set-sell-page", "state", "select_resource")
        
        # Возвращаемся на страницу создания предложения
        await self.scene.update_page("exchange-create-page")
        await callback.answer(f"✅ Выбрано: {amount} шт.")
    
    @OneUserPage.on_callback("cancel_input")
    async def cancel_input(self, callback: CallbackQuery, args: list):
        """Отмена ввода количества и возврат к выбору ресурса"""
        # Возвращаем состояние выбора ресурса
        await self.scene.update_key("exchange-create-set-sell-page", "state", "select_resource")
        
        # Обновляем страницу
        await self.scene.update_message()
        await callback.answer("↩️ Возврат к выбору ресурса")
    
    @OneUserPage.on_text("int")
    async def input_count(self, message, value):
        """Обработка ввода количества ресурса"""
        state = self.scene.get_key("exchange-create-set-sell-page", "state")
        
        # Сбрасываем ошибку при вводе
        await self.scene.update_key("exchange-create-set-sell-page", "error", None)
        
        # Обрабатываем ввод только в состоянии input_count
        if state != "input_count":
            await self.scene.update_key("exchange-create-set-sell-page", "error", "Сначала выберите ресурс!")
            await self.scene.update_message()
            return
        
        max_amount = self.scene.get_key("exchange-create-set-sell-page", "max_amount")
        
        # Проверяем корректность введенного количества
        if value <= 0:
            await self.scene.update_key("exchange-create-set-sell-page", "error", "Количество должно быть больше нуля!")
            await self.scene.update_message()
            return
        
        if value > max_amount:
            await self.scene.update_key("exchange-create-set-sell-page", "error", f"У вас нет столько ресурсов! Доступно: {max_amount} шт.")
            await self.scene.update_message()
            return
        
        # Сохраняем данные
        resource_id = self.scene.get_key("exchange-create-set-sell-page", "selected_resource_id")
        
        # Получаем текущие настройки
        settings_data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(settings_data)
        
        # Обновляем настройки
        settings["sell_resource"] = resource_id
        settings["sell_amount_per_trade"] = value
        
        # Сохраняем настройки
        await self.scene.update_key("exchange-create-page", "settings", json.dumps(settings))
        
        # Сбрасываем состояние
        await self.scene.update_key("exchange-create-set-sell-page", "state", "select_resource")
        
        # Возвращаемся на страницу создания предложения
        await self.scene.update_page("exchange-create-page")