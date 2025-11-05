import re

def validate_username(username: str) -> str:
    """
    Валидирует и очищает имя пользователя.
    
    Args:
        username (str): Исходное имя пользователя
        
    Returns:
        str: Очищенное имя пользователя
        
    Raises:
        ValueError: Если имя пользователя не соответствует требованиям
    """
    if not username:
        raise ValueError("Имя пользователя не может быть пустым.")
    
    # Убираем пробелы в начале и конце
    username = username.strip()
    
    # Удаляем нежелательные символы: _, *, `, ~
    forbidden_chars = ('_', '*', '`', '~')
    username = ''.join(c for c in username if c.isalnum() or c in ('-', ' ') and c not in forbidden_chars)
    
    # Убираем множественные пробелы и заменяем их одним
    username = re.sub(r'\s+', ' ', username).strip()
    
    # Проверяем длину
    if not (3 <= len(username) <= 20):
        raise ValueError("Имя / название должно быть от 3 до 20 символов.")
    
    return username