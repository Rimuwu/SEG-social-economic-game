import importlib

def func_to_str(func):
    """Преобразует функцию в строку вида 'модуль.имя_функции'."""
    return f"{func.__module__}.{func.__name__}"

def str_to_func(func_path):
    """Получает функцию по строке вида 'модуль.имя_функции'."""

    module_name, func_name = func_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def get_neighboring_cells(x: int, y: int, radius: int, map_size: dict) -> list[tuple[int, int]]:
    """Получает соседние клетки в радиусе от заданной координаты.
    
    Args:
        x: координата X
        y: координата Y
        radius: радиус поиска
        map_size: размер карты {"rows": int, "cols": int}
    
    Returns:
        Список кортежей с координатами соседних клеток
    """
    neighbors = []
    rows = map_size["rows"]
    cols = map_size["cols"]
    
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            # Пропускаем центральную клетку
            if dx == 0 and dy == 0:
                continue
            
            new_x = x + dx
            new_y = y + dy
            
            # Проверяем, что координаты в пределах карты
            if 0 <= new_x < rows and 0 <= new_y < cols:
                neighbors.append((new_x, new_y))
    
    return neighbors


async def determine_city_branch(
    x: int, y: int, 
    session_id: str, cells: list[str], 
    map_size: dict) -> str:
    """Определяет приоритетную ветку ресурсов для города на основе соседних клеток.
    
    Args:
        x: координата X города
        y: координата Y города
        session_id: ID сессии
        cells: список клеток карты
        map_size: размер карты
    
    Returns:
        Название ветки ('oil', 'metal', 'wood', 'cotton')
    """
    from modules.db import just_db
    
    # Маппинг типов клеток на ветки ресурсов
    cell_to_branch = {
        'water': 'oil',      # вода -> нефть
        'mountain': 'metal',  # горы -> металл
        'forest': 'wood',     # лес -> дерево
        'field': 'cotton'     # поле -> хлопок
    }
    
    # Получаем все города в сессии
    cities: list[dict] = await just_db.find(
        "cities", session_id=session_id) # type: ignore
    occupied_branches = {}
    
    for city in cities:
        if city.get('branch'):
            city_pos = city.get('cell_position', '').split('.')
            if len(city_pos) == 2:
                city_x, city_y = int(city_pos[0]), int(city_pos[1])
                occupied_branches[(city_x, city_y)] = city['branch']
    
    radius = 1
    max_radius = max(map_size["rows"], map_size["cols"]) // 2
    
    while radius <= max_radius:
        neighbors = get_neighboring_cells(x, y, radius, map_size)
        branch_counts = {'oil': 0, 'metal': 0, 'wood': 0, 'cotton': 0}
        
        # Подсчитываем ресурсы в радиусе
        for nx, ny in neighbors:
            index = nx * map_size["cols"] + ny
            if index < len(cells):
                cell_type = cells[index]
                if cell_type in cell_to_branch:
                    branch = cell_to_branch[cell_type]
                    branch_counts[branch] += 1
        
        # Исключаем ветки, занятые другими городами в этом радиусе
        for (city_x, city_y), branch in occupied_branches.items():
            if (city_x, city_y) in neighbors:
                # Уменьшаем приоритет занятой ветки
                branch_counts[branch] = max(0, branch_counts[branch] - 2)
        
        # Находим ветку с максимальным количеством клеток
        max_count = max(branch_counts.values())
        
        if max_count > 0:
            # Если есть явный лидер, возвращаем его
            top_branches = [b for b, c in branch_counts.items() if c == max_count]
            
            # Проверяем, не заняты ли все топовые ветки
            available_branches = [b for b in top_branches if b not in occupied_branches.values()]
            
            if available_branches:
                # Возвращаем случайную из доступных топовых веток
                import random
                return random.choice(available_branches)
            elif len(top_branches) == 1 or max_count >= radius * 2:
                # Если только одна ветка лидирует или явное преимущество
                return top_branches[0]
        
        # Увеличиваем радиус, если не нашли подходящую ветку
        radius += 1
    
    # Если ничего не нашли, возвращаем случайную ветку
    import random
    available = [b for b in ['oil', 'metal', 'wood', 'cotton'] 
                 if b not in occupied_branches.values()]
    return random.choice(available) if available else random.choice(
        ['oil', 'metal', 'wood', 'cotton'])