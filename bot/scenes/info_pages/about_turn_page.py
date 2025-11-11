from oms import Page
from modules.ws_client import get_session_event, get_session
from global_modules.load_config import ALL_CONFIGS, Events
from global_modules.models.events import Event


EVENTS: Events = ALL_CONFIGS["events"]


class AboutTurnPage(Page):
    __page_name__ = "about-turn-page"
    
    async def data_preparate(self):
        session_id = self.scene.get_key("scene", "session")
        session_data = await get_session(session_id)
        event_response = await get_session_event(session_id)
        await self.scene.update_key(self.__page_name__, 'session_data', session_data)
        await self.scene.update_key(self.__page_name__, 'event_response', event_response)
    
    async def content_worker(self):
        data = self.scene.get_data("scene")
        session_id = data.get("session")
        if not session_id:
            return "❌ Сессия не выбрана"
        session_data = self.scene.get_key(self.__page_name__, 'session_data')
        if not isinstance(session_data, dict):
            return "❌ Не удалось получить данные сессии"
        step = session_data.get("step")
        max_steps = session_data.get("max_steps")
        event_response = self.scene.get_key(self.__page_name__, 'event_response')
        event_payload = event_response.get("event") if isinstance(event_response, dict) else {}
        if not event_payload:
            event_text = ("🔕 Активных событий нет")
        else:
            event_text = self._format_event_info(event_payload, step)

        return self.content.format(
            step=step,
            max_steps=max_steps,
            event_text="\n".join(event_text) if isinstance(event_text, list) else event_text
        )

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
            