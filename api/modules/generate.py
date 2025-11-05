import random
import string

def generate_number(length) -> int:
    """Генерирует случайное число заданной длины"""
    if length <= 0:
        return 0

    # Первая цифра не может быть 0
    first_digit = random.randint(1, 9)
    remaining_digits = ''.join([str(random.randint(0, 9)) for _ in range(length - 1)])

    return first_digit + int(remaining_digits)

def generate_code(length, use_letters=True, use_numbers=True, use_uppercase=True):
    """Генерирует случайный код заданной длины
    
    Args:
        length (int): Длина генерируемого кода
        use_letters (bool): Использовать строчные буквы
        use_numbers (bool): Использовать цифры
        use_uppercase (bool): Использовать заглавные буквы
    
    Returns:
        str: Сгенерированный код
    """
    if length <= 0:
        return ""
    
    characters = ""
    
    if use_letters:
        characters += string.ascii_lowercase
    if use_uppercase:
        characters += string.ascii_uppercase
    if use_numbers:
        characters += string.digits
    
    if not characters:
        characters = string.ascii_letters + string.digits
    
    return ''.join(random.choice(characters) for _ in range(length))