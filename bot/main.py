import asyncio
import logging

from global_modules.logs import Logger

from modules.db import db
from modules.ws_client import ws_client
from bot_instance import bot, dp

from oms import register_handlers
from handlers.errors import error_handler

# Настройка логирования
bot_logger = Logger.get_logger("bot")
logging.basicConfig(level=logging.INFO)


async def main():
    """Главная функция для запуска бота"""
    bot_logger.info("Запуск бота...")

    await db.connect()  # Подключаемся к базе данных
    await db.create_table('scenes')

    # Регистрируем обработчик ошибок
    dp.error.register(error_handler)
    register_handlers(dp)

    try:
        await ws_client.connect() # Подключаемся к WebSocket серверу
        await dp.start_polling(bot)
    finally:
        await ws_client.disconnect() # Отключаемся от сервера
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())