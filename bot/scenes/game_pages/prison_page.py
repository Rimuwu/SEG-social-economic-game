from oms import Page
from aiogram.types import CallbackQuery
from modules.ws_client import get_company, get_session
from oms.utils import callback_generator
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class PrisonPage(Page):
    __page_name__ = "prison-page"
    
    async def content_worker(self) -> str:
        try:
            scene_data = self.scene.get_data('scene')
            if not scene_data:
                return "⏳ Загрузка данных..."
            
            company_id = scene_data.get('company_id')
            session_id = scene_data.get('session')
            
            if not company_id or not session_id:
                return "❌ Ошибка: Данные компании не найдены"

            # Получаем данные компании
            company_response = await get_company(id=company_id, session_id=session_id)
            if not company_response or "error" in company_response:
                return "❌ Ошибка загрузки данных компании"

            # Получаем данные сессии
            session_response = await get_session(session_id=session_id)
            if not session_response or "error" in session_response:
                return "❌ Ошибка загрузки данных сессии"

            company_name = company_response.get('name', 'Неизвестная компания')
            prison_end_step = company_response.get('prison_end_step')
            current_step = session_response.get('step', 0)
            in_prison = company_response.get('in_prison', False)

            content = "🚔 **ТЮРЬМА** 🚔\n\n"
            
            if not in_prison:
                content += "✅ Ваша компания не находится в тюрьме.\n"
                return content

            content += f"🏢 **Компания**: {company_name}\n\n"
            content += "⛓️ Ваша компания находится в тюрьме!.\n\n"
            
            if prison_end_step is not None:
                steps_remaining = prison_end_step - current_step
                if steps_remaining > 0:
                    content += f"⏳ **Освобождение через**: {steps_remaining} ход(а/ов)\n"
                    content += f"📅 **Освобождение на ходу**: {prison_end_step}\n\n"
                    content += "В это время:\n"
                    content += "• ❌ Невозможно управлять заводами\n"
                    content += "• ❌ Невозможно совершать сделки\n"
                    content += "• ❌ Невозможно брать кредиты\n\n"
                    content += "💡 *Не забывайте платить налоги, вовремя закрывать кредиты и выполнять контракты!*"
                else:
                    content += "✅ **Освобождение происходит на этом ходу!**\n"
                    content += "Ожидайте начала следующего этапа..."
            else:
                content += "⚠️ Срок освобождения не определён.\n"
                content += "Обратитесь к администратору."

            return content
            
        except Exception as e:
            bot_logger.error(f"Ошибка в PrisonPage.content_worker: {e}")
            return f"❌ Ошибка при загрузке данных: {str(e)}"
