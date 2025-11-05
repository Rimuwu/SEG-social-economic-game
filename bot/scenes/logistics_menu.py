from typing import Dict, List, Optional
from aiogram.types import CallbackQuery, Message  # type: ignore
from oms.utils import callback_generator
from modules.ws_client import get_logistics, logistics_pickup
from global_modules.load_config import ALL_CONFIGS, Resources
from modules.utils import xy_into_cell
from .oneuser_page import OneUserPage


RESOURCES: Resources = ALL_CONFIGS["resources"]
Page = OneUserPage

class LogisticsMenu(Page):

    __page_name__ = "logistics-menu"

    async def data_preparate(self):
        if self.scene.get_key("logistics-menu", "stage") is None:
            await self.scene.update_key("logistics-menu", "stage", "main")
        if self.scene.get_key("logistics-menu", "logistics_page") is None:
            await self.scene.update_key("logistics-menu", "logistics_page", 0)
        if self.scene.get_key("logistics-menu", "current_logistics_id") is None:
            await self.scene.update_key("logistics-menu", "current_logistics_id", None)
        if self.scene.get_key("logistics-menu", "status_message") is None:
            await self.scene.update_key("logistics-menu", "status_message", None)
        if self.scene.get_key("logistics-menu", "status_level") is None:
            await self.scene.update_key("logistics-menu", "status_level", "info")

    async def content_worker(self):
        scene_data = self.scene.get_data("scene")
        page_data = self.scene.get_data("logistics-menu")
        stage = page_data.get("stage", "main")
        company_id = scene_data.get("company_id")
        session_id = scene_data.get("session")
        lines: List[str] = []

        if not company_id or not session_id:
            return "❌ Не найдена активная компания или сессия"

        logistics = await self._get_company_logistics(session_id, company_id)

        if stage == "main":
            lines.extend(await self._build_main_text(logistics, company_id))
        elif stage == "list":
            lines.extend(await self._build_list_text(page_data, logistics))
        elif stage == "detail":
            detail = await self._build_detail_text(page_data, logistics, company_id)
            lines.extend(detail)
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
        scene_data = self.scene.get_data("scene") or {}
        page_data = self.scene.get_data("logistics-menu")
        stage = page_data.get("stage", "main")
        company_id = scene_data.get("company_id")
        session_id = scene_data.get("session")
        buttons: List[dict] = []

        if not company_id or not session_id:
            return buttons

        logistics = await self._get_company_logistics(session_id, company_id)

        if stage == "main":
            self.row_width = 1
            buttons.append({
                "text": "🚚 Все маршруты",
                "callback_data": callback_generator(self.scene.__scene_name__, "logistics_view")
            })
            buttons.append({
                "text": "📦 Забрать доставленные",
                "callback_data": callback_generator(self.scene.__scene_name__, "logistics_claim")
            })
            buttons.append({
                "text": "⬅️ Назад",
                "callback_data": callback_generator(self.scene.__scene_name__, "back_main_page")
            })
        elif stage == "list":
            self.row_width = 1
            chunks = self._chunk_list(logistics, 4)
            if not chunks:
                buttons.append({
                    "text": "🔄 Обновить",
                    "callback_data": callback_generator(self.scene.__scene_name__, "logistics_refresh")
                })
            else:
                current_page = self._clamp_page(page_data.get("logistics_page", 0), len(chunks))
                await self.scene.update_key("logistics-menu", "logistics_page", current_page)
                for item in chunks[current_page]:
                    buttons.append({
                        "text": self._format_list_button(item, company_id),
                        "callback_data": callback_generator(self.scene.__scene_name__, "logistics_select", item.get("id", 0))
                    })
                if len(chunks) > 1:
                    buttons.append({
                        "text": "◀️",
                        "callback_data": callback_generator(self.scene.__scene_name__, "logistics_page_prev"),
                        "next_line": True
                    })
                    buttons.append({
                        "text": f"{current_page + 1}/{len(chunks)}",
                        "callback_data": callback_generator(self.scene.__scene_name__, "noop")
                    })
                    buttons.append({
                        "text": "▶️",
                        "callback_data": callback_generator(self.scene.__scene_name__, "logistics_page_next")
                    })
            buttons.append({
                "text": "⬅️ Назад",
                "callback_data": callback_generator(self.scene.__scene_name__, "logistics_back_main"),
                "next_line": True
            })
        elif stage == "detail":
            self.row_width = 1
            current_id = page_data.get("current_logistics_id")
            logistic = self._find_logistic(logistics, current_id)
            if logistic and logistic.get("status") == "delivered" and logistic.get("to_company_id") == company_id:
                buttons.append({
                    "text": "📦 Забрать груз",
                    "callback_data": callback_generator(self.scene.__scene_name__, "logistics_pickup_one", current_id)
                })
            buttons.append({
                "text": "🔄 Обновить",
                "callback_data": callback_generator(self.scene.__scene_name__, "logistics_refresh")
            })
            buttons.append({
                "text": "⬅️ К списку",
                "callback_data": callback_generator(self.scene.__scene_name__, "logistics_back_list")
            })

        return buttons

    @Page.on_callback('logistics_view')
    async def view_list_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("logistics-menu", "stage", "list")
        await self.scene.update_key("logistics-menu", "logistics_page", 0)
        await self._set_status()
        await self.scene.update_message()
        await callback.answer("Показываю маршруты")

    @Page.on_callback('logistics_back_main')
    async def back_main_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("logistics-menu", "stage", "main")
        await self.scene.update_key("logistics-menu", "current_logistics_id", None)
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('logistics_back_list')
    async def back_list_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("logistics-menu", "stage", "list")
        await self.scene.update_key("logistics-menu", "current_logistics_id", None)
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('logistics_refresh')
    async def refresh_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('logistics_page_prev')
    async def page_prev_callback(self, callback: CallbackQuery, args: list):
        await self._change_page(-1)
        await callback.answer()

    @Page.on_callback('logistics_page_next')
    async def page_next_callback(self, callback: CallbackQuery, args: list):
        await self._change_page(1)
        await callback.answer()

    @Page.on_callback('noop')
    async def noop_callback(self, callback: CallbackQuery, args: list):
        await callback.answer()

    @Page.on_callback('logistics_select')
    async def select_logistics_callback(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return
        try:
            logistics_id = int(args[1])
        except ValueError:
            await callback.answer("❌ Некорректный идентификатор", show_alert=True)
            return
        await self.scene.update_key("logistics-menu", "current_logistics_id", logistics_id)
        await self.scene.update_key("logistics-menu", "stage", "detail")
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('logistics_claim')
    async def claim_all_callback(self, callback: CallbackQuery, args: list):
        scene_data = self.scene.get_data("scene") or {}
        session_id = scene_data.get("session")
        company_id = scene_data.get("company_id")
        if not session_id or not company_id:
            await self._set_status("Компания не найдена", level="error")
            await self.scene.update_message()
            await callback.answer("Ошибка", show_alert=True)
            return

        logistics = await self._get_company_logistics(session_id, company_id)
        targets = [item for item in logistics if item.get("status") == "delivered" and item.get("to_company_id") == company_id]

        if not targets:
            await self._set_status("Нет доставленных грузов для получения", level="info")
            await self.scene.update_message()
            await callback.answer("Нет доставленных грузов")
            return

        success = 0
        errors: List[str] = []
        has_errors = False
        for item in targets:
            response = await logistics_pickup(logistics_id=item.get("id"), company_id=company_id)
            if isinstance(response, dict) and response.get("success"):
                success += 1
            else:
                err_text = "Не удалось получить груз"
                if isinstance(response, dict) and response.get("error"):
                    err_text = response.get("error")
                elif isinstance(response, str):
                    err_text = response
                errors.append(f"#{item.get('id')}: {err_text}")
                has_errors = True

        if errors:
            await self._set_status("\n".join(errors), level="error")
            reply_text = "Не удалось получить часть грузов"
        else:
            await self._set_status(f"Получено грузов: {success}", level="success")
            reply_text = f"Получено грузов: {success}"

        await self.scene.update_message()
        await callback.answer(reply_text, show_alert=has_errors)

    @Page.on_callback('logistics_pickup_one')
    async def claim_one_callback(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return
        try:
            logistics_id = int(args[1])
        except ValueError:
            await callback.answer("❌ Некорректный идентификатор", show_alert=True)
            return

        scene_data = self.scene.get_data("scene") or {}
        company_id = scene_data.get("company_id")
        session_id = scene_data.get("session")
        if not company_id or not session_id:
            await self._set_status("Компания не найдена", level="error")
            await self.scene.update_message()
            await callback.answer("Ошибка", show_alert=True)
            return

        response = await logistics_pickup(logistics_id=logistics_id, company_id=company_id)
        is_success = isinstance(response, dict) and response.get("success")
        if is_success:
            await self._set_status("Груз получен", level="success")
            reply_text = "Груз получен"
        else:
            error_message = "Не удалось получить груз"
            if isinstance(response, dict) and response.get("error"):
                error_message = response.get("error")
            elif isinstance(response, str):
                error_message = response
            await self._set_status(error_message, level="error")
            reply_text = error_message

        await self.scene.update_message()
        await callback.answer(reply_text, show_alert=not is_success)

    @Page.on_text('all')
    async def ignore_text(self, message: Message):
        return

    async def _build_main_text(self, logistics: List[dict], company_id: int) -> List[str]:
        lines = ["🚚 **Логистика**", ""]
        if not logistics:
            lines.append("Маршрутов пока нет. Создайте доставку со своих заводов или складов.")
            return lines

        total = len(logistics)
        in_transit = sum(1 for item in logistics if item.get("status") == "in_transit")
        delivered_to_company = sum(1 for item in logistics if item.get("status") == "delivered" and item.get("to_company_id") == company_id)
        waiting = sum(1 for item in logistics if item.get("status") == "waiting_pickup")

        lines.append(f"Всего маршрутов: {total}")
        if in_transit:
            lines.append(f"В пути: {in_transit}")
        if waiting:
            lines.append(f"Ожидают получения: {waiting}")
        if delivered_to_company:
            lines.append(f"Доставлены к вам: {delivered_to_company}")

        return lines
    
    
    @Page.on_callback('back_main_page')
    async def back_main_page(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("logistics-menu", "stage", "main")
        await self.scene.update_key("logistics-menu", "logistics_page", 0)
        await self.scene.update_key("logistics-menu", "current_logistics_id", None)
        await self.scene.update_key("logistics-menu", "status_message", None)
        await self.scene.update_key("logistics-menu", "status_level", "info")
        await self.scene.update_page('main-page')
        await callback.answer()
    

    async def _build_list_text(self, page_data: dict, logistics: List[dict]) -> List[str]:
        lines = ["🚚 **Маршруты доставки**"]
        if not logistics:
            lines.append("")
            lines.append("Активных маршрутов нет. Обновите страницу, чтобы проверить новые доставки.")
            return lines

        chunks = self._chunk_list(logistics, 4)
        current_page = self._clamp_page(page_data.get("logistics_page", 0), len(chunks))
        lines.append("")
        lines.append(f"Страница {current_page + 1} из {len(chunks)}")

        for item in chunks[current_page]:
            lines.append(self._format_list_entry(item))

        return lines

    async def _build_detail_text(self, page_data: dict, logistics: List[dict], company_id: int) -> List[str]:
        logistics_id = page_data.get("current_logistics_id")
        logistic = self._find_logistic(logistics, logistics_id)
        if not logistic:
            return ["❌ Логистика не найдена. Вернитесь к списку и попробуйте снова."]

        resource_key = logistic.get("resource_type")
        resource = RESOURCES.get_resource(resource_key)
        emoji = resource.emoji if resource else "📦"
        label = resource.label if resource else resource_key or "Ресурс"

        lines = [f"{emoji} **{label}**"]
        lines.append(f"Количество: {self._format_number(logistic.get('amount'))}")

        status_text = self._status_text(logistic.get("status"))
        lines.append(f"Статус: {status_text}")

        from_company = logistic.get("from_company_id")
        to_company = logistic.get("to_company_id")
        to_city = logistic.get("to_city_id")

        if from_company:
            sender = "Вы" if from_company == company_id else f"Компания #{from_company}"
            lines.append(f"Отправитель: {sender}")

        if logistic.get("destination_type") == "company":
            if to_company == company_id:
                lines.append("Получатель: Ваша компания")
            elif to_company:
                lines.append(f"Получатель: Компания #{to_company}")
        elif logistic.get("destination_type") == "city":
            lines.append(f"Получатель: Город #{to_city}")
            if logistic.get("city_price"):
                lines.append(f"Цена города: {self._format_number(logistic.get('city_price'))} 💰")

        current_position = logistic.get("current_position")
        target_position = logistic.get("target_position")
        if current_position:
            lines.append(f"Текущая клетка: {self._format_cell(current_position)}")
        if target_position:
            lines.append(f"Целевая клетка: {self._format_cell(target_position)}")

        distance_left = logistic.get("distance_left")
        if isinstance(distance_left, (int, float)):
            lines.append(f"Осталось клеток: {distance_left:.1f}")

        waiting_turns = logistic.get("waiting_turns")
        if waiting_turns:
            lines.append(f"Ходов ожидания: {waiting_turns}")

        created_step = logistic.get("created_step")
        if created_step is not None:
            lines.append(f"Создано на ходу: {created_step}")

        return lines

    async def _change_page(self, shift: int) -> None:
        page_data = self._get_page_data()
        current_page = page_data.get("logistics_page", 0)
        new_page = current_page + shift
        if new_page < 0:
            new_page = 0
        await self.scene.update_key("logistics-menu", "logistics_page", new_page)
        await self.scene.update_message()

    async def _get_company_logistics(self, session_id: str, company_id: int) -> List[dict]:
        response = await get_logistics(session_id=session_id)
        if response is None or isinstance(response, str):
            return []
        if isinstance(response, dict) and response.get("error"):
            return []
        if not isinstance(response, list):
            return []

        result: List[dict] = []
        for item in response:
            if not isinstance(item, dict):
                continue
            if item.get("from_company_id") == company_id or item.get("to_company_id") == company_id:
                result.append(item)
        result.sort(key=lambda x: x.get("created_step", 0), reverse=True)
        return result

    def _find_logistic(self, logistics: List[dict], logistics_id: Optional[int]) -> Optional[dict]:
        for item in logistics:
            if item.get("id") == logistics_id:
                return item
        return None

    def _format_list_button(self, item: dict, company_id: int) -> str:
        resource = RESOURCES.get_resource(item.get("resource_type"))
        emoji = resource.emoji if resource else "📦"
        label = resource.label if resource else item.get("resource_type", "Ресурс")
        amount = self._format_number(item.get("amount"))
        status_icon = self._status_icon(item.get("status"))

        if item.get("destination_type") == "city":
            dest = f"→ город #{item.get('to_city_id')}"
        else:
            if item.get("to_company_id") == company_id:
                dest = "→ вам"
            elif item.get("to_company_id"):
                dest = f"→ компания #{item.get('to_company_id')}"
            else:
                dest = "→ компания"

        return f"{status_icon} {emoji} {label} ×{amount} {dest}"

    def _format_list_entry(self, item: dict) -> str:
        status = self._status_text(item.get("status"))
        created_step = item.get("created_step")
        return f"#{item.get('id')} · {status} · ход {created_step}" if created_step is not None else f"#{item.get('id')} · {status}"

    def _status_icon(self, status: Optional[str]) -> str:
        return {
            "in_transit": "🚚",
            "waiting_pickup": "⌛",
            "delivered": "📦",
            "failed": "⚠️"
        }.get(status or "", "📦")

    def _status_text(self, status: Optional[str]) -> str:
        return {
            "in_transit": "В пути",
            "waiting_pickup": "Ожидает получения",
            "delivered": "Доставлено",
            "failed": "Не доставлено"
        }.get(status or "", "Неизвестно")

    def _format_cell(self, position: Optional[str]) -> str:
        if not position:
            return "—"
        parts = position.split('.')
        if len(parts) != 2:
            return position
        try:
            x_idx = int(parts[0])
            y_idx = int(parts[1])
        except ValueError:
            return position
        return xy_into_cell(x_idx, y_idx)

    def _format_number(self, value: Optional[int]) -> str:
        if value is None:
            return "0"
        try:
            return f"{int(value):,}".replace(",", " ")
        except (TypeError, ValueError):
            return str(value)

    async def _set_status(self, message: Optional[str] = None, level: str = "info") -> None:
        await self.scene.update_key("logistics-menu", "status_message", message)
        await self.scene.update_key("logistics-menu", "status_level", level)

    def _get_page_data(self) -> Dict[str, object]:
        data = self.scene.get_data("logistics-menu")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _chunk_list(items: List[dict], chunk_size: int) -> List[List[dict]]:
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