from datetime import datetime, timedelta
import os
import re
from typing import Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
import importlib


CALLBACK_PREFIX = 'scene'
CALLBACK_SEPARATOR = ':'

def list_to_inline(buttons, row_width=3):
    """ Преобразует список кнопок в inline-клавиатуру 
         Example:
              buttons = [ {'text': 'Кнопка 1', 'callback_data': 'btn1'},
                          {'text': 'Кнопка 2', 'callback_data': 'btn2'},
                          {'text': 'Кнопка 3', 'callback_data': 'btn3'} ]

              > Кнопка 1 | Кнопка 2 | Кнопка 3
        ignore_row - кнопка будет на новой строке 
        next_line - после кнопки начнется новый ряд
    """

    inline_keyboard = []
    row = []
    for button in buttons:

        if 'ignore_row' in button and ((type(button['ignore_row']) == str and button['ignore_row'].lower() == 'true') or button['ignore_row'] == True):
            inline_keyboard.append(row)
            row = []
            inline_keyboard.append([InlineKeyboardButton(**button)])
            continue

        if 'next_line' in button and ((type(button['next_line']) == str and button['next_line'].lower() == 'true') or button['next_line'] == True):
            inline_keyboard.append(row)
            row = []

        if len(row) == row_width:
            inline_keyboard.append(row)
            row = []

        row.append(InlineKeyboardButton(**button))

    if row:
        inline_keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def callback_generator(scene_name: str, c_type: str, *args):
    """ prefix:type:name:*args
    """
    sep = CALLBACK_SEPARATOR
    res = f'{CALLBACK_PREFIX}{sep}{c_type}{sep}{scene_name}{sep}{":".join(map(str, args))}'
    if len(res) > 64:
        raise ValueError(f"Длина callback_data ({res}) превышает {len(res)} > 64 символа.")
    return res

def func_to_str(func):
    """Преобразует функцию в строку вида 'модуль.имя_функции'."""
    return f"{func.__module__}.{func.__name__}"

def str_to_func(func_path):
    """Получает функцию по строке вида 'модуль.имя_функции'."""

    module_name, func_name = func_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)

def parse_time(text: str) -> Optional[datetime]:
    """ Парсинг времени из строки """
    now = datetime.now()

    # Паттерн для времени с датой: 16:30 21.10.2025
    pattern_with_date = r'(\d{1,2}):(\d{2})\s+(\d{1,2})\.(\d{1,2})\.(\d{4})'
    match_date = re.match(pattern_with_date, text.strip())

    if match_date:
        hour, minute, day, month, year = map(int, match_date.groups())
        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return None

    # Паттерн для времени с датой без года: 16:30 21.10
    pattern_date_no_year = r'(\d{1,2}):(\d{2})\s+(\d{1,2})\.(\d{1,2})'
    match_date_no_year = re.match(pattern_date_no_year, text.strip())

    if match_date_no_year:
        hour, minute, day, month = map(int, match_date_no_year.groups())
        year = now.year
        try:
            target_time = datetime(year, month, day, hour, minute)
            # Если дата уже прошла в этом году, устанавливаем на следующий год
            if target_time <= now:
                target_time = datetime(year + 1, month, day, hour, minute)
            return target_time
        except ValueError:
            return None

    # Паттерн для времени без даты: 16:30
    pattern_time_only = r'(\d{1,2}):(\d{2})'
    match_time = re.match(pattern_time_only, text.strip())

    if match_time:
        hour, minute = map(int, match_time.groups())
        try:
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Если время уже прошло сегодня, устанавливаем на завтра
            if target_time <= now:
                target_time += timedelta(days=1)

            return target_time
        except ValueError:
            return None

    return None

def parse_text(text: str, data_type: str, separator: str = ','):
    """ Парсинг текста в соответствующий тип данных """
    text = text.strip()

    if data_type == 'int':
        try:
            return int(text)
        except ValueError:
            return None

    elif data_type == 'str':
        return text

    elif data_type == 'time':
        return parse_time(text)

    elif data_type == 'list':
        parsed_list = [item.strip() for item in text.split(separator) if item.strip()]
        # Если в списке только 1 элемент, считаем это не списком, а текстом
        if len(parsed_list) <= 1:
            return None
        return parsed_list

    return None

def prepare_image(image_path: str):
    """Подготавливает изображение для отправки в Telegram"""
    if not image_path:
        return None

    if not isinstance(image_path, str):
        return None

    # Если это URL
    if image_path.startswith(('http://', 'https://')):
        return image_path

    # Если это file_id Telegram (обычно начинается с определенных символов)
    if len(image_path) > 20 and not '/' in image_path and not '\\' in image_path:
        return image_path

    # Если это локальный файл
    if os.path.exists(image_path):
        return FSInputFile(image_path)

    return None
