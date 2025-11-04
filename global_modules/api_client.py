import asyncio
import websockets
import json
import time
from typing import Callable, Dict, Any, Optional
from os import getenv
import logging
import uuid


class WebSocketClient:
    """
    Простой WebSocket клиент с поддержкой декораторов для обработки сообщений
    """

    def __init__(self, uri: str, client_id: str, logger = None):
        self.uri = uri
        self.client_id = client_id
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.message_handlers: Dict[str, list[Callable]] = {}
        self.logger = logger or logging.getLogger(__name__)

        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None

        # Для ожидания ответов на сообщения
        self.pending_requests: Dict[str, asyncio.Future] = {}

        # Регистрируем базовые обработчики
        self._register_base_handlers()

    def _register_base_handlers(self):
        """Регистрируем базовые обработчики сообщений"""

        @self.on_message("error")
        async def handle_error(data):
            self.logger.error(f"Ошибка от сервера: {data.get('message', '')}")

    def on_message(self, message_type: str):
        """
        Декоратор для регистрации обработчиков сообщений
        
        Пример использования:
        @client.on_message("broadcast")
        async def handle_broadcast(data):
            print(f"Получено broadcast: {data['content']}")
        """
        def decorator(func: Callable):
            if message_type in self.message_handlers:
                self.message_handlers[message_type].append(func)
            else:
                self.message_handlers[message_type] = [func]
            return func
        return decorator

    def on_event(self, event_type: str):
        """
        Декоратор для регистрации обработчиков событий (подключение, отключение)

        Пример использования:
        @client.on_event("connect")
        async def on_connect():
            print("Подключено к серверу")
        """
        def decorator(func: Callable):
            if event_type == "connect":
                self._on_connect = func
            elif event_type == "disconnect":
                self._on_disconnect = func
            return func
        return decorator

    async def connect(self, max_attempts: int = 10, 
                      retry_delay: float = 1) -> bool:
        """
        Подключение к WebSocket серверу с несколькими попытками
        
        Args:
            max_attempts: Максимальное количество попыток подключения
            retry_delay: Задержка между попытками в секундах
        """
        for attempt in range(1, max_attempts + 1):
            try:
                full_uri = f"{self.uri}?client_id={self.client_id}"
                self.logger.info(f"Подключение к {full_uri} (попытка {attempt}/{max_attempts})")

                self.websocket = await websockets.connect(full_uri)
                self.connected = True

                if self._on_connect: 
                    await self._on_connect()

                # Запускаем прослушивание сообщений в фоне
                asyncio.create_task(self._listen_messages())

                self.logger.info(f"Успешно подключен с попытки {attempt}")
                return True

            except Exception as e:
                self.logger.error(f"Ошибка подключения (попытка {attempt}/{max_attempts}): {e}")
                
                if attempt < max_attempts:
                    self.logger.info(f"Ожидание {retry_delay} сек. перед следующей попыткой...")
                    await asyncio.sleep(retry_delay)
                    # Увеличиваем задержку для следующей попытки
                    retry_delay *= 1.5
                else:
                    self.logger.error("Все попытки подключения исчерпаны")
        
        return False

    async def disconnect(self):
        """Отключение от сервера"""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            self.logger.info("Отключен от сервера")

            if self._on_disconnect: await self._on_disconnect()

    async def _listen_messages(self):
        """Прослушивание входящих сообщений"""
        try:
            async for message in self.websocket:
                asyncio.create_task(self._handle_message(message))
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Соединение закрыто сервером")
            self.connected = False
            if self._on_disconnect: await self._on_disconnect()
        except Exception as e:
            self.logger.error(f"Ошибка при прослушивании: {e}")
            self.connected = False

    async def _handle_message(self, message: str):
        """Обработка полученного сообщения"""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            request_id = data.get("request_id")

            # Если это ответ на наш запрос
            if request_id and request_id in self.pending_requests:
                future = self.pending_requests[request_id]
                if not future.done():
                    future.set_result(data)
                del self.pending_requests[request_id]
                return

            # Обычная обработка сообщений
            if message_type in self.message_handlers:
                handlers = self.message_handlers[message_type]
                for handler in handlers:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        asyncio.create_task(asyncio.to_thread(handler, data))
            else:
                self.logger.debug(f"Нет обработчика для типа '{message_type}': {data}")

        except json.JSONDecodeError:
            self.logger.warning(f"Получено не-JSON сообщение: {message}")
        except Exception as e:
            self.logger.error(f"Ошибка обработки сообщения: {e}")

    async def send_message(self, message_type: str, 
                           content: Any = "", 
                           wait_for_response: bool = False, timeout: float = 20.0, 
                           **kwargs) -> Any:
        """
        Отправка сообщения на сервер

        Args:
            message_type: Тип сообщения (ping, broadcast, private, echo)
            content: Содержимое сообщения
            wait_for_response: Ожидать ли ответ от сервера
            timeout: Время ожидания ответа в секундах
            **kwargs: Дополнительные параметры
        """
        if not self.connected or not self.websocket:
            self.logger.error("Нет подключения к серверу")
            return False

        try:
            # Генерируем уникальный ID для запроса если нужен ответ
            request_id = str(uuid.uuid4()) if wait_for_response else None

            message = {
                "type": message_type,
                "content": content,
                "timestamp": time.time(),
                **kwargs
            }

            if request_id:
                message["request_id"] = request_id
                # Создаем Future для ожидания ответа
                future = asyncio.Future()
                self.pending_requests[request_id] = future

            await self.websocket.send(json.dumps(message, ensure_ascii=False))

            if getenv("DEBUG") == 'true':
                self.logger.debug(f"Отправлено: {message_type}")

            # Если не нужен ответ, возвращаем True
            if not wait_for_response:
                return True
 
            # Ждем ответ с таймаутом
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response['data'] if 'data' in response else response

            except asyncio.TimeoutError:
                self.logger.error(f"Таймаут ожидания ответа для {message_type}")
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                return None
            except Exception as e:
                self.logger.error(f"Ошибка ожидания ответа для {message_type}: {e}")

        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return False

    async def ping(self) -> bool: return await self.send_message("ping")

    def is_connected(self) -> bool: return self.connected

    def get_client_id(self) -> str: return self.client_id

# Фабричная функция для создания клиента
def create_client(uri: str = "ws://localhost:81/ws/connect", 
                 client_id: Optional[str] = None,
                 logger = None) -> WebSocketClient:
    """
    Создать WebSocket клиент

    Args:
        uri: URI WebSocket сервера
        client_id: ID клиента (если None, будет сгенерирован)

    Returns:
        WebSocketClient
    """
    if client_id is None:
        client_id = f"client_{int(time.time())}"

    return WebSocketClient(uri, client_id, logger)