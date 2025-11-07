from oms import Page
from modules.ws_client import get_company
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class WaitSelectCellPage(Page):
    __page_name__ = "wait-select-cell-page"
    
    async def content_worker(self) -> str:
        try:
            scene_data = self.scene.get_data('scene')
            if not scene_data:
                return "⏳ Загрузка данных компании..."
            
            company_id = scene_data.get('company_id')
            session_id = scene_data.get('session')
            
            if not company_id or not session_id:
                return "⏳ Ожидание данных о компании..."

            # Получаем данные компании
            user_company = await get_company(id=company_id, session_id=session_id)
            if not user_company:
                return "❌ Ошибка загрузки данных компании"
                
            company_name = user_company.get('name', 'Неизвестная компания')
            
            content = f"🏢 **{company_name}**\n\n"
            content += "⏳ **Ожидание выбора клетки владельцем компании...**\n\n"
            content += "📍 Владелец компании сейчас выбирает клетку на карте.\n"
            content += "Пожалуйста, подождите."
            
            return content
            
        except Exception as e:
            bot_logger.error(f"Ошибка в WaitSelectCellPage.content_worker: {e}")
            return f"❌ Ошибка при загрузке данных: {str(e)}"
