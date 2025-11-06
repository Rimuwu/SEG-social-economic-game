from oms import Page
from modules.ws_client import get_sessions
from modules.utils import create_buttons


class AdminSessionMainPage(Page):
    __page_name__ = "admin-session-main-page"
    
    async def content_worker(self):
        result = await get_sessions()
        
        session = "Нет активных сессий"
        if len(result) > 0:
            session = "Активные сессии:\n"
            for s in result:
                session += f"ID: {s.get('id')} | Статус: {s.get('stage')} | Ход: {s.get('step')}/{s.get('max_steps')}\n"
        
        return self.content.format(
            sessions=session
        )