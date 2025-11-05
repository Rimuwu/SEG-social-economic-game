# Реестр обработчиков сообщений
from typing import Callable, Dict, List, Union
from modules.websocket_manager import websocket_manager
from modules.logs import websocket_logger
from modules.logs import routers_logger
import traceback

MESSAGE_HANDLERS: Dict[str, dict[str, Union[Callable, str]]] = {}

def message_handler(message_type: str, 
                    doc: str = "", 
                    datatypes: list[str] = [],
                    messages: list[str] = []
                    ):
    """
    Декоратор для регистрации обработчиков сообщений

    Пример использования:
    @message_handler("ping")
    async def handle_ping(client_id: str, message: dict):
        # обработка ping сообщений
        pass
    
    Args:
        message_type: Тип сообщения, который будет обрабатываться
        doc: Описание обработчика
        datatypes: Список типов данных, которые ожидает обработчик [user_id: int, action: Optional[str], ...]
        messages: На какие типы сообщений отправляет ответ при обработке
    """
    def decorator(func: Callable):
        MESSAGE_HANDLERS[message_type] = {
            "handler": func, "doc": doc,
            "datatypes": datatypes,
            "messages": messages
            }
        websocket_logger.info(f"Зарегистрирован обработчик для типа сообщения: {message_type}")
        return func
    return decorator

async def handle_message(client_id: str, message: dict):
    """
    Обработчик входящих сообщений от клиентов через систему декораторов
    
    Args:
        client_id: ID клиента, отправившего сообщение
        message: Сообщение от клиента
    """
    message_type = message.get("type", "unknown")

    # Ищем зарегистрированный обработчик
    if message_type in MESSAGE_HANDLERS:
        try:
            routers_logger.info(f"Обработка сообщения типа {message_type} от клиента {client_id}")

            handler = MESSAGE_HANDLERS[message_type]["handler"]
            result = await handler(client_id, message)

            if 'request_id' in message:
                # Если есть request_id, отправляем ответ
                response = {
                    "type": "response",
                    "request_id": message["request_id"],
                    "data": result
                }
                routers_logger.info(f"Отправка ответа на request_id {message['request_id']} клиенту {client_id}")
                await websocket_manager.send_message(client_id, response)

        except Exception as e:
            print(traceback.format_exc())
            websocket_logger.error(f"Ошибка в обработчике {message_type}: {e}\n{traceback.format_exc()}")
            error_message = {
                "type": "error",
                "message": f"Ошибка обработки сообщения типа {message_type}: {str(e)}",
                "error": str(e)
            }
            await websocket_manager.send_message(client_id, error_message)
            routers_logger.error(
                f"Ошибка в роутере {message_type} для клиента {client_id}: {error_message}")

    else:
        # Неизвестный тип сообщения
        websocket_logger.warning(f"Неизвестный тип сообщения от {client_id}: {message_type}")

        available_types = []
        for m_type in MESSAGE_HANDLERS.keys():
            available_types.append(m_type)

        error_message = {
            "type": "error",
            "message": f"Неизвестный тип сообщения: {message_type}",
            "available_types": available_types
        }
        await websocket_manager.send_message(client_id, error_message)

# Функция для получения списка зарегистрированных обработчиков
def get_registered_handlers():
    """Получить список всех зарегистрированных типов сообщений"""
    return MESSAGE_HANDLERS