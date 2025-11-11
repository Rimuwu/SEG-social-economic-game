from oms import Page
from aiogram.types import CallbackQuery
from modules.ws_client import get_company, get_session
from oms.utils import callback_generator



class PrisonPage(Page):
    __page_name__ = "prison-page"
    
    async def content_worker(self) -> str:
        scene_data = self.scene.get_data('scene')
        
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        company_response = await get_company(id=company_id, session_id=session_id)
        session_response = await get_session(session_id=session_id)
        prison_end_step = company_response.get('prison_end_step')
        current_step = session_response.get('step')
        max_steps = session_response.get('max_steps')
        steps_remaining = prison_end_step - current_step
        text_chance = ""
        if prison_end_step > max_steps:
            text_chance = "...в этой сессии вы уже не выйдете из тюрьмы."
        else:
            text_chance = f"...осталось ходов до выхода: {steps_remaining}."
        
        return self.content.format(
            prison_reason=company_response.get('prison_reason'),
            text_chance=text_chance
        )
            
