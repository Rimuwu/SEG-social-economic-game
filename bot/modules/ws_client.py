import os
import time
from typing import Optional, Literal, Any
from global_modules.api_client import create_client
from global_modules.logs import Logger


UPDATE_PASSWORD = os.getenv("UPDATE_PASSWORD", "default_password")

# Настройка логирования
bot_logger = Logger.get_logger("bot")

# Создаем WebSocket клиента
ws_client = create_client(
    client_id=f"bot_client_{int(time.time())}", 
    uri=os.getenv("WS_SERVER_URI", "ws://localhost:81/ws/connect"),
    logger=bot_logger
)

# Функции для работы с компаниями
async def get_companies(session_id: Optional[str] = None, in_prison: Optional[bool] = None, cell_position: Optional[str] = None):
    """Получение списка компаний"""
    return await ws_client.send_message(
        "get-companies",
        session_id=session_id,
        in_prison=in_prison,
        cell_position=cell_position,
        wait_for_response=True,
        timeout=50
    )

async def get_company(id: Optional[int] = None, name: Optional[str] = None, reputation: Optional[int] = None, 
                     balance: Optional[int] = None, in_prison: Optional[bool] = None, 
                     session_id: Optional[str] = None, cell_position: Optional[str] = None):
    """Получение компании"""
    return await ws_client.send_message(
        "get-company",
        id=id,
        name=name,
        reputation=reputation,
        balance=balance,
        in_prison=in_prison,
        session_id=session_id,
        cell_position=cell_position,
        wait_for_response=True
    )

async def create_company(name: str, who_create: int):
    """Создание компании"""
    return await ws_client.send_message(
        "create-company",
        name=name,
        who_create=who_create,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def update_company_add_user(user_id: int, secret_code: int):
    """Добавление пользователя в компанию"""
    return await ws_client.send_message(
        "update-company-add-user",
        user_id=user_id,
        secret_code=secret_code,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def set_company_position(company_id: int, x: int, y: int):
    """Обновление местоположения компании"""
    return await ws_client.send_message(
        "set-company-position",
        company_id=company_id,
        x=x,
        y=y,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def update_company_left_user(user_id: int, company_id: str):
    """Выход пользователя из компании"""
    return await ws_client.send_message(
        "update-company-left-user",
        user_id=user_id,
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def delete_company(company_id: str):
    """Удаление компании"""
    return await ws_client.send_message(
        "delete-company",
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def get_company_cell_info(company_id: int):
    """Получение информации о ячейке компании"""
    return await ws_client.send_message(
        "get-company-cell-info",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_improvement_info(company_id: int):
    """Получение информации о улучшениях компании"""
    return await ws_client.send_message(
        "get-company-improvement-info",
        company_id=company_id,
        wait_for_response=True
    )

async def update_company_improve(company_id: str, improvement_type: str):
    """Улучшение компании"""
    return await ws_client.send_message(
        "update-company-improve",
        company_id=company_id,
        improvement_type=improvement_type,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def company_take_credit(company_id: str, amount: int, period: int):
    """Получение кредита компанией"""
    return await ws_client.send_message(
        "company-take-credit",
        company_id=company_id,
        amount=amount,
        period=period,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def company_pay_credit(company_id: str, credit_index: int, amount: int):
    """Погашение кредита компанией"""
    return await ws_client.send_message(
        "company-pay-credit",
        company_id=company_id,
        credit_index=credit_index,
        amount=amount,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def company_pay_taxes(company_id: str, amount: int):
    """Погашение налогов компанией"""
    return await ws_client.send_message(
        "company-pay-taxes",
        company_id=company_id,
        amount=amount,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def company_take_deposit(company_id: str, amount: int, period: int):
    """Создание вклада компанией"""
    return await ws_client.send_message(
        "company-take-deposit",
        company_id=company_id,
        amount=amount,
        period=period,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def company_withdraw_deposit(company_id: str, deposit_index: int):
    """Снятие вклада компанией"""
    return await ws_client.send_message(
        "company-withdraw-deposit",
        company_id=company_id,
        deposit_index=deposit_index,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def company_complete_free_factories(company_id: int, new_resource: str, count: int, 
                                        find_resource: Optional[str] = None, 
                                        produce_status: Optional[bool] = None):
    """Массовая перекомплектация свободных фабрик компании"""
    return await ws_client.send_message(
        "company-complete-free-factories",
        company_id=company_id,
        find_resource=find_resource,
        new_resource=new_resource,
        count=count,
        produce_status=produce_status,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

# Функции для работы с логистикой
async def get_logistics(session_id: Optional[str] = None, 
                       from_company_id: Optional[int] = None,
                       to_company_id: Optional[int] = None, 
                       to_city_id: Optional[int] = None,
                       logistics_id: Optional[int] = None,
                       destination_type: Optional[Literal['company', 'city']] = None,
                       status: Optional[Literal['in_transit', 'waiting_pickup', 'delivered', 'failed']] = None):
    """Получение списка логистики (доставок)
    
    Args:
        session_id: ID сессии для фильтрации
        from_company_id: ID компании-отправителя
        to_company_id: ID компании-получателя
        to_city_id: ID города-получателя
        logistics_id: ID конкретной логистики
        destination_type: Тип назначения ('company' или 'city')
        status: Статус доставки ('in_transit', 'waiting_pickup', 'delivered', 'failed')
    """
    return await ws_client.send_message(
        "get-logistics",
        session_id=session_id,
        from_company_id=from_company_id,
        to_company_id=to_company_id,
        to_city_id=to_city_id,
        logistics_id=logistics_id,
        destination_type=destination_type,
        status=status,
        wait_for_response=True
    )

async def logistics_pickup(logistics_id: int, company_id: int):
    """Получение ожидающего груза компанией
    
    Args:
        logistics_id: ID логистики
        company_id: ID компании, которая забирает груз
    """
    return await ws_client.send_message(
        "logistics-pickup",
        logistics_id=logistics_id,
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

# Функции для работы с контрактами
async def get_contracts(session_id: Optional[str] = None, 
                       supplier_company_id: Optional[int] = None,
                       customer_company_id: Optional[int] = None,
                       accepted: Optional[bool] = None,
                       resource: Optional[str] = None):
    """Получение списка контрактов с фильтрацией
    
    Args:
        session_id: ID сессии
        supplier_company_id: ID компании-поставщика
        customer_company_id: ID компании-заказчика
        accepted: Фильтр по статусу принятия (True/False/None)
        resource: Фильтр по ресурсу
    """
    return await ws_client.send_message(
        "get-contracts",
        session_id=session_id,
        supplier_company_id=supplier_company_id,
        customer_company_id=customer_company_id,
        accepted=accepted,
        resource=resource,
        wait_for_response=True
    )

async def get_contract(id: Optional[int] = None,
                      supplier_company_id: Optional[int] = None,
                      customer_company_id: Optional[int] = None,
                      session_id: Optional[str] = None,
                      accepted: Optional[bool] = None,
                      resource: Optional[str] = None):
    """Получение конкретного контракта
    
    Args:
        id: ID контракта
        supplier_company_id: ID компании-поставщика
        customer_company_id: ID компании-заказчика
        session_id: ID сессии
        accepted: Статус принятия
        resource: Ресурс контракта
    """
    return await ws_client.send_message(
        "get-contract",
        id=id,
        supplier_company_id=supplier_company_id,
        customer_company_id=customer_company_id,
        session_id=session_id,
        accepted=accepted,
        resource=resource,
        wait_for_response=True
    )

async def create_contract(supplier_company_id: int, customer_company_id: int,
                         session_id: str, resource: str, amount_per_turn: int,
                         duration_turns: int, payment_amount: int, who_creator: int):
    """Создание контракта
    
    Args:
        supplier_company_id: ID компании-поставщика
        customer_company_id: ID компании-заказчика
        session_id: ID сессии
        resource: Ресурс для поставки
        amount_per_turn: Количество ресурса за ход
        duration_turns: Длительность контракта в ходах
        payment_amount: Общая сумма оплаты
        who_creator: ID пользователя-создателя
    """
    return await ws_client.send_message(
        "create-contract",
        supplier_company_id=supplier_company_id,
        customer_company_id=customer_company_id,
        session_id=session_id,
        resource=resource,
        amount_per_turn=amount_per_turn,
        duration_turns=duration_turns,
        payment_amount=payment_amount,
        who_creator=who_creator,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def accept_contract(contract_id: int, who_accepter: int):
    """Принятие контракта поставщиком
    
    Args:
        contract_id: ID контракта
        who_accepter: ID пользователя, принимающего контракт
    """
    return await ws_client.send_message(
        "accept-contract",
        contract_id=contract_id,
        who_accepter=who_accepter,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def decline_contract(contract_id: int, who_decliner: int):
    """Отклонение контракта поставщиком
    
    Args:
        contract_id: ID контракта
        who_decliner: ID пользователя, отклоняющего контракт
    """
    return await ws_client.send_message(
        "decline-contract",
        contract_id=contract_id,
        who_decliner=who_decliner,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def execute_contract(contract_id: int):
    """Выполнение поставки по контракту
    
    Args:
        contract_id: ID контракта
    """
    return await ws_client.send_message(
        "execute-contract",
        contract_id=contract_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def cancel_contract(contract_id: int, who_canceller: int):
    """Отмена контракта с возвратом части денег и штрафом репутации
    
    Args:
        contract_id: ID контракта
        who_canceller: ID пользователя, отменяющего контракт
    """
    return await ws_client.send_message(
        "cancel-contract",
        contract_id=contract_id,
        who_canceller=who_canceller,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def get_company_contracts(company_id: int, as_supplier: Optional[bool] = None,
                               as_customer: Optional[bool] = None,
                               accepted_only: Optional[bool] = None):
    """Получение контрактов компании (как поставщика и/или как заказчика)
    
    Args:
        company_id: ID компании
        as_supplier: Получить контракты где компания - поставщик
        as_customer: Получить контракты где компания - заказчик
        accepted_only: Только принятые контракты
    """
    return await ws_client.send_message(
        "get-company-contracts",
        company_id=company_id,
        as_supplier=as_supplier,
        as_customer=as_customer,
        accepted_only=accepted_only,
        wait_for_response=True
    )


async def set_autopay_taxe(company_id: int):
    """Установка автоплатежа налогов для компании"""
    return await ws_client.send_message(
        "set-autopay-taxes",
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )


async def notforgame_create_timer(session_id):
    """Создание таймера для сессии. НЕ ИСПОЛЬЗОВАТЬ В ИГРОВОМ ПРОЦЕССЕ!"""
    return await ws_client.send_message(
        "notforgame-create-timer",
        session_id=session_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )


async def get_company_users(company_id: int):
    """Получение списка пользователей компании"""
    return await ws_client.send_message(
        "get-company-users",
        company_id=company_id,
        wait_for_response=True
    )

async def company_get_statistics(company_id: int, session_id: str):
    """Получение статистики компании"""
    return await ws_client.send_message(
        "company-get-statistics",
        company_id=company_id,
        session_id=session_id,
        wait_for_response=True
    )

async def get_company_balance(company_id: int):
    """Получение баланса компании"""
    return await ws_client.send_message(
        "get-company-balance",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_reputation(company_id: int):
    """Получение репутации компании"""
    return await ws_client.send_message(
        "get-company-reputation",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_warehouse(company_id: int):
    """Получение данных склада компании"""
    return await ws_client.send_message(
        "get-company-warehouse",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_credits(company_id: int):
    """Получение данных по кредитам компании"""
    return await ws_client.send_message(
        "get-company-credits",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_deposits(company_id: int):
    """Получение данных по депозитам компании"""
    return await ws_client.send_message(
        "get-company-deposits",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_taxes(company_id: int):
    """Получение данных по налогам компании"""
    return await ws_client.send_message(
        "get-company-taxes",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_position(company_id: int):
    """Получение позиции компании на карте"""
    return await ws_client.send_message(
        "get-company-position",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_prison_status(company_id: int):
    """Получение статуса тюрьмы компании"""
    return await ws_client.send_message(
        "get-company-prison-status",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_basic_info(company_id: int):
    """Получение базовой информации о компании"""
    return await ws_client.send_message(
        "get-company-basic-info",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_factories(company_id: int):
    """Получение фабрик компании"""
    return await ws_client.send_message(
        "get-company-factories",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_exchanges(company_id: int):
    """Получение бирж компании"""
    return await ws_client.send_message(
        "get-company-exchanges",
        company_id=company_id,
        wait_for_response=True
    )

async def get_company_production(company_id: int):
    """Получение производственной информации компании"""
    return await ws_client.send_message(
        "get-company-production",
        company_id=company_id,
        wait_for_response=True
    )

async def set_fast_logistic(company_id: int):
    """Установка быстрой логистики"""
    return await ws_client.send_message(
        "set-fast-logistic",
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def set_fast_complectation(company_id: int):
    """Установка быстрой комплектации"""
    return await ws_client.send_message(
        "set-fast-complectation",
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def change_position(company_id: int, x: int, y: int):
    """Изменение позиции компании на карте (платная услуга)"""
    return await ws_client.send_message(
        "change-position",
        company_id=company_id,
        x=x,
        y=y,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def notforgame_company_prison(company_id: int):
    """Отправление компании в тюрьму. НЕ ИСПОЛЬЗОВАТЬ В ИГРОВОМ ПРОЦЕССЕ!"""
    return await ws_client.send_message(
        "notforgame-compny-prison",
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def notforgame_update_company_balance(company_id: int, balance_change: int):
    """Обновление баланса компании. НЕ ИСПОЛЬЗОВАТЬ В ИГРОВОМ ПРОЦЕССЕ!
    
    Args:
        company_id: ID компании
        balance_change: Изменение баланса (может быть отрицательным)
    """
    return await ws_client.send_message(
        "notforgame-update-company-balance",
        company_id=company_id,
        balance_change=balance_change,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def notforgame_update_company_items(company_id: int, item_id: str, quantity_change: int, 
                                          ignore_space: Optional[bool] = None):
    """Обновление предметов компании. НЕ ИСПОЛЬЗОВАТЬ В ИГРОВОМ ПРОЦЕССЕ!
    
    Args:
        company_id: ID компании
        item_id: ID предмета/ресурса
        quantity_change: Изменение количества (может быть отрицательным)
        ignore_space: Игнорировать ограничения на место в складе
    """
    return await ws_client.send_message(
        "notforgame-update-company-items",
        company_id=company_id,
        item_id=item_id,
        quantity_change=quantity_change,
        ignore_space=ignore_space,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def notforgame_update_company_name(company_id: int, new_name: str):
    """Обновление названия компании
    
    Args:
        company_id: ID компании
        new_name: Новое название компании
    """
    return await ws_client.send_message(
        "notforgame-update-company-name",
        company_id=company_id,
        new_name=new_name,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

# Функции для работы с фабриками
async def get_factories(company_id: Optional[int] = None, 
                        complectation: Optional[str] = None, 
                       produce: Optional[bool] = None, is_auto: Optional[bool] = None):
    """Получение списка фабрик"""
    return await ws_client.send_message(
        "get-factories",
        company_id=company_id,
        complectation=complectation,
        produce=produce,
        is_auto=is_auto,
        wait_for_response=True
    )

async def get_factory(factory_id: int):
    """Получение информации о фабрике"""
    return await ws_client.send_message(
        "get-factory",
        factory_id=factory_id,
        wait_for_response=True
    )

async def factory_recomplectation(factory_id: int, new_complectation: str):
    """Перекомплектация фабрики"""
    return await ws_client.send_message(
        "factory-recomplectation",
        factory_id=factory_id,
        new_complectation=new_complectation,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def factory_set_produce(factory_id: int, produce: bool):
    """Установка статуса производства фабрики"""
    return await ws_client.send_message(
        "factory-set-produce",
        factory_id=factory_id,
        produce=produce,
        wait_for_response=True
    )

async def factory_set_auto(factory_id: int, is_auto: bool):
    """Установка статуса автоматического производства фабрики"""
    return await ws_client.send_message(
        "factory-set-auto",
        factory_id=factory_id,
        is_auto=is_auto,
        wait_for_response=True
    )

# Функции для работы с сессиями
async def get_sessions(stage: Optional[str] = None):
    """Получение списка сессий"""
    return await ws_client.send_message(
        "get-sessions",
        stage=stage,
        wait_for_response=True
    )

async def get_session(session_id: Optional[str] = None, stage: Optional[str] = None):
    """Получение сессии"""
    return await ws_client.send_message(
        "get-session",
        session_id=session_id,
        stage=stage,
        wait_for_response=True
    )

async def create_session(session_id: Optional[str] = None, 
                        map_pattern: Optional[str] = None,
                        size: Optional[int] = None,
                        max_steps: Optional[int] = None,
                        session_group_url: Optional[str] = None,
                        max_companies: Optional[int] = None,
                        max_players_in_company: Optional[int] = None,
                        time_on_game_stage: Optional[int] = None,
                        time_on_change_stage: Optional[int] = None):
    """Создание сессии
    
    Args:
        session_id: ID сессии (опционально)
        map_pattern: Паттерн карты (опционально)
        size: Размер карты (опционально)
        max_steps: Максимальное количество ходов (опционально)
        session_group_url: URL группы сессии (опционально)
        max_companies: Максимальное количество компаний (опционально)
        max_players_in_company: Максимальное количество игроков в компании (опционально)
        time_on_game_stage: Время на игровой стадии (опционально)
        time_on_change_stage: Время на стадии смены (опционально)
    """
    return await ws_client.send_message(
        "create-session",
        session_id=session_id,
        map_pattern=map_pattern,
        size=size,
        max_steps=max_steps,
        session_group_url=session_group_url,
        max_companies=max_companies,
        max_players_in_company=max_players_in_company,
        time_on_game_stage=time_on_game_stage,
        time_on_change_stage=time_on_change_stage,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def update_session_stage(session_id: Optional[str] = None, 
                              stage: Literal['FreeUserConnect', 'CellSelect', 'Game', 'End'] = 'FreeUserConnect',
                              add_shedule: Optional[bool] = None):
    """Обновление стадии сессии
    
    Args:
        session_id: ID сессии
        stage: Новая стадия сессии
        add_shedule: Запускать ли таймер после обновления этапа (по умолчанию True)
    """
    return await ws_client.send_message(
        "update-session-stage",
        session_id=session_id,
        stage=stage,
        add_shedule=add_shedule,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def get_sessions_free_cells(session_id: str):
    """Получение свободных клеток сессии"""
    return await ws_client.send_message(
        "get-sessions-free-cells",
        session_id=session_id,
        wait_for_response=True
    )

async def delete_session(session_id: str, really: bool = False):
    """Удаление сессии"""
    return await ws_client.send_message(
        "delete-session",
        session_id=session_id,
        password=UPDATE_PASSWORD,
        really=really,
        wait_for_response=True
    )

async def get_session_time_to_next_stage(session_id: str):
    """Получение времени до следующей стадии сессии"""
    return await ws_client.send_message(
        "get-session-time-to-next-stage",
        session_id=session_id,
        wait_for_response=True
    )

async def get_item_price(session_id: str, item_id: str):
    """Получение цены конкретного товара в сессии"""
    return await ws_client.send_message(
        "get-item-price",
        session_id=session_id,
        item_id=item_id,
        wait_for_response=True
    )

async def get_items_price(session_id: str):
    """Получение цен товаров в городе (алиас для get_all_item_prices)"""
    return await ws_client.send_message(
        "get-items-price",
        session_id=session_id,
        wait_for_response=True
    )

async def get_item_price_by_id(session_id: str, item_id: str):
    """Получение цены товара по ID (алиас для get_item_price)"""
    return await ws_client.send_message(
        "get-item-price-by-id",
        session_id=session_id,
        item_id=item_id,
        wait_for_response=True
    )

async def get_all_item_prices(session_id: str):
    """Получение всех цен товаров в сессии"""
    return await ws_client.send_message(
        "get-all-item-prices",
        session_id=session_id,
        wait_for_response=True
    )

async def get_session_event(session_id: str):
    """Получение события сессии"""
    return await ws_client.send_message(
        "get-session-event",
        session_id=session_id,
        wait_for_response=True
    )

async def get_session_leaders(session_id: str):
    """Получение лидеров сессии (топ компаний)
    
    Args:
        session_id: ID сессии
    """
    return await ws_client.send_message(
        "get-session-leaders",
        session_id=session_id,
        wait_for_response=True
    )

async def get_all_session_statistics(session_id: str):
    """Получение всех статистических данных сессии
    
    Args:
        session_id: ID сессии
    """
    return await ws_client.send_message(
        "get-all-session-statistics",
        session_id=session_id,
        wait_for_response=True
    )

async def get_session_basic_info(session_id: str):
    """Получение базовой информации о сессии
    
    Args:
        session_id: ID сессии
    """
    return await ws_client.send_message(
        "get-session-basic-info",
        session_id=session_id,
        wait_for_response=True
    )

async def get_session_map_info(session_id: str):
    """Получение информации о карте сессии
    
    Args:
        session_id: ID сессии
    """
    return await ws_client.send_message(
        "get-session-map-info",
        session_id=session_id,
        wait_for_response=True
    )

async def get_session_companies(session_id: str, full_data: Optional[bool] = None):
    """Получение компаний сессии
    
    Args:
        session_id: ID сессии
        full_data: Получить полные данные о компаниях
    """
    return await ws_client.send_message(
        "get-session-companies",
        session_id=session_id,
        full_data=full_data,
        wait_for_response=True
    )

async def get_session_users(session_id: str):
    """Получение пользователей сессии
    
    Args:
        session_id: ID сессии
    """
    return await ws_client.send_message(
        "get-session-users",
        session_id=session_id,
        wait_for_response=True
    )

async def get_session_cities(session_id: str):
    """Получение городов сессии
    
    Args:
        session_id: ID сессии
    """
    return await ws_client.send_message(
        "get-session-cities",
        session_id=session_id,
        wait_for_response=True
    )

async def notforgame_update_session_max_steps(session_id: str, max_steps: int):
    """Обновление максимального количества этапов сессии. НЕ ИСПОЛЬЗОВАТЬ В ИГРОВОМ ПРОЦЕССЕ!
    
    Args:
        session_id: ID сессии
        max_steps: Новое максимальное количество этапов
    """
    return await ws_client.send_message(
        "notforgame-update-session-max-steps",
        session_id=session_id,
        max_steps=max_steps,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

# Функции для работы с городами
async def get_cities(session_id: Optional[str] = None):
    """Получение списка городов"""
    return await ws_client.send_message(
        "get-cities",
        session_id=session_id,
        wait_for_response=True
    )

async def get_city(id: Optional[int] = None, session_id: Optional[str] = None, 
                   cell_position: Optional[str] = None, branch: Optional[str] = None):
    """Получение города
    
    Args:
        id: ID города
        session_id: ID сессии
        cell_position: Позиция ячейки
        branch: Отрасль города
    """
    return await ws_client.send_message(
        "get-city",
        id=id,
        session_id=session_id,
        cell_position=cell_position,
        branch=branch,
        wait_for_response=True
    )

async def sell_to_city(city_id: int, company_id: int, resource_id: str, amount: int):
    """Продажа ресурса городу
    
    Args:
        city_id: ID города
        company_id: ID компании
        resource_id: ID ресурса
        amount: Количество ресурса
    """
    return await ws_client.send_message(
        "sell-to-city",
        city_id=city_id,
        company_id=company_id,
        resource_id=resource_id,
        amount=amount,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def get_city_demands(city_id: int):
    """Получение спроса города на товары"""
    return await ws_client.send_message(
        "get-city-demands",
        city_id=city_id,
        wait_for_response=True
    )

# Функции для работы с пользователями
async def get_users(company_id: Optional[int] = None, session_id: Optional[str] = None):
    """Получение списка пользователей"""
    return await ws_client.send_message(
        "get-users",
        company_id=company_id,
        session_id=session_id,
        wait_for_response=True
    )

async def get_user(id: Optional[int] = None, username: Optional[str] = None, 
                  company_id: Optional[int] = None, session_id: Optional[str] = None):
    """Получение пользователя"""
    return await ws_client.send_message(
        "get-user",
        id=id,
        username=username,
        company_id=company_id,
        session_id=session_id,
        wait_for_response=True
    )

async def create_user(user_id: int, username: str, session_id: str):
    """Создание пользователя"""
    return await ws_client.send_message(
        "create-user",
        user_id=user_id,
        username=username,
        password=UPDATE_PASSWORD,
        session_id=session_id,
        wait_for_response=True
    )

async def update_user(user_id: int, username: Optional[str] = None, company_id: Optional[int] = None):
    """Обновление пользователя"""
    return await ws_client.send_message(
        "update-user",
        user_id=user_id,
        username=username,
        company_id=company_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def delete_user(user_id: int):
    """Удаление пользователя"""
    return await ws_client.send_message(
        "delete-user",
        user_id=user_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

# Функции биржи (Exchange)
async def get_exchanges(session_id: Optional[str] = None, company_id: Optional[int] = None, 
                       sell_resource: Optional[str] = None, offer_type: Optional[str] = None):
    """Получить список предложений биржи с фильтрацией"""
    return await ws_client.send_message(
        "get-exchanges",
        session_id=session_id,
        company_id=company_id,
        sell_resource=sell_resource,
        offer_type=offer_type,
        wait_for_response=True
    )

async def get_exchange(id: int):
    """Получить информацию о конкретном предложении биржи"""
    return await ws_client.send_message(
        "get-exchange",
        id=id,
        wait_for_response=True
    )

async def create_exchange_offer(
    company_id: int,
    session_id: str,
    sell_resource: str,
    sell_amount_per_trade: int,
    count_offers: int,
    offer_type: Literal['money', 'barter'],
    price: Optional[int] = None,
    barter_resource: Optional[str] = None,
    barter_amount: Optional[int] = None
):
    """Создать предложение на бирже
    
    Args:
        company_id: ID компании
        session_id: ID сессии
        sell_resource: Ресурс для продажи
        sell_amount_per_trade: Количество ресурса за сделку
        count_offers: Количество предложений
        offer_type: Тип предложения ('money' или 'barter')
        price: Цена (для offer_type='money')
        barter_resource: Ресурс бартера (для offer_type='barter')
        barter_amount: Количество ресурса бартера (для offer_type='barter')
    """
    return await ws_client.send_message(
        "create-exchange-offer",
        company_id=company_id,
        session_id=session_id,
        sell_resource=sell_resource,
        sell_amount_per_trade=sell_amount_per_trade,
        count_offers=count_offers,
        offer_type=offer_type,
        price=price,
        barter_resource=barter_resource,
        barter_amount=barter_amount,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def update_exchange_offer(
    offer_id: int,
    sell_amount_per_trade: Optional[int] = None,
    price: Optional[int] = None,
    barter_amount: Optional[int] = None
):
    """Обновить параметры предложения биржи"""
    return await ws_client.send_message(
        "update-exchange-offer",
        offer_id=offer_id,
        sell_amount_per_trade=sell_amount_per_trade,
        price=price,
        barter_amount=barter_amount,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def cancel_exchange_offer(offer_id: int):
    """Отменить предложение биржи (возврат товара)"""
    return await ws_client.send_message(
        "cancel-exchange-offer",
        offer_id=offer_id,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

async def buy_exchange_offer(offer_id: int, buyer_company_id: int, quantity: int):
    """Купить предложение с биржи
    
    Args:
        offer_id: ID предложения
        buyer_company_id: ID компании-покупателя
        quantity: Количество для покупки
    """
    return await ws_client.send_message(
        "buy-exchange-offer",
        offer_id=offer_id,
        buyer_company_id=buyer_company_id,
        quantity=quantity,
        password=UPDATE_PASSWORD,
        wait_for_response=True
    )

# Утилитарные функции
async def ping(timestamp: str = "", content: Any = None):
    """Ping сообщение"""
    return await ws_client.send_message(
        "ping",
        timestamp=timestamp,
        content=content,
        wait_for_response=True
    )
