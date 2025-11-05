from typing import List, Optional

from oms import Page
from aiogram.types import Message, CallbackQuery
from modules.ws_client import get_cities, get_city, get_company, sell_to_city
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources
from modules.utils import xy_into_cell
from .oneuser_page import OneUserPage


RESOURCES: Resources = ALL_CONFIGS["resources"]


class City(OneUserPage):
    __page_name__ = "city-page"

    async def data_preparate(self):
        if self.scene.get_key("city-page", "stage") is None:
            await self.scene.update_key("city-page", "stage", "main")

        if self.scene.get_key("city-page", "city_id") is None:
            await self.scene.update_key("city-page", "city_id", None)

        if self.scene.get_key("city-page", "page_cities") is None:
            await self.scene.update_key("city-page", "page_cities", 0)

        if self.scene.get_key("city-page", "page_products") is None:
            await self.scene.update_key("city-page", "page_products", 0)

        if self.scene.get_key("city-page", "current_product") is None:
            await self.scene.update_key("city-page", "current_product", None)

        if self.scene.get_key("city-page", "status_message") is None:
            await self.scene.update_key("city-page", "status_message", None)

        if self.scene.get_key("city-page", "status_level") is None:
            await self.scene.update_key("city-page", "status_level", "info")

    async def content_worker(self):
        scene_data = self.scene.get_data("scene")
        page_data = self.scene.get_data("city-page")
        stage = page_data.get("stage", "main")
        lines: List[str] = []

        if stage == "main":
            lines.append("🏙 **Города**")
            lines.append("")
            lines.append("🗺 Нажмите на город (🏢), чтобы посмотреть востребованные товары.")
        elif stage == "city_info":
            city_text = await self._build_city_info_text(scene_data, page_data)
            lines.append(city_text)
        elif stage == "product_info":
            product_text = await self._build_product_info_text(scene_data, page_data)
            lines.append(product_text)
        elif stage == "sell_product":
            sell_text = await self._build_sell_product_text(scene_data, page_data)
            lines.append(sell_text)
        else:
            lines.append("❌ Неизвестный этап страницы")

        status_message = page_data.get("status_message")
        status_level = page_data.get("status_level", "info")
        if status_message:
            prefix = "✅" if status_level == "success" else "❌" if status_level == "error" else "ℹ️"
            lines.append("")
            lines.append(f"{prefix} {status_message}")

        return "\n".join(lines)

    async def buttons_worker(self):
        scene_data = self.scene.get_data("scene")
        page_data = self.scene.get_data("city-page")
        stage = page_data.get("stage", "main")
        session_id = scene_data.get("session")
        buttons: List[dict] = []

        if stage == "main":
            self.row_width = 7
            
            # Получаем список городов
            cities_data = await get_cities(session_id=session_id)
            cities_map = {}  # {(x, y): city}
            
            if cities_data and isinstance(cities_data, list):
                for city in cities_data:
                    # cell_position в формате "x.y" (например, "1.5")
                    cell_position = city.get("cell_position", "")
                    if cell_position and "." in cell_position:
                        try:
                            x, y = cell_position.split(".")
                            x, y = int(x), int(y)
                            cities_map[(x, y)] = city
                        except (ValueError, AttributeError):
                            continue
            
            # Генерируем карту 7x7
            for x in range(7):
                for y in range(7):
                    cell_position = xy_into_cell(x, y)
                    
                    # Проверяем, есть ли город в этой позиции
                    if (x, y) in cities_map:
                        city = cities_map[(x, y)]
                        buttons.append({
                            'text': '🏢',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__, 
                                'city_select',
                                city.get('id', 0)
                            )
                        })
                    # Центральная клетка - банк
                    elif cell_position == "D4":
                        buttons.append({
                            'text': '🏦',
                            'callback_data': callback_generator(self.scene.__scene_name__, "noop")
                        })
                    # Остальные клетки - показываем координаты
                    else:
                        buttons.append({
                            'text': cell_position,
                            'callback_data': callback_generator(self.scene.__scene_name__, "noop")
                        })
            
            # Кнопка возврата на главную
            buttons.append({
                "text": "⬅️ На главную",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_exit"),
                "next_line": True
            })

        elif stage == "city_info":
            self.row_width = 3
            city_id = page_data.get("city_id")
            city_data = await self._load_city(city_id, session_id)
            demands = city_data.get("demands", {}) if city_data else {}
            demand_keys = list(demands.keys())
            resource_chunks = self._chunk_list(demand_keys, 4)

            if not demand_keys:
                buttons.append({
                    "text": "🔄 Обновить",
                    "callback_data": callback_generator(self.scene.__scene_name__, "city_refresh")
                })
            else:
                current_page = self._clamp_page(page_data.get("page_products", 0), len(resource_chunks))
                await self.scene.update_key("city-page", "page_products", current_page)
                for resource_key in resource_chunks[current_page]:
                    resource = RESOURCES.get_resource(resource_key)
                    demand = demands.get(resource_key, {})
                    amount = demand.get("amount", 0)
                    label = resource.label if resource else resource_key
                    emoji = resource.emoji if resource else "📦"
                    buttons.append({
                        "text": f"{emoji} {label} ({amount})",
                        "callback_data": callback_generator(self.scene.__scene_name__, "city_view_product", resource_key),
                        "ignore_row": True
                    })

                if len(resource_chunks) > 1:
                    buttons.append({
                        "text": "◀️",
                        "callback_data": callback_generator(self.scene.__scene_name__, "city_products_prev")
                    })
                    buttons.append({
                        "text": f"{current_page + 1}/{len(resource_chunks)}",
                        "callback_data": callback_generator(self.scene.__scene_name__, "noop")
                    })
                    buttons.append({
                        "text": "▶️",
                        "callback_data": callback_generator(self.scene.__scene_name__, "city_products_next")
                    })

            buttons.append({
                "text": "⬅️ К списку городов",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_back_to_list"),
                "next_line": True
            })

        elif stage == "product_info":
            self.row_width = 1
            can_sell = await self._company_has_product(scene_data, page_data)
            if can_sell:
                buttons.append({
                    "text": "💰 Продать",
                    "callback_data": callback_generator(self.scene.__scene_name__, "city_start_sell")
                })
            buttons.append({
                "text": "⬅️ Назад",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_product_back")
            })

        elif stage == "sell_product":
            self.row_width = 1
            buttons.append({
                "text": "⬅️ Назад",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_cancel_sell")
            })

        return buttons

    @Page.on_callback('noop')
    async def noop_callback(self, callback: CallbackQuery, args: list):
        await callback.answer()

    @Page.on_callback('city_refresh')
    async def refresh_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('city_exit')
    async def exit_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_page('main-page')
        await callback.answer()

    @Page.on_callback('city_select')
    async def select_city_callback(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        try:
            city_id = int(args[1])
        except ValueError:
            await callback.answer("❌ Некорректный идентификатор города", show_alert=True)
            return

        await self.scene.update_key("city-page", "city_id", city_id)
        await self.scene.update_key("city-page", "stage", "city_info")
        await self.scene.update_key("city-page", "page_products", 0)
        await self.scene.update_key("city-page", "current_product", None)
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('city_back_to_list')
    async def back_to_list_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("city-page", "stage", "main")
        await self.scene.update_key("city-page", "city_id", None)
        await self.scene.update_key("city-page", "current_product", None)
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('city_page_prev')
    async def city_page_prev_callback(self, callback: CallbackQuery, args: list):
        await self._change_city_page(-1)
        await callback.answer()

    @Page.on_callback('city_page_next')
    async def city_page_next_callback(self, callback: CallbackQuery, args: list):
        await self._change_city_page(1)
        await callback.answer()

    @Page.on_callback('city_products_prev')
    async def city_products_prev_callback(self, callback: CallbackQuery, args: list):
        await self._change_product_page(-1)
        await callback.answer()

    @Page.on_callback('city_products_next')
    async def city_products_next_callback(self, callback: CallbackQuery, args: list):
        await self._change_product_page(1)
        await callback.answer()

    @Page.on_callback('city_view_product')
    async def view_product_callback(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Неизвестный товар", show_alert=True)
            return

        resource_key = args[1]
        await self.scene.update_key("city-page", "current_product", resource_key)
        await self.scene.update_key("city-page", "stage", "product_info")
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('city_product_back')
    async def product_back_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("city-page", "stage", "city_info")
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('city_start_sell')
    async def start_sell_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("city-page", "stage", "sell_product")
        await self._set_status()
        await self.scene.update_message()
        await callback.answer("Введите количество товара числом")

    @Page.on_callback('city_cancel_sell')
    async def cancel_sell_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("city-page", "stage", "product_info")
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_text('int')
    async def handle_numeric_input(self, message: Message, value: int):
        page_data = self.scene.get_data("city-page")
        if page_data.get("stage") != "sell_product":
            return

        if value <= 0:
            await self._set_status("Количество должно быть больше нуля", level="error")
            await self.scene.update_message()
            return

        _ = message  # OMS требует параметр message; логика использует статусные сообщения

        scene_data = self.scene.get_data("scene")
        session_id = scene_data.get("session")
        company_id = scene_data.get("company_id")
        city_id = page_data.get("city_id")
        resource_key = page_data.get("current_product")

        city_data = await self._load_city(city_id, session_id)
        demand = city_data.get("demands", {}).get(resource_key, {}) if city_data else {}
        demand_amount = demand.get("amount", 0)

        company_data = await get_company(id=company_id)
        if company_data is None or isinstance(company_data, str):
            await self._set_status("Не удалось получить данные компании", level="error")
            await self.scene.update_message()
            return

        available = self._get_company_stock(company_data, resource_key)

        if available <= 0:
            await self._set_status("У компании нет такого товара", level="error")
            await self.scene.update_message()
            return

        if demand_amount <= 0:
            await self._set_status("Город больше не покупает этот товар", level="error")
            await self.scene.update_message()
            return

        if value > available:
            await self._set_status(f"Недостаточно товара. Доступно: {available}", level="error")
            await self.scene.update_message()
            return

        sell_amount = min(value, demand_amount)
        response = await sell_to_city(city_id=city_id, company_id=company_id, resource_id=resource_key, amount=sell_amount)

        if response is not None:
            if isinstance(response, dict) and response.get("error"):
                await self._set_status(response.get("error", "Не удалось совершить сделку"), level="error")
                await self.scene.update_message()
                return
            if isinstance(response, str):
                await self._set_status(response, level="error")
                await self.scene.update_message()
                return

        await self._set_status(f"Продано {sell_amount} ед.", level="success")
        await self.scene.update_key("city-page", "stage", "product_info")
        await self.scene.update_message()

    async def _build_city_info_text(self, scene_data: dict, page_data: dict) -> str:
        session_id = scene_data.get("session")
        city_id = page_data.get("city_id")
        city_data = await self._load_city(city_id, session_id)

        if not city_data:
            return "❌ Не удалось загрузить данные города"

        name = city_data.get("name", "Город")
        branch_id = city_data.get("branch", "-")
        branch_data = RESOURCES.get_resource(branch_id)
        branch = f"{branch_data.emoji} {branch_data.label}"
        cell_position = city_data.get("cell_position", "0.0")
        x_str, y_str = cell_position.split(".") if "." in cell_position else (cell_position, "0")
        try:
            x_idx = int(x_str)
            y_idx = int(y_str)
        except ValueError:
            x_idx, y_idx = 0, 0
        cell = xy_into_cell(x_idx, y_idx)
        demands = city_data.get("demands", {})

        return (
            f"🏙 **{name}**\n\n"
            f"📍 Клетка: {cell}\n"
            f"🏭 Отрасль: {branch or '-'}\n\n"
            f"Город ищет {len(demands)} видов товаров. Выберите ресурс ниже."
        )

    async def _build_product_info_text(self, scene_data: dict, page_data: dict) -> str:
        session_id = scene_data.get("session")
        company_id = scene_data.get("company_id")
        city_id = page_data.get("city_id")
        resource_key = page_data.get("current_product")
        city_data = await self._load_city(city_id, session_id)

        if not city_data or not resource_key:
            return "❌ Не удалось загрузить информацию о товаре"

        resource = RESOURCES.get_resource(resource_key)
        demand = city_data.get("demands", {}).get(resource_key, {})
        amount = demand.get("amount", 0)
        price = demand.get("price", 0)

        company_data = await get_company(id=company_id)
        available = 0
        if company_data and not isinstance(company_data, str):
            available = self._get_company_stock(company_data, resource_key)

        label = resource.label if resource else resource_key
        emoji = resource.emoji if resource else "📦"

        return (
            f"{emoji} **{label}**\n\n"
            f"Город купит до {amount} ед. по цене {price} 💰 за единицу.\n"
            f"На складе компании: {available} ед."
        )

    async def _build_sell_product_text(self, scene_data: dict, page_data: dict) -> str:
        session_id = scene_data.get("session")
        company_id = scene_data.get("company_id")
        city_id = page_data.get("city_id")
        resource_key = page_data.get("current_product")

        city_data = await self._load_city(city_id, session_id)
        demand = city_data.get("demands", {}).get(resource_key, {}) if city_data else {}
        demand_amount = demand.get("amount", 0)
        price = demand.get("price", 0)

        company_data = await get_company(id=company_id)
        available = 0
        if company_data and not isinstance(company_data, str):
            available = self._get_company_stock(company_data, resource_key)

        resource = RESOURCES.get_resource(resource_key)
        label = resource.label if resource else resource_key
        emoji = resource.emoji if resource else "📦"

        return (
            f"{emoji} **{label}**\n\n"
            f"Введите количество для продажи сообщением.\n"
            f"Город купит до {demand_amount} ед. по {price} 💰.\n"
            f"На складе компании: {available} ед."
        )

    async def _get_city_chunks(self, session_id: Optional[str]) -> List[List[dict]]:
        response = await get_cities(session_id=session_id)
        if response is None or isinstance(response, str):
            return []
        if not isinstance(response, list):
            return []
        return self._chunk_list(response, 4)

    async def _change_city_page(self, shift: int) -> None:
        scene_data = self.scene.get_data("scene")
        page_data = self.scene.get_data("city-page")
        session_id = scene_data.get("session")
        chunks = await self._get_city_chunks(session_id)
        if not chunks:
            return
        current_page = self._clamp_page(page_data.get("page_cities", 0), len(chunks))
        new_page = self._clamp_page(current_page + shift, len(chunks))
        await self.scene.update_key("city-page", "page_cities", new_page)
        await self.scene.update_message()

    async def _change_product_page(self, shift: int) -> None:
        scene_data = self.scene.get_data("scene")
        page_data = self.scene.get_data("city-page")
        city_id = page_data.get("city_id")
        session_id = scene_data.get("session")
        city_data = await self._load_city(city_id, session_id)
        demands = city_data.get("demands", {}) if city_data else {}
        chunks = self._chunk_list(list(demands.keys()), 4)
        if not chunks:
            return
        current_page = self._clamp_page(page_data.get("page_products", 0), len(chunks))
        new_page = self._clamp_page(current_page + shift, len(chunks))
        await self.scene.update_key("city-page", "page_products", new_page)
        await self.scene.update_message()

    async def _load_city(self, city_id: Optional[int], session_id: Optional[str]) -> Optional[dict]:
        if not city_id:
            return None
        response = await get_city(id=city_id, session_id=session_id)
        if response is None or isinstance(response, str):
            return None
        if isinstance(response, dict) and response.get("error"):
            return None
        return response

    async def _company_has_product(self, scene_data: dict, page_data: dict) -> bool:
        company_id = scene_data.get("company_id")
        resource_key = page_data.get("current_product")
        city_id = page_data.get("city_id")
        session_id = scene_data.get("session")
        if not company_id or not resource_key or not city_id:
            return False

        city_data = await self._load_city(city_id, session_id)
        demand_amount = 0
        if city_data:
            demand_amount = city_data.get("demands", {}).get(resource_key, {}).get("amount", 0)
        if demand_amount <= 0:
            return False

        company_data = await get_company(id=company_id)
        if company_data is None or isinstance(company_data, str):
            return False
        return self._get_company_stock(company_data, resource_key) > 0

    @staticmethod
    def _get_company_stock(company_data: dict, resource_key: str) -> int:
        if not isinstance(company_data, dict):
            return 0

        warehouse_data = {}

        if isinstance(company_data.get("warehouses"), dict):
            warehouse_data = company_data.get("warehouses", {})
        elif isinstance(company_data.get("warehouse"), dict):
            warehouse_data = company_data.get("warehouse", {})

        value = warehouse_data.get(resource_key, 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    async def _set_status(self, message: Optional[str] = None, level: str = "info") -> None:
        await self.scene.update_key("city-page", "status_message", message)
        await self.scene.update_key("city-page", "status_level", level)

    @staticmethod
    def _chunk_list(items: List, chunk_size: int) -> List[List]:
        if chunk_size <= 0:
            return [items] if items else []
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    @staticmethod
    def _clamp_page(value: int, total_pages: int) -> int:
        if total_pages <= 0:
            return 0
        if value < 0:
            return 0
        if value >= total_pages:
            return total_pages - 1
        return value


