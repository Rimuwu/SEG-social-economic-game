from oms import Page
from aiogram.types import Message
from modules.ws_client import get_company, get_users

class WaitStart(Page):

    __page_name__ = 'wait-start-page'
    
    
    async def content_worker(self) -> str:
        try:
            scene_data = self.scene.get_data('scene')
            if not scene_data:
                return "⏳ Загрузка данных компании..."
            
            company_id = scene_data.get('company_id')
            session_id = scene_data.get('session')
            
            if not company_id or not session_id:
                return "⏳ Ожидание данных о компании..."

            user_company = await get_company(id=company_id, session_id=session_id)
            if not user_company:
                return "❌ Ошибка загрузки данных компании"
                
            company_name = user_company.get('name', 'Неизвестная компания')
            secret_code = user_company.get('secret_code', 'Неизвестно')
            
            participants = await get_users(session_id=session_id, company_id=company_id)
            if not participants:
                participants = []
                
            content = (
                    f"🏢 **{company_name}**\n\n"
                    f"🔑 Код для присоединения: {secret_code}\n\n"
                    f"👥 Участники компании:\n"
                )
            
            if participants:
                for user_n in participants:
                    username = user_n.get('username', 'Неизвестный пользователь')
                    content += f" - {username}\n"
            else:
                content += " - Загрузка участников...\n"
                
            content += "\nОжидание начала игры..."
            return content
            
        except Exception as e:
            return f"❌ Ошибка при загрузке данных: {str(e)}"