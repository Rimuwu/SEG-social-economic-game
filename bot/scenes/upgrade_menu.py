from typing import Dict, Optional
from aiogram.types import CallbackQuery
from modules.ws_client import get_company, update_company_improve, get_company_cell_info
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Improvements, Cells
from global_modules.models.improvements import ImprovementLevel
from .oneuser_page import OneUserPage


IMPROVEMENTS: Improvements = ALL_CONFIGS["improvements"]
CELLS: Cells = ALL_CONFIGS["cells"]

IMPROVEMENT_OPTIONS = {
    "warehouse": {"emoji": "📦", "label": "Склад"},
    "contracts": {"emoji": "📋", "label": "Контракты"},
    "factory": {"emoji": "🏭", "label": "Заводы"},
    "station": {"emoji": "⛏️", "label": "Добывающие станции"},
}


Page = OneUserPage

class UpgradeMenu(Page):
    __page_name__ = "upgrade-menu"

    async def data_preparate(self):
        page_data = self.scene.get_data(self.__page_name__)
        if page_data is None:
            await self.scene.set_data(self.__page_name__, {})
            page_data = {}

        if page_data.get("stage") is None:
            await self.scene.update_key(self.__page_name__, "stage", "choose_type")

        if page_data.get("selected_type") is None:
            await self.scene.update_key(self.__page_name__, "selected_type", None)

        if page_data.get("status_message") is None:
            await self.scene.update_key(self.__page_name__, "status_message", None)

        if page_data.get("status_level") is None:
            await self.scene.update_key(self.__page_name__, "status_level", "info")

    async def content_worker(self):
        scene_data = self.scene.get_data("scene")
        page_data = self.scene.get_data(self.__page_name__)
        company_id = scene_data.get("company_id")
        stage = page_data.get("stage", "choose_type")

        if not company_id:
            return "❌ Компания не выбрана"

        company_data = await get_company(id=company_id)
        if not isinstance(company_data, dict):
            return "❌ Не удалось получить данные компании"

        lines = ["🔧 **Улучшения компании**"]

        if stage == "choose_type":
            lines.append("")
            lines.append("Выберите тип улучшения, чтобы посмотреть детали.")
            lines.append("")
            lines.append("Текущие уровни:")
            improvements = company_data.get("improvements", {})
            for key, meta in IMPROVEMENT_OPTIONS.items():
                level = self._as_int(improvements.get(key, 1), 1)
                lines.append(f"{meta['emoji']} {meta['label']}: уровень {level}")
        elif stage == "details":
            selected_type = page_data.get("selected_type")
            if not selected_type:
                lines.append("")
                lines.append("❌ Тип улучшения не выбран")
            else:
                detail_lines = await self._build_detail_lines(company_data, selected_type)
                lines.extend(detail_lines)
        else:
            lines.append("")
            lines.append("❌ Неизвестный этап страницы")

        status_message = page_data.get("status_message")
        status_level = page_data.get("status_level", "info")
        if status_message:
            prefix = "✅" if status_level == "success" else "❌" if status_level == "error" else "ℹ️"
            lines.append("")
            lines.append(f"{prefix} {status_message}")

        return "\n".join(lines)

    async def buttons_worker(self):
        page_data = self.scene.get_data(self.__page_name__)
        scene_data = self.scene.get_data("scene")
        company_id = scene_data.get("company_id")
        stage = page_data.get("stage", "choose_type")
        buttons: list[dict] = []

        if stage == "choose_type":
            self.row_width = 2
            for key, meta in IMPROVEMENT_OPTIONS.items():
                buttons.append({
                    "text": f"{meta['emoji']} {meta['label']}",
                    "callback_data": callback_generator(self.scene.__scene_name__, "upgrade_select", key)
                })
        elif stage == "details":
            self.row_width = 1
            selected_type = page_data.get("selected_type")
            if selected_type:
                upgrade_available = False
                if company_id:
                    company_data = await get_company(id=company_id)
                    if isinstance(company_data, dict):
                        state = await self._get_improvement_state(company_data, selected_type)
                        upgrade_available = state.get("next_config") is not None

                if upgrade_available:
                    buttons.append({
                        "text": "⬆️ Улучшить",
                        "callback_data": callback_generator(self.scene.__scene_name__, "upgrade_perform")
                    })

            buttons.append({
                "text": "⬅️ Выбор улучшений",
                "callback_data": callback_generator(self.scene.__scene_name__, "upgrade_back")
            })

        return buttons

    @Page.on_callback('upgrade_select')
    async def select_improvement_callback(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return

        improvement_type = args[1]
        if improvement_type not in IMPROVEMENT_OPTIONS:
            await callback.answer("❌ Неизвестный тип улучшений", show_alert=True)
            return

        await self.scene.update_key(self.__page_name__, "selected_type", improvement_type)
        await self.scene.update_key(self.__page_name__, "stage", "details")
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('upgrade_back')
    async def back_callback(self, callback: CallbackQuery, args: list):
        await self.scene.update_key(self.__page_name__, "stage", "choose_type")
        await self.scene.update_key(self.__page_name__, "selected_type", None)
        await self._set_status()
        await self.scene.update_message()
        await callback.answer()

    @Page.on_callback('upgrade_perform')
    async def perform_upgrade_callback(self, callback: CallbackQuery, args: list):
        scene_data = self.scene.get_data("scene")
        page_data = self.scene.get_data(self.__page_name__)
        improvement_type = page_data.get("selected_type")
        company_id = scene_data.get("company_id")

        if not improvement_type or improvement_type not in IMPROVEMENT_OPTIONS:
            await callback.answer("❌ Не выбран тип улучшения", show_alert=True)
            return

        if not company_id:
            await callback.answer("❌ Компания не найдена", show_alert=True)
            return

        company_data = await get_company(id=company_id)
        if not isinstance(company_data, dict):
            await self._set_status("Не удалось загрузить данные компании", level="error")
            await self.scene.update_message()
            await callback.answer("Ошибка", show_alert=True)
            return

        state = await self._get_improvement_state(company_data, improvement_type)
        next_config: Optional[ImprovementLevel] = state.get("next_config")

        if not next_config:
            await self._set_status("Достигнут максимальный уровень", level="error")
            await self.scene.update_message()
            await callback.answer("Максимальный уровень", show_alert=True)
            return

        cost = next_config.cost
        balance_value = self._to_optional_int(company_data.get("balance"))
        balance = balance_value if balance_value is not None else 0

        if cost is not None and balance is not None and balance < cost:
            await self._set_status("Недостаточно средств для улучшения", level="error")
            await self.scene.update_message()
            await callback.answer("Недостаточно средств", show_alert=True)
            return

        response = await update_company_improve(company_id=company_id, improvement_type=improvement_type)
        if isinstance(response, dict) and response.get("error"):
            await self._set_status(response.get("error", "Не удалось выполнить улучшение"), level="error")
            await self.scene.update_message()
            await callback.answer("Ошибка", show_alert=True)
            return

        new_level = state.get("next_level")
        await self._set_status(f"Улучшение повышено до уровня {new_level}", level="success")
        await self.scene.update_message()
        await callback.answer("Готово")

    async def _build_detail_lines(self, company_data: dict, improvement_type: str) -> list[str]:
        improvements = company_data.get("improvements", {})
        balance = self._to_optional_int(company_data.get("balance"))
        level = self._as_int(improvements.get(improvement_type, 1), 1)
        meta = IMPROVEMENT_OPTIONS.get(improvement_type, {})
        state = await self._get_improvement_state(company_data, improvement_type)
        current_cfg: Optional[ImprovementLevel] = state.get("current_config")
        next_cfg: Optional[ImprovementLevel] = state.get("next_config")
        next_level = state.get("next_level")
        cell_type = state.get("cell_type")

        lines = [""]
        header = f"{meta.get('emoji', '🔧')} **{meta.get('label', 'Улучшение')}**"
        lines.append(header)
        lines.append(f"Текущий уровень: {level}")

        if cell_type:
            cell_label = CELLS.types.get(cell_type).label if CELLS.types.get(cell_type) else cell_type
            lines.append(f"Тип клетки: {cell_label}")

        current_stats = self._format_stats(current_cfg, improvement_type, title="Текущие характеристики")
        lines.extend(current_stats)

        if next_cfg:
            lines.append("")
            lines.append(f"➡️ После улучшения (уровень {next_level}):")
            target_stats = self._format_stats(next_cfg, improvement_type)
            lines.extend(target_stats)
            lines.append(f"Стоимость: {self._format_number(next_cfg.cost)} 💰")
            if balance is not None and next_cfg.cost is not None and balance < next_cfg.cost:
                lines.append("⚠️ Недостаточно средств на счету")
        else:
            lines.append("")
            lines.append("✅ Достигнут максимальный уровень")

        if balance is not None:
            lines.append("")
            lines.append(f"Баланс компании: {self._format_number(balance)} 💰")

        return lines

    async def _get_improvement_state(self, company_data: dict, improvement_type: str) -> Dict[str, Optional[object]]:
        company_id = company_data.get("id")
        improvements = company_data.get("improvements", {})
        current_level = self._as_int(improvements.get(improvement_type, 1), 1)
        next_level = current_level + 1

        cell_type = None
        if improvement_type in {"factory", "station"} and company_id is not None:
            cell_type = await self._get_cell_type(company_id)

        lookup_key = cell_type if cell_type else improvement_type
        current_cfg = IMPROVEMENTS.get_improvement(lookup_key, improvement_type, str(current_level))
        next_cfg = IMPROVEMENTS.get_improvement(lookup_key, improvement_type, str(next_level))

        return {
            "current_config": current_cfg,
            "next_config": next_cfg,
            "current_level": current_level,
            "next_level": next_level if next_cfg else None,
            "cell_type": cell_type,
        }

    async def _get_cell_type(self, company_id: int) -> Optional[str]:
        response = await get_company_cell_info(company_id=company_id)
        cell_type = None
        if isinstance(response, dict):
            cell_type = response.get("type")
        return cell_type

    def _format_stats(self, config: Optional[ImprovementLevel], improvement_type: str, title: Optional[str] = None) -> list[str]:
        if not config:
            return ["Информация недоступна"]

        lines: list[str] = []
        if title:
            lines.append(title)

        if improvement_type == "warehouse" and config.capacity is not None:
            lines.append(f"Вместимость: {self._format_number(config.capacity)} ед.")
        elif improvement_type == "contracts" and config.max is not None:
            lines.append(f"Доступно контрактов: {config.max}")
        elif improvement_type == "station" and config.productsPerTurn is not None:
            lines.append(f"Добыча за ход: {self._format_number(config.productsPerTurn)} ед.")
        elif improvement_type == "factory" and config.tasksPerTurn is not None:
            lines.append(f"Задач за ход: {self._format_number(config.tasksPerTurn)} шт.")
        else:
            lines.append("Параметры уровня отсутствуют")

        return lines

    def _format_number(self, value: Optional[int]) -> str:
        if value is None:
            return "—"
        return f"{value:,}".replace(",", " ")

    def _as_int(self, value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _to_optional_int(self, value) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def _set_status(self, message: Optional[str] = None, level: str = "info") -> None:
        await self.scene.update_key(self.__page_name__, "status_message", message)
        await self.scene.update_key(self.__page_name__, "status_level", level)
    
    