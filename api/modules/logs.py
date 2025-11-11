from global_modules.logs import Logger
from os import getenv

game_logger = Logger().get_logger("game")
routers_logger = Logger().get_logger("routers")
websocket_logger = Logger().get_logger("websocket")

if getenv('DEBUG') == 'true':
    websocket_logger.setLevel("WARNING")
    routers_logger.setLevel("WARNING")