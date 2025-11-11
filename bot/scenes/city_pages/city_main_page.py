from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from modules.ws_client import get_cities, get_session
from modules.utils import do_matrix, do_matrix_7x7_with_large, xy_into_cell


class CityMain(OneUserPage):
    __page_name__ = "city-main-page"
    
    async def data_preparate(self):
        """Кэшируем данные сессии (матрица клеток) и список городов.
        Выполняется один раз за цикл отображения, пока не инвалидировано.
        """
        if self.scene.get_key(self.__page_name__, "select_city_id") is None:
            await self.scene.update_key(self.__page_name__, "select_city_id", None)
        # Кэш сессии (ячейки карты)
        if self.scene.get_key(self.__page_name__, "session_cells") is None:
            session_id = self.scene.get_key("scene", "session")
            session = await get_session(session_id=session_id)
            cells_matrix = do_matrix(session.get("cells")) if session else []
            await self.scene.update_key(self.__page_name__, "session_cells", cells_matrix)
        # Кэш списка городов
        if self.scene.get_key(self.__page_name__, "cities_data") is None:
            session_id = self.scene.get_key("scene", "session")
            cities = await get_cities(session_id=session_id) or []
            await self.scene.update_key(self.__page_name__, "cities_data", cities)
    
    async def buttons_worker(self):
        self.row_width = 7
        buttons = []
        cells_matrix = self.scene.get_key(self.__page_name__, "session_cells") or []
        matrix_cells = do_matrix_7x7_with_large(cells_matrix) if cells_matrix else []
        cities_data = self.scene.get_key(self.__page_name__, "cities_data") or []
        city_ids = [c.get("id") for c in cities_data]
        print(city_ids)
        
        count_city = 0
        # Генерируем карту 7x7
        for x in range(7):
            for y in range(7):
                cell_position = xy_into_cell(y, x)
                
                # Проверяем, есть ли город в этой позиции
                if cell_position in ["B2", "F2", "B6", "F6"]:
                    if cell_position == "B2": 
                        city_id = city_ids[0]
                    elif cell_position == "F2":
                        city_id = city_ids[1]
                    elif cell_position == "B6":
                        city_id = city_ids[2]
                    elif cell_position == "F6":
                        city_id = city_ids[3]
                    buttons.append({
                        'text': '🏢',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__, 
                            'city_select',
                            city_id
                        )
                    })
                    count_city += 1
                # Центральная клетка - банк
                elif cell_position == "D4":
                    buttons.append({
                        'text': '🏦',
                        'callback_data': callback_generator(self.scene.__scene_name__, "noop")
                    })
                # Остальные клетки - показываем координаты
                else:
                    buttons.append({
                        'text': cell_position,
                        'callback_data': callback_generator(self.scene.__scene_name__, "noop")
                    })
        
        return buttons

    @OneUserPage.on_callback("city_select")
    async def city_select(self, callback, args):
        """Выбор города: устанавливаем выбранный id и инвалидируем кэши зависимых страниц."""
        city_id = args[1]
        await self.scene.update_key(self.__page_name__, "select_city_id", city_id)
        # Инвалидация кэшей страницы просмотра города
        await self.scene.update_key("city-view-page", "city_cache", None)
        await self.scene.update_key("city-view-page", "page", 0)
        await self.scene.update_key("city-view-page", "selected_resource", None)
        # Инвалидация кэшей страницы продажи
        await self.scene.update_key("city-sell-page", "company_data", None)
        await self.scene.update_key("city-sell-page", "city_cache", None)
        await self.scene.update_page("city-view-page")