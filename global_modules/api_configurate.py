from fastapi import APIRouter, FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback

def get_fastapi_app(
        title: str,
        version: str,
        description: str,
        debug: bool = False,
        lifespan: any = None,
        routers: list[APIRouter] = None,
        api_logger = None
    ):
    """Создание FastAPI приложения с базовыми настройками"""

    app = FastAPI(
        title=title,
        version=version,
        description=description,
        debug=debug,
        lifespan=lifespan
    )

    if api_logger:
        app.state.logger = api_logger

    for router in routers:
        app.include_router(router)

    return app