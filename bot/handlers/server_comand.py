
import os

from bot_instance import bot
from modules.ws_client import ws_client
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")

# Список ID администраторов
UPDATE_PASSWORD = os.getenv("UPDATE_PASSWORD", "default_password")

GROUP_ID = os.getenv("GROUP_ID", None)

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


async def _format_winners_message(winners: dict, session_id: str) -> str:
    """Форматировать сообщение о победителях"""
    message = f"🏆 Результаты игры {session_id}:\n\n"

    for category, company_data in winners.items():
        if not company_data:
            continue

        category_names = {
            'capital': '💰 По капиталу',
            'reputation': '⭐ По репутации',
            'economic': '📊 По экономической мощи'
        }

        company_name = company_data.get('name', 'Неизвестная компания')
        message += f"{category_names.get(category, category)}: {company_name}\n"

        # Получаем участников компании
        try:
            users_data = company_data.get('users', [])
            if users_data:
                message += "Участники: \n"
                mentions = []
                for user in users_data:
                    mention = await _get_user_mention(user)
                    mentions.append(mention)
                message += "\n- ".join(mentions)
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
    winners_message = await _format_winners_message(winners, session_id)

    # Отправляем сообщение каждому админу
    if GROUP_ID:
        try:
            await bot.send_message(
                GROUP_ID,
                winners_message,
                parse_mode=None
            )
        except Exception as e:
            bot_logger.error(f"Ошибка при отправке сообщения админу {GROUP_ID}: {e}")

        bot_logger.info(f"Сообщение о конце игры {session_id} отправлено")


async def _format_price_difference_message(session_id: str, item_prices: dict, step: int) -> str:
    """Форматировать сообщение о разнице в ценах"""
    message = f"📊 *Изменения цен в сессии {session_id}, за шаг {step}:*\n\n"

    # Считаем изменения
    changes = []
    for item_id, prices in item_prices.items():
        last_price = prices.get('last', 0)
        new_price = prices.get('new', 0)
        item_name = prices.get('name', item_id)  # Используем имя или ID как fallback
        
        if last_price != new_price:
            difference = new_price - last_price
            percentage = (difference / last_price * 100) if last_price > 0 else 0
            
            # Выбираем эмодзи в зависимости от изменения
            if difference > 0:
                emoji = "📈"
                sign = "+"
            else:
                emoji = "📉"
                sign = ""
            
            changes.append({
                'item_id': item_id,
                'item_name': item_name,
                'last_price': last_price,
                'new_price': new_price,
                'difference': difference,
                'percentage': percentage,
                'emoji': emoji,
                'sign': sign
            })
    
    if not changes:
        message += "Цены остались без изменений.\n"
    else:
        # Сортируем по абсолютному значению изменения (самые большие изменения вверху)
        changes.sort(key=lambda x: abs(x['percentage']), reverse=True)
        
        for change in changes:
            message += f"{change['emoji']} *{change['item_name']}*\n"
            message += f"  {change['last_price']} → {change['new_price']} "
            message += f"({change['sign']}{change['difference']}, {change['sign']}{change['percentage']:.1f}%)\n\n"
    
    return message


@ws_client.on_message("api-price_difference")
async def on_price_difference(message: dict):
    data = message.get('data', {})

    session_id = data.get('session_id', 'Неизвестная сессия')
    item_prices = data.get('item_prices', {})
    step = data.get('step', 0)
    
    # Форматируем сообщение о ценах
    price_message = await _format_price_difference_message(session_id, item_prices, step)
    
    # Отправляем сообщение каждому админу
    if GROUP_ID:
        try:
            await bot.send_message(
                GROUP_ID,
                price_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            bot_logger.error(f"Ошибка при отправке сообщения о ценах админу {GROUP_ID}: {e}")
    
        bot_logger.info(f"Сообщение об изменении цен в сессии {session_id} отправлено")