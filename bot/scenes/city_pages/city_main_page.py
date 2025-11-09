from scenes.utils.oneuser_page import OneUserPage
from oms.utils import callback_generator
from modules.ws_client import get_cities, get_session
from modules.utils import do_matrix, do_matrix_7x7_with_large, xy_into_cell, do_cell_emoji


class CityMain(OneUserPage):
    __page_name__ = "city-main-page"
    
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "select_city_id") is None:
            await self.scene.update_key(self.__page_name__, "select_city_id", None)
    
    async def buttons_worker(self):
        self.row_width = 7
        buttons = []
        session_id = self.scene.get_key("scene", "session")
        session = await get_session(session_id=session_id)
        matrix_cells = do_matrix_7x7_with_large(do_matrix(session.get("cells")))
        # Получаем список городов
        cities_data = await get_cities(session_id=session_id)
        city_ids = []
        # {(x, y): city}
        for c in cities_data:
            city_ids.append(c.get("id"))
        
        count_city = 0
        # Генерируем карту 7x7
        for x in range(7):
            for y in range(7):
                cell_position = xy_into_cell(x, y)
                
                # Проверяем, есть ли город в этой позиции
                if cell_position in ["B2", "B6", "F2", "F6"]:
                    buttons.append({
                        'text': '🏢',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__, 
                            'city_select',
                            city_ids[count_city]
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
        """Выбор города"""
        city_id = args[1]
        await self.scene.update_key(self.__page_name__, "select_city_id", city_id)
        await self.scene.update_page("city-view-page")