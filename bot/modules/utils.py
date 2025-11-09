from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from modules.ws_client import get_users, get_company, get_companies
from oms import scene_manager
from oms.utils import callback_generator

def list_to_inline(buttons, row_width=3):
    """ Преобразует список кнопок в inline-клавиатуру 
         Example:
              buttons = [ {'text': 'Кнопка 1', 'callback_data': 'btn1'},
                          {'text': 'Кнопка 2', 'callback_data': 'btn2', 'ignore_row': 'true'},
                          {'text': 'Кнопка 3', 'callback_data': 'btn3'} ]
              
              > Кнопка 1 | Кнопка 2 
                    | Кнопка 3
    """

    inline_keyboard = []
    row = []
    for button in buttons:

        if 'ignore_row' in button and (button['ignore_row'].lower() == 'true' or button['ignore_row'] == True):
            inline_keyboard.append(row)
            row = []
            inline_keyboard.append([InlineKeyboardButton(**button)])
            continue
        row.append(InlineKeyboardButton(**button))
        if len(row) == row_width:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def update_page(user_company_id, page_name, user_id = None):
    company_users = await get_users(company_id=user_company_id)
    for user in company_users:
        user_id_2 = user.get('id')
        if user_id_2 != user_id or user_id is None:
            if user_id_2 and scene_manager.has_scene(user_id_2):
                scene = scene_manager.get_scene(user_id_2)
                if scene and scene.page:
                    current_page_name = scene.page
                    if current_page_name == page_name:
                        await scene.update_message()


async def go_to_page(session_id, old_page_name, new_page_name):
    companies = await get_companies(session_id=session_id)
    for c in companies:
        company_id = c.get('id')
        users = await get_users(session_id=session_id, company_id=company_id)
        for user in users:
            user_id = user.get('id')
            if user_id and scene_manager.has_scene(user_id):
                scene = scene_manager.get_scene(user_id)
                if scene and scene.page:
                    current_page_name = scene.page
                    if old_page_name is not None and current_page_name == old_page_name:
                        await scene.update_page(new_page_name)
                    else:
                        await scene.update_page(new_page_name)


def xy_into_cell(x, y):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return f"{alphabet[int(y)]}{int(x)+1}"

def cell_into_xy(cell):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    x = alphabet.index(cell[0].upper())
    y = int(cell[1:]) - 1
    return x, y


def do_matrix(list_matrix: list):
    len_one_line = int(len(list_matrix) ** 0.5)
    new_matrix = []
    line = []
    c = 0
    for i in list_matrix:
        line.append(i)
        c += 1
        if c == len_one_line:
            new_matrix.append(line)
            line = []
            c = 0
    return new_matrix


def do_cell_emoji(cell: str):
    cell_emoji = {
        "mountain": "⛰️",
        "water": "🌊",
        "forest": "🌲",
        "field": "🌾"
    }
    return cell_emoji[cell]


def do_matrix_7x7_with_large(matrix: list):
    n, m = len(matrix), len(matrix[0])
    center_i, center_j = n // 2, m // 2
    
    row_start = center_i - 3
    row_end = center_i + 4
    col_start = center_j - 3
    col_end = center_j + 4
    new_matrix = []
    for i in range(row_start, row_end):
        row = []
        for j in range(col_start, col_end):
            if 0 <= i < n and 0 <= j < m:
                row.append(matrix[i][j])
        new_matrix.append(row)
    return new_matrix


def create_buttons(scene_name, text: str, callback_data: str, *args, ignore_row=False, next_line=False):
    return {
        "text": text,
        "callback_data": callback_generator(scene_name, callback_data, *args),
        "ignore_row": ignore_row,
        "next_line": next_line
    }


