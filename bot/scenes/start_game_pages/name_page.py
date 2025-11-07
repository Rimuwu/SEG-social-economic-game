from oms import Page
from aiogram.types import Message
from modules.ws_client import create_user, get_users

class UserName(Page):

    __page_name__ = 'name-enter'

    @Page.on_text('str')
    async def on_str(self, message: Message, value: str) -> None:
        """ Обработка и получение сообщения на странице
        """

        scene_data = self.scene.get_data('scene')
        session_id = scene_data['session']

        res = await create_user(
            user_id=message.from_user.id,
            username=value,
            session_id=session_id
        )
        if "error" in res:
            self.clear_content()
            self.content = self.content.replace("Введите ваше имя для продолжения: ", 
                                                res["error"])

            await self.scene.update_message()
        else:
            await self.scene.update_page('company-option')