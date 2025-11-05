from oms import Page
from aiogram.types import Message
from modules.ws_client import create_company, get_companies, get_company

class CompanyCreate(Page):

    __page_name__ = 'company-create'

    @Page.on_text('str')
    async def on_text(self, message: Message, value: str) -> None:
        """ Обработка и получение сообщения на странице
        """
        company_name = value.strip()

        if not company_name:
            self.clear_content()
            self.content = self.content.replace("Введите название компании: ", "❌ Название не может быть пустым. Введите название компании: ")
            await self.scene.update_message()
            return

        # Получаем данные сессии
        scene_data = self.scene.get_data('scene')
        session_id = scene_data['session']

        # Проверяем, не существует ли уже компания с таким именем в этой сессии
        existing_companies = await get_companies(session_id=session_id)
        for company in existing_companies or []:
            if company.get('name', '').lower() == company_name.lower():
                self.content = self.__page__.content
                self.content = self.content.replace("Введите название компании: ", f"❌ Компания '{company_name}' уже существует. Введите другое название: ")
                await self.scene.update_message()
                return

        try:
            # Создаем компанию
            response = await create_company(
                name=company_name,
                who_create=message.from_user.id
            )

            if response and response.get('company'):
                # Сохраняем данные компании в сцене
                await self.scene.update_key(
                    'scene',
                    'company_id',
                    response['company']["id"]
                )

                # Переходим на страницу ожидания игры
                await self.scene.update_page('wait-start-page')
            else:
                error_message = response.get('error', 'Неизвестная ошибка') if response else 'Нет ответа от сервера'
                self.clear_content()
                self.content = self.content.replace("Введите название компании: ", f"❌ Ошибка создания: {error_message}. Попробуйте снова: ")
                await self.scene.update_message()

        except Exception as e:
            self.clear_content()
            self.content = self.content.replace("Введите название компании: ", f"❌ Ошибка: {str(e)}. Попробуйте снова: ")
            await self.scene.update_message()