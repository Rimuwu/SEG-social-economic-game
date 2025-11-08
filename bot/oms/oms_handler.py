from typing import Union
from aiogram.types import Message, CallbackQuery
from aiogram import Dispatcher

from .utils import CALLBACK_PREFIX
from .manager import scene_manager
from aiogram import F, Router
from logging import getLogger
from .filters.scene_filter import InScene

logger = getLogger(__name__)

def register_handlers(router: Union[Router, Dispatcher]):

    @router.message(InScene())
    async def on_message(message: Message):
        user_id = message.from_user.id
        scene = scene_manager.get_scene(user_id)
        if message.chat.id != user_id: return

        logger.info(
            f'on_message\nscene: {scene}\nmessage: {message.text}'
        )

        if scene:
            await scene.text_handler(message)

    @router.callback_query(
        InScene(),
        F.data.split(":")[:2] == [CALLBACK_PREFIX, 'to_page']
                    )
    async def to_page(callback: CallbackQuery):
        user_id = callback.from_user.id
        user_session = scene_manager.get_scene(user_id)

        prefix, c_type, scene_name, *args = callback.data.split(':')
        to_page = args[0]

        if user_session:
            status, answer = await user_session.update_page(to_page)
            if not status:
                await callback.answer(answer, show_alert=True)

    @router.callback_query(
        InScene(),
        F.data.split(":")[0] == CALLBACK_PREFIX)
    async def on_callback_query(callback: CallbackQuery):
        user_id = callback.from_user.id
        user_session = scene_manager.get_scene(user_id)

        prefix, c_type, scene_name, *args = callback.data.split(':')

        if user_session:
            # Передаем c_type как первый элемент args, остальные аргументы следом
            callback_args = [c_type] + args
            await user_session.callback_handler(callback, callback_args)