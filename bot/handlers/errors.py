"""
Простой обработчик ошибок для бота
"""
from aiogram.types import ErrorEvent
from modules.logs import bot_logger


async def error_handler(event: ErrorEvent):
    """
    Простой обработчик ошибок - логирует все ошибки через bot_logger
    """
    exception = event.exception
    update = event.update
    
    # Основная информация об ошибке
    bot_logger.error(f"Ошибка в боте: {type(exception).__name__}: {str(exception)}")
    
    # Дополнительная информация об обновлении (если есть)
    if update and update.update_id:
        bot_logger.error(f"Update ID: {update.update_id}")
    
    return True