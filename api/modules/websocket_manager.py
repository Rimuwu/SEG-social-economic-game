from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
import json
from modules.logs import websocket_logger

class WebSocketManager:
    """Менеджер для управления WebSocket соединениями"""

    def __init__(self):
        # Словарь активных соединений {client_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        Подключить новое WebSocket соединение

        Args:
            websocket: WebSocket соединение
            client_id: Уникальный ID клиента

        Returns:
            bool: True если подключение успешно, False если клиент уже подключен
        """
        try:
            await websocket.accept()

            # Если клиент уже подключен, отключаем старое соединение
            if client_id in self.active_connections:
                await self.disconnect(client_id)

            self.active_connections[client_id] = websocket
            websocket_logger.info(f"WebSocket подключение установлено для клиента: {client_id}")
            return True

        except Exception as e:
            websocket_logger.error(f"Ошибка при подключении WebSocket для {client_id}: {e}")
            return False

    async def disconnect(self, client_id: str) -> bool:
        """
        Отключить WebSocket соединение

        Args:
            client_id: ID клиента для отключения

        Returns:
            bool: True если отключение успешно
        """
        try:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                try:
                    await websocket.close()
                except:
                    pass  # Соединение уже может быть закрыто

                del self.active_connections[client_id]
                websocket_logger.info(f"WebSocket соединение закрыто для клиента: {client_id}")
                return True

            websocket_logger.warning(f"Попытка отключить несуществующее соединение: {client_id}")
            return False

        except Exception as e:
            websocket_logger.error(f"Ошибка при отключении WebSocket для {client_id}: {e}")
            return False

    async def send_message(self, client_id: str, message: Any, log: bool = True) -> bool:
        """
        Отправить сообщение конкретному клиенту

        Args:
            client_id: ID клиента
            message: Сообщение (словарь, строка или любой JSON-сериализуемый объект)
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            if client_id not in self.active_connections:
                websocket_logger.warning(f"Попытка отправить сообщение несуществующему клиенту: {client_id}")
                return False

            websocket = self.active_connections[client_id]

            # Конвертируем сообщение в JSON если это не строка
            if isinstance(message, str):
                await websocket.send_text(message)
            else:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))

            if log:
                websocket_logger.info(f"Sent message to {client_id}")

            return True

        except WebSocketDisconnect:
            websocket_logger.warning(f"Клиент {client_id} отключился")
            await self.disconnect(client_id)
            return False
        except Exception as e:
            websocket_logger.error(f"Ошибка при отправке сообщения клиенту {client_id}: {e}\nmessage: {message}")
            # await self.disconnect(client_id)
            return False

    async def broadcast(self, message: Any, 
                        exclude: List[str] = None) -> int:
        """
        Отправить сообщение всем подключенным клиентам

        Args:
            message: Сообщение для отправки
            exclude: Список ID клиентов, которых нужно исключить

        Returns:
            int: Количество клиентов, которым успешно доставлено сообщение
        """
        exclude = exclude or []
        success_count = 0

        # Создаем копию списка клиентов, чтобы избежать изменения во время итерации
        clients = list(self.active_connections.keys())

        for client_id in clients:
            if client_id not in exclude:
                if await self.send_message(client_id, message, False):
                    success_count += 1

        websocket_logger.info(
            f"Broadcast ({message['type']}) for {success_count} clients")
        return success_count

    def get_connected_clients(self) -> List[str]:
        """
        Получить список ID всех подключенных клиентов

        Returns:
            List[str]: Список ID клиентов
        """
        return list(self.active_connections.keys())

    def is_connected(self, client_id: str) -> bool:
        """
        Проверить, подключен ли клиент

        Args:
            client_id: ID клиента

        Returns:
            bool: True если клиент подключен
        """
        return client_id in self.active_connections

    def get_connection_count(self) -> int:
        """
        Получить количество активных соединений

        Returns:
            int: Количество активных соединений
        """
        return len(self.active_connections)


# Глобальный экземпляр менеджера
websocket_manager = WebSocketManager()