from oms import Page
from modules.ws_client import get_all_session_statistics, get_session_leaders


class EndGamePage(Page):
    __page_name__ = "end-game-page"
    
    async def content_worker(self) -> str:
        session_id = self.scene.get_key("scene", "session")
        leaders = await get_session_leaders(session_id=session_id)
        economic_leaders = leaders["economic"]["name"]
        reputation_leaders = leaders["reputation"]["name"]
        balance_leaders = leaders["capital"]["name"]
        return self.content.format(
            economic_leaders=economic_leaders,
            reputation_leaders=reputation_leaders,
            balance_leaders=balance_leaders
        )
