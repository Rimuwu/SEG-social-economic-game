
from oms.manager import SceneManager
from modules.db import db
from bot_instance import bot

async def load_scenes_from_db(manager: SceneManager):

    results = await db.find('scenes')
    for result in results:
        manager.load_scene_from_db(
            result['user_id'],
            result['scene_path'],
            result['page'],
            result['message_id'],
            result['data'],
            bot,
            False
        )