from oms import Page
from aiogram.types import Message
from modules.ws_client import update_company_add_user, get_company, get_users
from modules.utils import update_page


class CompanyJoin(Page):

    __page_name__ = 'company-join'
    
    
    @Page.on_text('str')
    async def on_str(self, message: Message, value: str) -> None:
        self.clear_content()
        self.content = self.content.replace("Введите секретный код: ", 
                                            "❌ Код должен состоять только из цифр. Введите секретный код: ")
        await self.scene.update_message()


    @Page.on_text('int')
    async def on_int(self, message: Message, value: int) -> None:
        """ Обработка и получение сообщения на странице
        """

        # Получаем данные сессии
        scene_data = self.scene.get_data('scene')
        session_id = scene_data['session']

        # Пытаемся присоединиться к компании
        response = await update_company_add_user(
            user_id=message.from_user.id,
            secret_code=value
        )
        if response is not None and response.get('error'):
            self.clear_content()
            self.content = self.content.replace("Введите секретный код: ", 
                                                f"❌ Ошибка: {response.get('error')}. Попробуйте снова: ")
            await self.scene.update_message()
            return

        # После успешного присоединения получаем данные компании
        # Ищем компании в сессии и находим нужную по пользователю

        users = await get_users(session_id=session_id)
        user_company_id = None

        for user in users or []:
            if user.get('id') == message.from_user.id:
                user_company_id = user.get('company_id')
                break

        if user_company_id:
            company_data = await get_company(id=user_company_id)
            if company_data:
                # Сохраняем данные компании в сцене
                await self.scene.update_key(
                    'scene',
                    'company_id',
                    company_data.get('id')
                )
        else:
            # Если не удалось найти компанию, показываем ошибку
            self.clear_content()
            self.content = self.content.replace("Введите секретный код: ", 
                                                "❌ Не удалось найти вашу компанию. Попробуйте снова: ")
            await self.scene.update_message()
            return

        await update_page(
            user_company_id=user_company_id,
            user_id=message.from_user.id,
            page_name='wait-start-page'
        )
        
        
        # Переходим на главную страницу
        await self.scene.update_page('wait-start-page')