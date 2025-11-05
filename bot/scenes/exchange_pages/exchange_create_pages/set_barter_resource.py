from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources
from aiogram.types import CallbackQuery
import json


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ExchangeCreateSetBarter(OneUserPage):
    __for_blocked_pages__ = ["exchange-sellect-confirm", "exchange-main-page"]
    __page_name__ = "exchange-create-set-barter-page"
    
    
    async def data_preparate(self):
        """Инициализация данных"""
        if self.scene.get_key("exchange-create-set-barter-page", "page_number") is None:
            await self.scene.update_key("exchange-create-set-barter-page", "page_number", 0)
        if self.scene.get_key("exchange-create-set-barter-page", "count") is None:
            await self.scene.update_key("exchange-create-set-barter-page", "count", 0)
        if self.scene.get_key("exchange-create-set-barter-page", "state") is None:
            await self.scene.update_key("exchange-create-set-barter-page", "state", "select_resource")
        
        # Инициализация ключа для ошибок
        if self.scene.get_key("exchange-create-set-barter-page", "error") is None:
            await self.scene.update_key("exchange-create-set-barter-page", "error", None)
    
    async def content_worker(self):
        """Генерация контента"""
        state = self.scene.get_key("exchange-create-set-barter-page", "state")
        error = self.scene.get_key("exchange-create-set-barter-page", "error")
        
        if state == "select_resource":
            text = "⇄ Выбор ресурса для бартера\n\n"
            text += "Выберите ресурс, который хотите получить в обмен:"
        
        elif state == "input_count":
            selected_resource_id = self.scene.get_key("exchange-create-set-barter-page", "selected_resource_id")
            
            resource = RESOURCES.resources.get(selected_resource_id)
            
            text = "🔢 Выбор количества\n\n"
            text += f"Ресурс для получения: {resource.emoji} {resource.label}\n\n"
            text += "💬 Введите количество ресурса, которое хотите получить в обмен, или выберите одну из кнопок:"
        
        else:
            text = "❌ Неизвестное состояние"
        
        # Добавляем ошибку, если она есть
        if error:
            text += f"\n\n❌ Ошибка: {error}"
        
        return text
    
    
    async def buttons_worker(self):
        state = self.scene.get_key("exchange-create-set-barter-page", "state")
        buttons = []
        if state == "select_resource":
            """Генерация кнопок с ресурсами и пагинацией"""
            cur_page = self.scene.get_key("exchange-create-set-barter-page", "page_number")
            self.row_width = 1

            # Получаем все ресурсы и сортируем их
            all_resources = []
            for resource_id, resource in RESOURCES.resources.items():
                all_resources.append({
                    "id": resource_id,
                    "name": resource.label,
                    "emoji": resource.emoji,
                    "level": resource.lvl
                })

            # Сортируем по уровню и имени
            all_resources.sort(key=lambda x: (x["level"], x["name"]))

            # Пагинация: 5 элементов на странице
            items_per_page = 5
            total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)

            # Нормализуем номер страницы
            cur_page = cur_page % total_pages
            await self.scene.update_key("exchange-create-set-barter-page", "page_number", cur_page)

            # Получаем элементы для текущей страницы
            start_idx = cur_page * items_per_page
            end_idx = start_idx + items_per_page
            page_resources = all_resources[start_idx:end_idx]

            # Создаем кнопки с ресурсами
            for resource in page_resources:
                buttons.append({
                    "text": f"{resource['emoji']} {resource['name']}",
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
    
    
    @OneUserPage.on_text('int')
    async def input_count(self, message, value):
        """Ввод количества ресурса"""
        state = self.scene.get_key("exchange-create-set-barter-page", "state")
        
        # Сбрасываем ошибку при вводе
        await self.scene.update_key("exchange-create-set-barter-page", "error", None)
        
        # Обрабатываем ввод только в состоянии input_count
        if state != "input_count":
            await self.scene.update_key("exchange-create-set-barter-page", "error", "Сначала выберите ресурс!")
            await self.scene.update_message()
            return
        
        # Проверяем корректность введенного количества
        if value <= 0:
            await self.scene.update_key("exchange-create-set-barter-page", "error", "Количество должно быть больше нуля!")
            await self.scene.update_message()
            return
        
        # Сохраняем данные
        resource_id = self.scene.get_key("exchange-create-set-barter-page", "selected_resource_id")
        
        # Получаем текущие настройки
        settings_data = self.scene.get_key("exchange-create-page", "settings")
        settings = json.loads(settings_data)
        
        # Обновляем настройки
        settings["barter_resource"] = resource_id
        settings["barter_amount"] = value
        
        # Сохраняем настройки
        await self.scene.update_key("exchange-create-page", "settings", json.dumps(settings))
        
        # Сбрасываем состояние
        await self.scene.update_key("exchange-create-set-barter-page", "state", "select_resource")
        
        # Возвращаемся на страницу создания предложения
        await self.scene.update_page("exchange-create-page")
            
    
    
    @OneUserPage.on_callback("select_resource")
    async def select_resource(self, callback: CallbackQuery, args: list):
        """Выбор ресурса для бартера"""
        if not args or len(args) < 2:
            await callback.answer("❌ Ошибка: не указан ID ресурса")
            return
        
        resource_id = args[1]
        
        # Сохраняем выбранный ресурс
        await self.scene.update_key("exchange-create-set-barter-page", "selected_resource_id", resource_id)
        
        # Переключаем состояние на ввод количества
        await self.scene.update_key("exchange-create-set-barter-page", "state", "input_count")
        
        # Обновляем страницу
        await self.scene.update_message()
        await callback.answer("✅ Ресурс выбран! Теперь выберите количество")
    
    @OneUserPage.on_callback("next_page")
    async def next_page(self, callback: CallbackQuery, args: list):
        """Следующая страница"""
        cur_page = self.scene.get_key("exchange-create-set-barter-page", "page_number")
        
        # Вычисляем общее количество страниц
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: после последней страницы идет первая
        new_page = (cur_page + 1) % total_pages
        await self.scene.update_key("exchange-create-set-barter-page", "page_number", new_page)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("back_page")
    async def back_page(self, callback: CallbackQuery, args: list):
        """Предыдущая страница"""
        cur_page = self.scene.get_key("exchange-create-set-barter-page", "page_number")
        
        # Вычисляем общее количество страниц
        all_resources = list(RESOURCES.resources.items())
        items_per_page = 5
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: перед первой страницей идет последняя
        new_page = (cur_page - 1) % total_pages
        await self.scene.update_key("exchange-create-set-barter-page", "page_number", new_page)
        await self.scene.update_message()
    
    @OneUserPage.on_callback("page_info")
    async def page_info(self, callback: CallbackQuery, args: list):
        """Информация о странице (заглушка)"""
        await callback.answer("Информация о странице")
    
    @OneUserPage.on_callback("back_to_create")
    async def back_to_create(self, callback: CallbackQuery, args: list):
        """Возврат на страницу создания предложения"""
        # Сбрасываем состояние
        await self.scene.update_key("exchange-create-set-barter-page", "state", "select_resource")
        
        await self.scene.update_page("exchange-create-page")
    
   
    
    @OneUserPage.on_callback("cancel_input")
    async def cancel_input(self, callback: CallbackQuery, args: list):
        """Отмена ввода количества и возврат к выбору ресурса"""
        # Возвращаем состояние выбора ресурса
        await self.scene.update_key("exchange-create-set-barter-page", "state", "select_resource")
        
        # Обновляем страницу
        await self.scene.update_message()
        await callback.answer("↩️ Возврат к выбору ресурса")