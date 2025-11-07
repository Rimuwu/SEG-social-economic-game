from oms import Page
from modules.ws_client import get_session_leaders, get_session
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class EndGamePage(Page):
    __page_name__ = "end-game-page"
    
    async def content_worker(self) -> str:
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

            # Получаем лидеров
            leaders_response = await get_session_leaders(session_id=session_id)
            if not leaders_response or "error" in leaders_response:
                return "❌ Ошибка загрузки данных лидеров"

            capital_leader = leaders_response.get('capital')
            reputation_leader = leaders_response.get('reputation')
            economic_leader = leaders_response.get('economic')

            content = "🎉 **Игра завершена!**\n\n"
            content += "Спасибо за участие в экономической игре!\n\n"
            content += "━━━━━━━━━━━━━━━━━━━━\n"
            content += "**🏆 Победители:**\n\n"

            # Лидер по капиталу
            if capital_leader:
                content += f"💰 **Капитал**: {capital_leader.get('name', 'Неизвестно')}\n"
                content += f"   Баланс: {capital_leader.get('balance', 0):,} 💵\n\n"
            else:
                content += "💰 **Капитал**: Нет данных\n\n"

            # Лидер по репутации
            if reputation_leader:
                content += f"⭐ **Репутация**: {reputation_leader.get('name', 'Неизвестно')}\n"
                content += f"   Репутация: {reputation_leader.get('reputation', 0)} ⭐\n\n"
            else:
                content += "⭐ **Репутация**: Нет данных\n\n"

            # Лидер по экономической мощи
            if economic_leader:
                content += f"📊 **Экономическая мощь**: {economic_leader.get('name', 'Неизвестно')}\n"
                content += f"   Мощь: {economic_leader.get('economic_power', 0):,} 📈\n\n"
            else:
                content += "📊 **Экономическая мощь**: Нет данных\n\n"

            content += "━━━━━━━━━━━━━━━━━━━━\n"
            content += "\nДо новых встреч! 👋"

            return content
            
        except Exception as e:
            bot_logger.error(f"Ошибка в EndGamePage.content_worker: {e}")
            return f"❌ Ошибка при загрузке данных: {str(e)}"
