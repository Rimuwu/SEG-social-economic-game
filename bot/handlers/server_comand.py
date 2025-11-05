
import os

from bot_instance import dp, bot
from modules.ws_client import ws_client
from global_modules.logs import Logger

# Логгер
bot_logger = Logger.get_logger("bot")

# Список ID администраторов
UPDATE_PASSWORD = os.getenv("UPDATE_PASSWORD", "default_password")

ADMIN_IDS = [admin_id.strip(
    ) for admin_id in os.getenv("ADMIN_IDS", 
                                "").strip().split(",") if admin_id.strip()]


async def _get_user_mention(user: dict) -> str:
    """Получить @упоминание пользователя или ссылку на него"""
    user_id = user.get('id', 0)
    
    if not user_id:
        return "Неизвестный пользователь"
    
    try:
        # Получаем информацию о пользователе из Telegram
        chat_member = await bot.get_chat_member(user_id, user_id)
        tg_user = chat_member.user
        
        # Если есть username - используем его
        if tg_user.username:
            return f"@{tg_user.username} ({user['username']})"
        # Иначе создаем ссылку с ФИ или ID
        elif tg_user.first_name:
            name = tg_user.first_name
            if tg_user.last_name:
                name += f" {tg_user.last_name}"
            return f"[{name}](tg://user?id={user_id}) ({user['username']})"
        else:
            return f"[{user_id}](tg://user?id={user_id}) ({user['username']})"

    except Exception as e:
        bot_logger.error(f"Ошибка при получении данных пользователя {user_id}: {e}")
        # Fallback на ссылку если не удалось получить данные
        return f"[{user_id}](tg://user?id={user_id})"


async def _format_winners_message(winners: dict) -> str:
    """Форматировать сообщение о победителях"""
    message = "🏆 *Результаты игры:*\n\n"
    
    for category, company_data in winners.items():
        if not company_data:
            continue
            
        category_names = {
            'capital': '💰 По капиталу',
            'reputation': '⭐ По репутации',
            'economic': '📊 По экономической мощи'
        }
        
        company_name = company_data.get('name', 'Неизвестная компания')
        message += f"{category_names.get(category, category)}: *{company_name}*\n"
        
        # Получаем участников компании
        try:
            users_data = company_data.get('users', [])
            if users_data:
                message += "Участники: "
                mentions = []
                for user in users_data:
                    mention = await _get_user_mention(user)
                    mentions.append(mention)
                message += ", ".join(mentions) + "\n"
        except Exception as e:
            bot_logger.error(f"Ошибка при получении участников компании: {e}")
        
        message += "\n"
    
    return message


@ws_client.on_message("api-game_ended")
async def on_company_to_prison(message: dict):
    data = message.get('data', {})
    
    session_id = data['session_id']
    winners = data['winners']
    
    # Форматируем сообщение о победителях
    winners_message = await _format_winners_message(winners)
    
    # Отправляем сообщение каждому админу
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                int(admin_id),
                winners_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            bot_logger.error(f"Ошибка при отправке сообщения админу {admin_id}: {e}")
    
    bot_logger.info(f"Сообщение о конце игры {session_id} отправлено {len(ADMIN_IDS)} администраторам")


