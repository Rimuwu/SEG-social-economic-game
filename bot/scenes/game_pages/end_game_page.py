from oms import Page
from modules.ws_client import get_all_session_statistics, get_session_leaders
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class EndGamePage(Page):
    __page_name__ = "end-game-page"
    
    async def content_worker(self) -> str:
        session_id = self.scene.get_key("scene", "session")
        return self.content
