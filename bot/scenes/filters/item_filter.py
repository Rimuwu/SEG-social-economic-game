"""
Модуль фильтра предметов для различных страниц
Позволяет выбрать ресурс из списка и передать его в callback
"""
from typing import Optional, Callable
from oms.utils import callback_generator
from global_modules.load_config import ALL_CONFIGS, Resources

RESOURCES: Resources = ALL_CONFIGS["resources"]


class ItemFilter:
    """
    Фильтр предметов с пагинацией
    
    Пример использования в Page:
    
    # В __after_init__ или __post_init__:
    self.item_filter = ItemFilter(
        scene_name=self.scene.__scene_name__,
        callback_prefix='select_resource',
        items_per_page=5
    )
    
    # В buttons_worker:
    if filter_mode:
        buttons = self.item_filter.get_buttons(current_page=page_num)
    """
    
    def __init__(self, 
                 scene_name: str,
                 callback_prefix: str = 'filter_item',
                 items_per_page: int = 10,
                 show_raw_only: bool = False,
                 show_produced_only: bool = False):
        """
        Args:
            scene_name: Имя сцены для генерации callback_data
            callback_prefix: Префикс для callback (будет использоваться для идентификации выбора)
            items_per_page: Количество предметов на одной странице
            show_raw_only: Показывать только сырьевые ресурсы
            show_produced_only: Показывать только производимые ресурсы
        """
        self.scene_name = scene_name
        self.callback_prefix = callback_prefix
        self.items_per_page = items_per_page
        
        # Получаем список ресурсов
        if show_raw_only:
            self.resources = RESOURCES.get_raw_resources()
        elif show_produced_only:
            self.resources = RESOURCES.get_produced_resources()
        else:
            self.resources = RESOURCES.resources
        
        # Сортируем ресурсы по уровню и имени
        self.sorted_resources = sorted(
            self.resources.items(),
            key=lambda x: (x[1].lvl, x[1].label)
        )
        
        self.total_pages = max(1, (len(self.sorted_resources) + items_per_page - 1) // items_per_page)
    
    def get_page_resources(self, page: int) -> list[tuple[str, any]]:
        """Получить ресурсы для конкретной страницы"""
        start_idx = page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.sorted_resources[start_idx:end_idx]
    
    def get_buttons(self, 
                   current_page: int = 0,
                   add_reset_button: bool = True,
                   reset_callback: str = 'reset_filter') -> list[dict]:
        """
        Генерирует кнопки для фильтра
        
        Args:
            current_page: Текущая страница (0-indexed)
            add_reset_button: Добавить ли кнопку "Сбросить фильтр"
            reset_callback: Callback для кнопки сброса фильтра
        
        Returns:
            Список кнопок для InlineKeyboard
        """
        # Нормализуем номер страницы (зацикливание)
        current_page = current_page % self.total_pages
        buttons = []
        
        # Кнопки с ресурсами (каждая на отдельной строке через ignore_row)
        page_resources = self.get_page_resources(current_page)
        for i, (resource_id, resource) in enumerate(page_resources):
            buttons.append({
                'text': f'{resource.emoji} {resource.label}',
                'callback_data': callback_generator(
                    self.scene_name,
                    self.callback_prefix,
                    resource_id
                ),
                'ignore_row': True  # Каждая кнопка на отдельной строке
            })
        
        # Навигация (все 3 кнопки в одной строке)
        prev_page = (current_page - 1) % self.total_pages
        next_page = (current_page + 1) % self.total_pages
        
        # Кнопка "Назад" (продолжает после ресурсов)
        buttons.append({
            'text': '◀️ Назад',
            'callback_data': callback_generator(
                self.scene_name,
                'filter_page',
                str(prev_page)
            )
        })
        
        # Индикатор страницы (продолжает ту же строку)
        buttons.append({
            'text': f'📄 {current_page + 1}/{self.total_pages}',
            'callback_data': callback_generator(
                self.scene_name,
                'page_info',
                str(current_page)
            )
        })
        
        # Кнопка "Вперёд" (продолжает ту же строку)
        buttons.append({
            'text': 'Вперёд ▶️',
            'callback_data': callback_generator(
                self.scene_name,
                'filter_page',
                str(next_page)
            )
        })
        
        # Кнопка сброса фильтра
        if add_reset_button:
            buttons.append({
                'text': '🔄 Показать всё',
                'callback_data': callback_generator(
                    self.scene_name,
                    reset_callback
                ),
                'next_line': True
            })
        
        return buttons
    
    def get_resource_name(self, resource_id: str) -> Optional[str]:
        """Получить название ресурса по ID"""
        resource = RESOURCES.get_resource(resource_id)
        return f"{resource.emoji} {resource.label}" if resource else None
    
    def resource_exists(self, resource_id: str) -> bool:
        """Проверить существование ресурса"""
        return resource_id in self.resources
