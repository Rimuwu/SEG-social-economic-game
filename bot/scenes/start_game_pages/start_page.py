from oms import Page
from aiogram.types import Message
from modules.ws_client import get_session

class Start(Page):

    __page_name__ = 'start'

    @Page.on_text('str')
    async def on_str(self, message: Message, value: str) -> None:
        """ Обработка и получение сообщения на странице
        """
        self.clear_content()
        response = await get_session(value)

        if not response:
            self.content = self.content.replace("Введиие код для подключения к игровой сессии: ", 
                                                "Неверный код, введите код заново: ")
            await self.scene.update_page(self.__page_name__)

        elif response.get("stage") != "FreeUserConnect":
            self.content = self.content.replace("Введиие код для подключения к игровой сессии: ", 
                                                "Сессия в процессе игры, введите другой код: ")
            await self.scene.update_page(self.__page_name__)
        else:

            await self.scene.update_key(
                'scene',
                'session',
                value
            )
            await self.scene.update_page(
                'name-enter'
            )