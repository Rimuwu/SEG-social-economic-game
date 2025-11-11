from dataclasses import dataclass
from typing import Dict


@dataclass
class StartImprovementsLevel:
    """Начальные уровни улучшений"""
    warehouse: int
    contracts: int
    station: int
    factory: int


@dataclass
class Settings:
    """Игровые настройки"""
    players_wait_minutes: int  # Время ожидания игроков в минутах
    max_companies: int  # Максимальное количество компаний
    map_side: int  # Размер стороны карты (NxN)
    turn_cell_time_minutes: int  # Время на выбор клетки в минутах
    cell_on_company: int  # Количество клеток на компанию (НЕ ИСПОЛЬЗУЕТСЯ)
    time_on_game_stage: int  # Время на 1 игровой этап в минутах
    time_on_change_stage: int  # Время на смену этапа в минутах
    max_players_in_company: int  # Максимальное количество игроков в компании
    start_improvements_level: StartImprovementsLevel  # Начальные уровни улучшений
    max_credits_per_company: int  # Максимальное количество кредитов на компанию
    start_complectation: Dict[str, str]  # Начальная комплектация
    logistics_speed: int  # Скорость логистики (чем больше, тем быстрее)

    fast_logistic: float 
    fast_complectation: float

    fast_logistic_price: int 
    fast_complectation_price: int

    change_location_price: dict[str, int] # Ключи big & small с ценой

    tax_autopay_price: int  # Цена улучшения автоплатежа налогов

    @classmethod
    def load_from_json(cls, data: dict):
        start_improvements = StartImprovementsLevel(**data["start_improvements_level"])

        data['start_improvements_level'] = start_improvements
        return cls(**data)