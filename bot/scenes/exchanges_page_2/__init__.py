"""
Модуль биржи - разделённый на отдельные файлы
"""

from .exchange_main import ExchangeMain
from .exchange_details import ExchangeDetails
from .exchange_filter import ExchangeFilter
from .exchange_create import (
    ExchangeCreateMain,
    ExchangeCreateSetSell,
    ExchangeCreateSetBarter
)
from .exchange_update import ExchangeUpdate

# Список всех страниц для экспорта
__exchange__ = [
    # Основные страницы
    ExchangeMain,
    ExchangeDetails,
    ExchangeFilter,
    
    # Страницы создания предложения
    ExchangeCreateMain,
    ExchangeCreateSetSell,
    ExchangeCreateSetBarter,
    
    # Страница обновления предложения
    ExchangeUpdate,
]

__all__ = [
    'ExchangeMain',
    'ExchangeDetails',
    'ExchangeFilter',
    'ExchangeCreateMain',
    'ExchangeCreateSetSell',
    'ExchangeCreateSetBarter',
    'ExchangeUpdate',
    '__exchange__',
]
