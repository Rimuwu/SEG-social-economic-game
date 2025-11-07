from oms import Page
from aiogram.types import Message, CallbackQuery
from modules.utils import update_page, cell_into_xy, xy_into_cell
from modules.ws_client import get_sessions_free_cells, set_company_position, get_session
from oms.utils import callback_generator


class SelectCell(Page):
    
    __page_name__ = 'select-cell-page'
    
    row_width = 7
    
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, 'camera_x') is None:
            await self.scene.update_key(self.__page_name__, 'camera_x', 0)
        if self.scene.get_key(self.__page_name__, 'camera_y') is None:
            await self.scene.update_key(self.__page_name__, 'camera_y', 0)
   
    async def buttons_worker(self):
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('session')

        s = await get_session(session_id=session_id)
        map_size = s.get("map_size", {})
        total_rows = map_size.get("rows", 7)
        total_cols = map_size.get("cols", 7)

        free_cells = await get_sessions_free_cells(session_id=session_id)
        free_coords = set()
        if free_cells and "free_cells" in free_cells:
            for cell in free_cells["free_cells"]:
                free_coords.add((cell[0], cell[1]))

        camera_x = self.scene.get_key(self.__page_name__, 'camera_x') or 0
        camera_y = self.scene.get_key(self.__page_name__, 'camera_y') or 0
        view_size = 7
        center_row = total_rows // 2
        center_col = total_cols // 2
        
        buttons = []
        self.row_width = 7
        for row in range(view_size):
            for col in range(view_size):
                real_row = camera_y + row
                real_col = camera_x + col
                if real_row < 0 or real_row >= total_rows or real_col < 0 or real_col >= total_cols:
                    buttons.append({
                        'text': '⬛',
                        'callback_data': 'out_of_bounds'
                    })
                    continue
                
                cell_text = xy_into_cell(real_col, real_row)
                if real_row == center_row and real_col == center_col:
                    buttons.append({
                        'text': '🏦',
                        'callback_data': 'bank'
                    })
                elif (real_row == center_row - 2 and real_col == center_col - 2) or \
                     (real_row == center_row - 2 and real_col == center_col + 2) or \
                     (real_row == center_row + 2 and real_col == center_col - 2) or \
                     (real_row == center_row + 2 and real_col == center_col + 2):
                    buttons.append({
                        'text': '🏢',
                        'callback_data': 'city'
                    })
                elif (real_row, real_col) in free_coords:
                    buttons.append({
                        'text': f"{cell_text}",
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'cell_select',
                            cell_text
                        )
                    })
                else:
                    buttons.append({
                        'text': '❌',
                        'callback_data': 'occupied'
                    })
        
        can_move_up = camera_y > 0
        can_move_down = camera_y + view_size < total_rows
        can_move_left = camera_x > 0
        can_move_right = camera_x + view_size < total_cols
        if total_rows > 7:
            buttons.append({'text': ' ', 'callback_data': 'empty', "next_line": True})
            buttons.append({
                'text': '⬆️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'move', 'up') if can_move_up else 'no_move'
            })
            buttons.append({'text': ' ', 'callback_data': 'empty'})

            
            buttons.append({
                'text': '⬅️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'move', 'left') if can_move_left else 'no_move',
                "next_line": True
            })
            buttons.append({'text': ' ', 'callback_data': 'center'})
            buttons.append({
                'text': '➡️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'move', 'right') if can_move_right else 'no_move'
            })
        
        
            buttons.append({'text': ' ', 'callback_data': 'empty', "next_line": True})
            buttons.append({
                'text': '⬇️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'move', 'down') if can_move_down else 'no_move'
            })
            buttons.append({'text': ' ', 'callback_data': 'empty'})
        
        return buttons
    
    @Page.on_callback('move')
    async def move_camera_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer()
            return
        
        direction = args[1]
        camera_x = self.scene.get_key(self.__page_name__, 'camera_x') or 0
        camera_y = self.scene.get_key(self.__page_name__, 'camera_y') or 0
        
        if direction == 'up':
            camera_y = max(0, camera_y - 1)
        elif direction == 'down':
            camera_y += 1
        elif direction == 'left':
            camera_x = max(0, camera_x - 1)
        elif direction == 'right':
            camera_x += 1
        
        await self.scene.update_key(self.__page_name__, 'camera_x', camera_x)
        await self.scene.update_key(self.__page_name__, 'camera_y', camera_y)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('cell_select')
    async def my_callback_handler(self, callback: CallbackQuery, args: list):       
        cell_name = args[1] if len(args) > 1 else None
        if cell_name:
            y, x = cell_into_xy(cell_name)
            data = self.scene.get_data('scene')
            company_id = data.get('company_id')
            response = await set_company_position(company_id=company_id, x=x, y=y)
            
            if "error" in response:
                self.content = "Данная клетка уже занята, выберите другую:"
                await self.scene.update_message()
                return
            await self.scene.update_page("wait-game-stage-page")