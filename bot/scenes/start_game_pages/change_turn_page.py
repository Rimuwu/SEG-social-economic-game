from oms import Page
from modules.ws_client import get_session


class ChangeTurnPage(Page):
    __page_name__ = "change-turn-page"
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Создаёт текстовый прогресс-бар"""
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        return bar
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')          
        session_id = scene_data.get('session')
        session_response = await get_session(session_id=session_id)
        current_step = session_response.get('step', 0)
        max_steps = session_response.get('max_steps', 15)
        progress_bar = self.create_progress_bar(current_step, max_steps, 15)
        return self.content.format(
            progress_bar=progress_bar,
            current_step=current_step,
            max_steps=max_steps
        )