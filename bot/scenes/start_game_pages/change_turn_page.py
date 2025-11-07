from oms import Page
from modules.ws_client import get_session
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class ChangeTurnPage(Page):
    __page_name__ = "change-turn-page"
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Создаёт текстовый прогресс-бар"""
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        return bar
    
    async def content_worker(self):
        try:
            scene_data = self.scene.get_data('scene')
            if not scene_data:
                return "⏳ Загрузка данных..."
            
            session_id = scene_data.get('session')
            if not session_id:
                return "❌ Ошибка: ID сессии не найден"

            # Получаем информацию о сессии
            session_response = await get_session(session_id=session_id)
            if not session_response or "error" in session_response:
                return "❌ Ошибка загрузки данных сессии"

            current_step = session_response.get('step', 0)
            max_steps = session_response.get('max_steps', 15)

            # Создаём прогресс-бар
            progress_bar = self.create_progress_bar(current_step, max_steps, 15)

            content = "🔄 **Смена хода...**\n\n"
            content += "⏳ Ожидаем следующего этапа...\n\n"
            content += f"**Этап** {progress_bar} **{current_step}/{max_steps}**"

            return content
            
        except Exception as e:
            bot_logger.error(f"Ошибка в ChangeTurnPage.content_worker: {e}")
            return f"❌ Ошибка при загрузке данных: {str(e)}"