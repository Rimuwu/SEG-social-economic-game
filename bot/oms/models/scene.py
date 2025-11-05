from typing import Callable, Optional, Type

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from ..fast_page import fast_page
from ..utils import list_to_inline, callback_generator, func_to_str, prepare_image
from ..manager import scene_manager
from .json_scene import scenes_loader, SceneModel
from .page import Page

class Scene:

    __scenes_path__: str = "scenes"
    __scene_name__: str = ''
    __pages__: list[Type[Page]] = [] # Регистрация страниц сцены

    # Функция для вставки сцены в БД
    # В функцию передаёт user_id: int, data: dict
    __insert_function__: Optional[Callable] = None

    # Функция для загрузки сцены из БД
    # В функцию передаёт user_id: int, вернуть должна dict
    __load_function__: Optional[Callable] = None

    # Функция для обновления сцены в БД
    # В функцию передаёт user_id: int, data: dict
    __update_function__: Optional[Callable] = None

    # Функция для удаления сцены из БД
    # В функцию передаёт user_id: int
    __delete_function__: Optional[Callable] = None

    def __init__(self, user_id: int, bot_instance: Bot):
        self.user_id = user_id
        self.message_id: int = 0
        self.__bot__ = bot_instance

        self.scene: SceneModel = scenes_loader.get_scene(
            self.__scene_name__) # type: ignore

        # ВАЖНО: создаём глубокую копию standart_data для каждого пользователя!
        import copy
        self.data: dict = {
            'scene': copy.deepcopy(self.scene.standart_data)
        }

        if not self.scene:
            print(scenes_loader.scenes)
            raise ValueError(f"Сцена {self.__scene_name__} не найдена")

        self.set_pages()
        self.page = self.start_page
        self.data['scene']['last_page'] = self.page

        if not self.scene:
            raise ValueError(f"Сцена {self.__scene_name__} не найдена")

    def __call__(self, *args, **kwargs):
        # self.__init__(*args, **kwargs)
        return self

    async def start(self):
        await self.save_to_db()
        await self.send_message()


    # ===== Работа со страницами =====

    def set_pages(self):
        self.pages = {}
        for page in self.__pages__:
            self.pages[
                page.__page_name__
            ] = page(
                self.scene, this_scene=self
            )

            if page.__page_name__ not in self.data:
                self.data[
                    page.__page_name__
                ] = {
                    'last_button': '',
                    'last_message': ''
                }

        for page in self.scene.pages.keys():
            if page not in self.data:
                self.data[page] = {}

            if page not in self.pages:
                js_type = self.scene.pages[page].type
                page_type = fast_page(js_type, page)

                self.pages[page] = page_type(
                    self.scene, this_scene=self
                    )

    @property
    def start_page(self) -> str:
        if self.scene.settings.start_page:
            return self.scene.settings.start_page
        else:
            return list(self.scene.pages.keys())[0]

    @property
    def current_page(self) -> Page:
        return self.pages.get(self.page, self.standart_page(self.page))

    async def update_page(self, page_name: str):

        if page_name not in self.scene.pages:
            raise ValueError(f"Страница {page_name} не найдена в сцене {self.__scene_name__}")

        page_model: Page = self.pages[page_name]
        status, answer = page_model.page_blocked()
        if status:

            await self.update_key('scene', 'last_page', self.page)
            self.page = page_name

            await self.save_to_db()
            await self.update_message()

        else:
            print(f'Страница {page_name} заблокирована для перехода')

        return status, answer

    def get_page(self, page_name: str):
        if page_name not in self.pages:
            raise ValueError(f"Страница {page_name} не найдена в сцене {self.__scene_name__}")

        return self.pages.get(page_name, None)

    def standart_page(self, page_name: str) -> Page:
        sp = Page(self.scene, self, page_name)
        return sp


    # ===== Работа с сообщениями =====

    async def preparate_message_data(self,
                        only_buttons: bool = False, 
                        raw_buttons: bool = False
                        ):
        page = self.current_page
        await page.data_preparate()

        if not only_buttons:
            text: str = await page.content_worker()
        else: text = page.__page__.content
        
        if self.scene.settings.parse_mode == "Markdown":
            text = self.clear_message_for_markdown(text)

        buttons: list[dict] = await page.buttons_worker()

        if page.enable_topages:
            to_pages: dict[str, str] = page.to_pages

            for i, (page_name, title) in enumerate(
                to_pages.items()):
                buttons.append({
                    'text': title,
                    'callback_data': callback_generator(
                    self.__scene_name__, 
                    'to_page', page_name
                    ),
                    'next_line': len(buttons) > 0 and i == 0
                })

        if not raw_buttons:
            inl_markup = list_to_inline(buttons, page.row_width)
        else:
            inl_markup = buttons

        return text, inl_markup

    async def send_message(self):
        content, markup = await self.preparate_message_data()
        page = self.current_page

        # Проверяем есть ли картинка у страницы
        if hasattr(page, 'image') and page.__page__.image:
            prepared_image = prepare_image(page.__page__.image)
            if prepared_image:
                message = await self.__bot__.send_photo(
                    self.user_id, 
                    prepared_image,
                    caption=content,
                    parse_mode=self.scene.settings.parse_mode,
                    reply_markup=markup
                )
            else:
                print(f"OMS: Не удалось подготовить изображение: {page.__page__.image}")
                message = await self.__bot__.send_message(
                    self.user_id, 
                    content, 
                    parse_mode=self.scene.settings.parse_mode,
                    reply_markup=markup
                )
        else:
            message = await self.__bot__.send_message(
                self.user_id, 
                content, 
                parse_mode=self.scene.settings.parse_mode,
                reply_markup=markup
            )

        self.message_id = message.message_id
        await self.save_to_db()

    def clear_message_for_markdown(self, content: str) -> str:
        symbols = ['*', '_', '`', '~']
        for sym in symbols:
            count = content.count(sym)
            if count % 2 == 1:
                # Находим последний (непарный) символ и заменяем только его
                last_index = content.rfind(sym)
                if last_index != -1:
                    content = content[:last_index] + '#' + content[last_index + 1:]
        return content

    async def update_message(self):
        content, markup = await self.preparate_message_data()
        page = self.current_page

        # Проверяем было ли последнее сообщение с фото
        last_page_name = self.data['scene'].get('last_page', None)
        last_page = self.pages.get(last_page_name, None) if last_page_name else None
        last_have_photo = last_page is not None and last_page.__page__.image is not None

        # Проверяем есть ли фото на новой странице
        has_new_photo = page.__page__.image is not None
        new_photo = page.__page__.image

        # Если раньше было фото, а теперь нет, удаляем сообщение и отправляем новое
        if last_have_photo and not has_new_photo:
            print("OMS: Раньше было фото, а теперь нет, пересоздаем сообщение")
            try:
                await self.__bot__.delete_message(self.user_id, self.message_id)
            except Exception as e: pass
            await self.send_message()
            return

        # Пытаемся обновить сообщение
        try:
            if has_new_photo and new_photo:
                prepared_image = prepare_image(new_photo)
                if prepared_image:
                    await self.__bot__.edit_message_media(
                        chat_id=self.user_id,
                        message_id=self.message_id,
                        media=InputMediaPhoto(
                            media=prepared_image, 
                            caption=content,
                            parse_mode=self.scene.settings.parse_mode
                            ),
                        reply_markup=markup
                    )
                else:
                    print(f"OMS: Не удалось подготовить изображение для обновления: {new_photo}")
                    # Если не удалось подготовить изображение, обновляем как текст
                    await self.__bot__.edit_message_text(
                        chat_id=self.user_id,
                        message_id=self.message_id,
                        text=content,
                        parse_mode=self.scene.settings.parse_mode,
                        reply_markup=markup
                    )
            else:
                await self.__bot__.edit_message_text(
                    chat_id=self.user_id,
                    message_id=self.message_id,
                    text=content,
                    parse_mode=self.scene.settings.parse_mode,
                    reply_markup=markup
                )

        except Exception as e:
            if "message is not modified" in str(e):
                print("OMS: Сообщение не изменилось, пропускаем обновление")
                return

            print(f"OMS: Ошибка при обновлении сообщения: {e}")
            # Если не удалось обновить, пересоздаем сообщение
            try:
                print("OMS: Пересоздаем сообщение")
                try:
                    await self.__bot__.delete_message(self.user_id, self.message_id)
                except Exception as e: pass

                await self.send_message()
            except Exception as delete_error:
                print(f"OMS: Ошибка при пересоздании сообщения: {delete_error}")

    async def update_message_markup(self):
        _, buttons = await self.preparate_message_data(True)
        
        try:
            await self.__bot__.edit_message_reply_markup(
                chat_id=self.user_id,
                message_id=self.message_id,
                reply_markup=buttons
            )
        except Exception as e:
            print(f"OMS: Ошибка при обновлении кнопок: {e}")


    # ===== Работа с БД =====

    def data_to_save(self) -> dict:
        return {
            'user_id': self.user_id,
            'scene': self.__scene_name__,
            'scene_path': func_to_str(self.__class__),
            'page': self.page,
            'message_id': self.message_id,
            'data': self.data
        }

    def update_from_data(self, data: dict) -> None:
        import copy
        self.page = data.get('page', self.start_page)
        self.message_id = data.get('message_id', 0)
        # ВАЖНО: создаём глубокую копию data для каждого пользователя!
        self.data = copy.deepcopy(data.get('data', {'scene': {}}))
        self.scene: SceneModel = scenes_loader.get_scene(
            self.__scene_name__) # type: ignore

    async def save_to_db(self) -> bool:
        if not self.__insert_function__ or not self.__update_function__:
            return False

        if self.__load_function__:
            exist = await self.__load_function__(self.user_id)
            if not exist:
                await self.__insert_function__(user_id=self.user_id, data=self.data_to_save())
            else:
                await self.__update_function__(user_id=self.user_id, data=self.data_to_save())
        return True

    async def load_from_db(self, update_page: bool) -> bool:
        if not self.__load_function__:
            return False

        data = await self.__load_function__(user_id=self.user_id)
        if not data:
            return False

        self.update_from_data(data)
        if update_page:
            await self.update_message()
        return True


    # ===== Обработчики событий и страниц =====

    async def text_handler(self, message: Message) -> None:
        """Обработчик текстовых сообщений"""
        page = self.current_page
        await page.text_handler(message)

        if self.scene.settings.delete_after_send:
            print("Delete message after send")
            try:
                await self.__bot__.delete_message(
                    self.user_id, message.message_id
                )
            except Exception as e: pass

        await self.update_key(page.__page_name__, 'last_message', message.text)
        await page.post_handle('text')

    async def callback_handler(self, 
                callback: CallbackQuery, args: list) -> None:
        """Обработчик колбэков"""
        page = self.current_page
        await page.callback_handler(callback, args)

        await self.update_key(page.__page_name__, 'last_button', callback.data)
        await page.post_handle('button')


    # ===== Работа с данными сцены и страниц =====

    def get_data(self, element: str) -> Optional[dict]:
        """ Получение данных элемента

            Элементы - это страницы или сцена, то есть либо 'scene', либо название страницы
        """

        if element in self.data: return self.data[element]
        return None

    async def set_data(self, element: str, value: dict) -> bool:
        """ Установка данных элемента (полная перезапись)
        """

        if element in self.data:
            self.data[element] = value
            await self.save_to_db()
            return True
        return False

    async def update_key(self, element: str, key: str, 
                         value) -> bool:
        """ Обновление ключа в данных элемента
            Если ключа нет, он будет создан
            Аккуратно, value должен быть сериализуемым в JSON
        """
        if element in self.data:
            if key in self.data[element]:
                self.data[element][key] = value
            else:
                self.data[element][key] = value
            await self.save_to_db()
            return True
        return False

    def get_key(self, element: str, key: str):
        """ Получение ключа из данных элемента
        """
        if element in self.data:
            return self.data[element].get(key, None)
        return None


    # ==== Конец сцены ====

    async def end(self):
        try:
            await self.__bot__.delete_message(
                self.user_id, self.message_id
            ) 
        except Exception as e: pass

        scene_manager.remove_scene(self.user_id)
        if self.__delete_function__:
            await self.__delete_function__(self.user_id)