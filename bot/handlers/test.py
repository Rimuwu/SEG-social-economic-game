from oms import scene_manager
from bot_instance import dp, bot
from aiogram.filters import Command
from aiogram.types import Message
from scenes.start_scenario import StartManager
from scenes.admin_scenario import AdminManager
from filters.admins import AdminFilter 

@dp.message(Command('start'))
async def test(message: Message):
    scene = scene_manager.create_scene(
        message.from_user.id,
        StartManager,
        bot
    )
    await scene.start()


@dp.message(AdminFilter, Command('admin'))
async def admin_panel(message: Message):
    scene = scene_manager.create_scene(
        message.from_user.id,
        AdminManager,
        bot
    )
    await scene.start()