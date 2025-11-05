"""
Модуль страниц биржи
Содержит все страницы, связанные с функционалом биржи
"""

from .exchange_main import ExchangeMain
from .exchange_filter import ExchangeFilter
from .exchange_sellect_comfirm import ExchangeSellectConfirm
from .exhcange_create import ExchangeCreate
from .exchange_create_pages.set_sell_resource import ExchangeCreateSetSell
from .exchange_create_pages.set_barter_resource import ExchangeCreateSetBarter


__exchange__ = [
    ExchangeMain,
    ExchangeFilter,
    ExchangeSellectConfirm,
    ExchangeCreate,
    ExchangeCreateSetSell,
    ExchangeCreateSetBarter,
]
