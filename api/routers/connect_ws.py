from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse
import json

from modules.ws_hadnler import get_registered_handlers, handle_message
from modules.websocket_manager import websocket_manager
from modules.logs import websocket_logger

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(..., description="Уникальный ID клиента")
):
    """
    WebSocket эндпоинт для подключения клиентов
    
    Args:
        websocket: WebSocket соединение
        client_id: Уникальный идентификатор клиента
    """
    connection_successful = await websocket_manager.connect(websocket, client_id)
    
    if not connection_successful:
        await websocket.close(code=1000, reason="Ошибка подключения")
        return
    
    try:
        # Основной цикл получения сообщений
        while True:
            try:
                # Ожидаем сообщение от клиента
                data = await websocket.receive_text()
                websocket_logger.info(f"Получено сообщение от {client_id}: {data}")

                try:
                    # Пытаемся распарсить JSON
                    message = json.loads(data)
                except json.JSONDecodeError:
                    # Если не JSON, обрабатываем как текст
                    message = {"type": "text", "content": data}
                
                # Обработка различных типов сообщений
                await handle_message(client_id, message)

            except WebSocketDisconnect:
                websocket_logger.info(f"Клиент {client_id} отключился")
                break

            except Exception as e:
                websocket_logger.error(f"Ошибка при обработке сообщения от {client_id}: {e}")
                error_message = {
                    "type": "error",
                    "message": f"Ошибка обработки сообщения: {str(e)}"
                }
                await websocket_manager.send_message(client_id, error_message)

    finally:
        # Отключаем клиента
        await websocket_manager.disconnect(client_id)

@router.get("/status")
async def get_websocket_status():
    """
    Получить статус WebSocket соединений
    
    Returns:
        dict: Информация о текущих соединениях
    """
    try:
        connected_clients = websocket_manager.get_connected_clients()
        connection_count = websocket_manager.get_connection_count()

        available_types = []
        for m_type, info in get_registered_handlers().items():
            available_types.append({
                "type": m_type
            })

            if info.get("doc"):
                available_types[-1]["description"] = info["doc"]

            if not info.get("datatypes"):
                available_types[-1]["args"] = "Нет аргументов"

            elif len(info["datatypes"]) > 0:
                available_types[-1]["args"] = ', '.join(info.get("datatypes", []))

            if info.get("messages") and len(info["messages"]) > 0:
                available_types[-1]["responses"] = info.get("messages", [])
            else:
                available_types[-1]["responses"] = "Не отправляет никакие сообщения. (Не учитывается работа с request_id)"

        return JSONResponse({
            "status": "ok",
            "total_connections": connection_count,
            "connected_clients": connected_clients,
            "server_status": "running",
            "supported_message_types": available_types
        })

    except Exception as e:
        websocket_logger.error(f"Ошибка при получении статуса WebSocket: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")


@router.get("/connections")
async def get_connections():
    try:
        connected_clients = websocket_manager.get_connected_clients()
        connection_count = websocket_manager.get_connection_count()

        return JSONResponse({
            "status": "ok",
            "total_connections": connection_count,
            "connected_clients": connected_clients,
            "server_status": "running",
        })
    
    except Exception as e:
        websocket_logger.error(f"Ошибка при получении статуса WebSocket: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")