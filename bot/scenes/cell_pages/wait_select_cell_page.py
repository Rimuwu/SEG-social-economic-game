from oms import Page
from modules.ws_client import get_company
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class WaitSelectCellPage(Page):
    __page_name__ = "wait-select-cell-page"
