from oms import Page
from modules.ws_client import get_session_event, get_session
from global_modules.load_config import ALL_CONFIGS, Events
from global_modules.models.events import Event


EVENTS: Events = ALL_CONFIGS["events"]


class AboutTurnPage(Page):
    __page_name__ = "about-turn-page"
    
    async def content_worker(self):
        data = self.scene.get_data("scene")
        session_id = data.get("session")
        if not session_id:
            return "❌ Сессия не выбрана"

        session_data = await get_session(session_id)
        if not isinstance(session_data, dict):
            return "❌ Не удалось получить данные сессии"

        step = session_data.get("step")
        max_steps = session_data.get("max_steps")

        lines = ["📊 **Текущий ход**"]
        if step is not None and max_steps is not None:
            lines.append(f"Ход {step} из {max_steps}")
        elif step is not None:
            lines.append(f"Ход {step}")

        event_response = await get_session_event(session_id)
        event_payload = {}

        if isinstance(event_response, dict):
            if event_response.get("error"):
                lines.append("")
                lines.append(f"❌ {event_response['error']}")
                return "\n".join(lines)
            event_payload = event_response.get("event") or {}
        elif isinstance(event_response, str):
            lines.append("")
            lines.append(f"❌ {event_response}")
            return "\n".join(lines)

        if not event_payload:
            lines.append("")
            lines.append("🔕 Активных событий нет")
            return "\n".join(lines)

        event_lines = self._format_event_info(event_payload, step)
        if event_lines:
            lines.append("")
            lines.extend(event_lines)

        return "\n".join(lines)

    def _format_event_info(self, event_data: dict, current_step: int | None) -> list[str]:
        event_id = event_data.get("id")
        event_config: Event | None = EVENTS.events.get(event_id) if event_id else None

        name = event_data.get("name") or (event_config.name if event_config else "Неизвестное событие")
        description = event_data.get("description") or (event_config.description if event_config else "Информация недоступна")
        category = event_data.get("category") or (event_config.category.value if event_config else "")
        start_step = event_data.get("start_step")
        end_step = event_data.get("end_step")
        is_active = event_data.get("is_active")
        starts_next_turn = event_data.get("starts_next_turn")
        predictable = event_data.get("predictable")

        lines = [f"📣 **{name}**", description]

        if category:
            category_badge = {
                "positive": "🟢 Положительное",
                "negative": "🔴 Отрицательное"
            }.get(category, category)
            lines.append(category_badge)

        status_parts: list[str] = []
        if is_active:
            status_parts.append("Активно сейчас")
        elif starts_next_turn:
            status_parts.append("Начнётся на следующем ходу")
        elif predictable:
            status_parts.append("Ожидается (предсказуемое)")

        if start_step is not None and end_step is not None:
            lines.append(f"Действует с {start_step}-го по {end_step}-й ход")
            if current_step is not None and not is_active and start_step > current_step:
                steps_until = start_step - current_step
                status_parts.append(f"До старта: {steps_until}")

        if status_parts:
            lines.append(", ".join(status_parts))

        if event_config and event_config.duration.min is not None and event_config.duration.max is not None:
            duration_min = event_config.duration.min
            duration_max = event_config.duration.max
            if duration_min == duration_max:
                lines.append(f"Длительность события: {duration_min} хода")
            else:
                lines.append(f"Длительность события: {duration_min}–{duration_max} ходов")

        return lines
            