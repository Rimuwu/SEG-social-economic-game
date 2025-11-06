from .admin_panel_page import AdminPanelPage
from .admin_session_main_page import AdminSessionMainPage
from .admin_session_page import SessionAdd, SessionDell, SessionInfo, SessonChangeStage
from .admin_main_page import AdminMainPage

__admin__ = [
    AdminSessionMainPage,
    SessionAdd, SessionDell, SessionInfo,
    SessonChangeStage
]
