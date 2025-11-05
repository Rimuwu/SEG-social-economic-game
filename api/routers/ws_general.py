

from modules.websocket_manager import websocket_manager
from modules.ws_hadnler import message_handler
from modules.logs import websocket_logger

@message_handler(
    "ping", 
    doc="Обработчик ping сообщений. Отправляет pong в ответ.", 
    datatypes=["timestamp: str", "content: Any"])
async def handle_ping(client_id: str, message: dict):
    """Обработчик ping сообщений"""
    pong_message = {
        "type": "pong",
        "timestamp": message.get("timestamp", ""),
        "client_id": client_id,
        "content": message.get("content", "Pong!")
    }

    await websocket_manager.send_message(client_id, pong_message)
    websocket_logger.debug(f"Отправлен pong клиенту {client_id}")