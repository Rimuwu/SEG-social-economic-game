from .main_page import MainPage
from .wait_game_page import WaitStart
from .wait_game_stage_page import WaitGameStagePage
from .end_game_page import EndGamePage
from .prison_page import PrisonPage

__game__ = [
    MainPage,
    WaitStart,
    WaitGameStagePage,
    EndGamePage,
    PrisonPage
]

# GameInfo отдельно, так как импортирует GameManager и вызывает циркулярный импорт
from .game_info_page import GameInfo
__gameinfo__ = [GameInfo]
