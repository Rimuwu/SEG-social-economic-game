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

        users = await get_users(session_id=session_id)       
        flag_name = True
        for i in users:
            if i['username'] == value:
                flag_name = False
                break

        if flag_name:
            await create_user(
                user_id=message.from_user.id,
                username=value,
                session_id=session_id
            )
            await self.scene.update_page('company-option')
        else:
            self.clear_content()
            self.content = self.content.replace("Введите ваше имя для продолжения: ", 
                                                "Данное имя уже занято, введите другое: ")

            await self.scene.update_message()