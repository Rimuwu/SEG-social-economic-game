from oms import Page
from aiogram.types import Message
from modules.ws_client import get_company, get_session, get_users

class WaitStart(Page):

    __page_name__ = 'wait-start-page'
    
    
    async def content_worker(self) -> str:
        company_id = self.scene.get_key("scene", "company_id")
        session_id = self.scene.get_key("scene", "session")
        s = await get_session(session_id=session_id)
        users = await get_users(company_id=company_id)
        result = await get_company(id=company_id)
        if "error" in s:
            return s["error"]
        url_group = s.get("session_group_url")
        if "error" in result:
            return result["error"]
        company_name = result.get("name")
        code = result.get("secret_code")
        users_list = ""
        for u in users:
            users_list += f" - 👤 {u.get('username')}\n"
        
        return self.content.format(company_name=company_name, code=code, url_group=url_group, users_list=users_list)