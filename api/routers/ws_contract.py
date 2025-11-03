from game.contract import Contract
from modules.websocket_manager import websocket_manager
from modules.check_password import check_password
from modules.ws_hadnler import message_handler
from modules.db import just_db

@message_handler(
    "get-contracts", 
    doc="Обработчик получения списка контрактов. Отправляет ответ на request_id", 
    datatypes=[
        "session_id: Optional[str]", 
        "supplier_company_id: Optional[int]",
        "customer_company_id: Optional[int]",
        "accepted: Optional[bool]",
        "resource: Optional[str]",
        "request_id: str"
        ])
async def handle_get_contracts(client_id: str, message: dict):
    """Обработчик получения списка контрактов"""

    conditions = {
        "session_id": message.get("session_id"),
        "supplier_company_id": message.get("supplier_company_id"),
        "customer_company_id": message.get("customer_company_id"),
        "accepted": message.get("accepted"),
        "resource": message.get("resource")
    }

    # Получаем список контрактов из базы данных
    contracts_data: list[dict] = await just_db.find('contracts',
                         **{k: v for k, v in conditions.items() if v is not None}) # type: ignore

    contracts = []
    for contract_data in contracts_data:
        contract = Contract(id=contract_data.get('id', 0))
        contract.load_from_base(contract_data)
        contracts.append(contract)

    return [contract.to_dict() for contract in contracts]

@message_handler(
    "get-contract", 
    doc="Обработчик получения контракта. Отправляет ответ на request_id.", 
    datatypes=[
        "id: Optional[int]", 
        "supplier_company_id: Optional[int]", 
        "customer_company_id: Optional[int]", 
        "session_id: Optional[str]",
        "accepted: Optional[bool]",
        "resource: Optional[str]",
        "request_id: str"
        ])
async def handle_get_contract(client_id: str, message: dict):
    """Обработчик получения контракта"""

    conditions = {
        "id": message.get("id"),
        "supplier_company_id": message.get("supplier_company_id"),
        "customer_company_id": message.get("customer_company_id"),
        "session_id": message.get("session_id"),
        "accepted": message.get("accepted"),
        "resource": message.get("resource")
    }

    # Получаем контракт из базы данных
    contract_data = await just_db.find_one('contracts',
                         **{k: v for k, v in conditions.items() if v is not None})

    if contract_data:
        contract = Contract(id=contract_data.get('id', 0))
        contract.load_from_base(contract_data)
        return contract.to_dict()
    else:
        return None

@message_handler(
    "create-contract", 
    doc="Обработчик создания контракта. Отправляет ответ на request_id. Требуется пароль для взаимодействия.",
    datatypes=[
        "supplier_company_id: int",
        "customer_company_id: int",
        "session_id: str",
        "resource: str",
        "amount_per_turn: int",
        "duration_turns: int",
        "payment_amount: int",
        "who_creator: int",

        "password: str",
        "request_id: str"
    ],
    messages=["api-contract_created (broadcast)"]
)
async def handle_create_contract(client_id: str, message: dict):
    """Обработчик создания контракта"""

    password = message.get("password")
    supplier_company_id = message.get("supplier_company_id")
    customer_company_id = message.get("customer_company_id")
    session_id = message.get("session_id")
    resource = message.get("resource")
    amount_per_turn = message.get("amount_per_turn")
    duration_turns = message.get("duration_turns")
    payment_amount = message.get("payment_amount")
    who_creator = message.get("who_creator")

    required_fields = [
        supplier_company_id, customer_company_id, session_id, 
        resource, amount_per_turn, duration_turns, payment_amount, password, who_creator
    ]
    
    for field in required_fields:
        if field is None: 
            return {"error": "Упущены обязательные поля."}

    try:
        # Проверка типов
        if not isinstance(password, str):
            return {"error": "Password must be a string"}
        if not isinstance(supplier_company_id, int):
            return {"error": "Supplier company ID must be an integer"}
        if not isinstance(customer_company_id, int):
            return {"error": "Customer company ID must be an integer"}
        if not isinstance(session_id, str):
            return {"error": "Session ID must be a string"}
        if not isinstance(resource, str):
            return {"error": "Resource must be a string"}
        if not isinstance(amount_per_turn, int):
            return {"error": "Amount per turn must be an integer"}
        if not isinstance(duration_turns, int):
            return {"error": "Duration turns must be an integer"}
        if not isinstance(payment_amount, int):
            return {"error": "Payment amount must be an integer"}
        if not isinstance(who_creator, int):
            return {"error": "Who creator must be an integer"}

        check_password(password)

        contract = Contract()
        await contract.create(
            supplier_company_id=supplier_company_id,
            customer_company_id=customer_company_id,
            session_id=session_id,
            resource=resource,
            amount_per_turn=amount_per_turn,
            duration_turns=duration_turns,
            payment_amount=payment_amount,
            who_creator=who_creator
        )

    except ValueError as e:
        return {"error": str(e)}

    return {
        'contract_id': contract.id,
        'contract': contract.to_dict()
    }

@message_handler(
    "accept-contract", 
    doc="Обработчик принятия контракта поставщиком. Требуется пароль для взаимодействия.",
    datatypes=[
        "contract_id: int",
        "who_accepter: int",

        "password: str"
    ],
    messages=["api-contract_accepted (broadcast)"]
)
async def handle_accept_contract(client_id: str, message: dict):
    """Обработчик принятия контракта поставщиком"""

    password = message.get("password")
    contract_id = message.get("contract_id")
    who_accepter = message.get("who_accepter", 0)

    for i in [contract_id, password, who_accepter]:
        if i is None: return {"error": "Упущены обязательные поля."}

    try:
        if not isinstance(password, str):
            return {"error": "Пароль должен быть строкой"}
        if not isinstance(contract_id, int):
            return {"error": "ID контракта должен быть целым числом"}

        check_password(password)

        contract = await Contract(id=contract_id).reupdate()
        if not contract: raise ValueError("Контракт не найден.")

        await contract.accept_contract(who_accepter)

    except ValueError as e:
        return {"error": str(e)}

    return {"success": True}

@message_handler(
    "decline-contract", 
    doc="Обработчик отклонения контракта поставщиком. Требуется пароль для взаимодействия.",
    datatypes=[
        "contract_id: int",
        "who_decliner: int",

        "password: str"
    ],
    messages=["api-contract_declined (broadcast)"]
)
async def handle_decline_contract(client_id: str, message: dict):
    """Обработчик отклонения контракта поставщиком"""

    password = message.get("password")
    contract_id = message.get("contract_id")
    who_decliner = message.get("who_decliner", 0)

    for i in [contract_id, password, who_decliner]:
        if i is None: return {"error": "Упущены обязательные поля."}

    try:
        if not isinstance(password, str):
            return {"error": "Пароль должен быть строкой"}
        if not isinstance(contract_id, int):
            return {"error": "ID контракта должен быть целым числом"}

        check_password(password)

        contract = await Contract(id=contract_id).reupdate()
        if not contract: raise ValueError("Контракт не найден.")

        await contract.decline_contract(who_decliner)

    except ValueError as e:
        return {"error": str(e)}

    return {"success": True}

@message_handler(
    "execute-contract", 
    doc="Обработчик выполнения поставки по контракту. Требуется пароль для взаимодействия. Отправляет ответ на request_id.",
    datatypes=[
        "contract_id: int",

        "password: str",
        "request_id: str"
    ],
    messages=["api-contract_executed (broadcast)"]
)
async def handle_execute_contract(client_id: str, message: dict):
    """Обработчик выполнения поставки по контракту"""

    password = message.get("password")
    contract_id = message.get("contract_id")

    for i in [contract_id, password]:
        if i is None: return {"error": "Упущены обязательные поля."}

    try:
        if not isinstance(password, str):
            return {"error": "Пароль должен быть строкой"}
        if not isinstance(contract_id, int):
            return {"error": "ID контракта должен быть целым числом"}

        check_password(password)

        contract = await Contract(id=contract_id).reupdate()
        if not contract: raise ValueError("Контракт не найден.")

        success = await contract.execute_turn()

    except ValueError as e:
        return {"error": str(e)}

    return {
        "success": success,
        "contract_completed": success and contract.successful_deliveries >= contract.duration_turns
    }

@message_handler(
    "cancel-contract", 
    doc="Обработчик отмены контракта с возвратом части денег и штрафом репутации. Требуется пароль для взаимодействия.",
    datatypes=[
        "contract_id: int",
        "who_canceller: int",

        "password: str"
    ],
    messages=["api-contract_cancelled (broadcast)"]
)
async def handle_cancel_contract(client_id: str, message: dict):
    """Обработчик отмены контракта с возвратом части денег и штрафом репутации"""

    password = message.get("password")
    contract_id = message.get("contract_id")
    who_canceller = message.get("who_canceller", 0)

    for i in [contract_id, password, who_canceller]:
        if i is None: return {"error": "Упущены обязательные поля."}

    try:
        if not isinstance(password, str):
            return {"error": "Password must be a string"}
        if not isinstance(contract_id, int):
            return {"error": "Contract ID must be an integer"}

        check_password(password)

        contract = await Contract(id=contract_id).reupdate()
        if not contract: raise ValueError("Контракт не найден.")

        await contract.cancel_with_refund(who_canceller)

    except ValueError as e:
        return {"error": str(e)}

    return {"success": True}

@message_handler(
    "get-company-contracts", 
    doc="Обработчик получения контрактов компании (как поставщика и как заказчика). Отправляет ответ на request_id", 
    datatypes=[
        "company_id: int",
        "as_supplier: Optional[bool]",
        "as_customer: Optional[bool]",
        "accepted_only: Optional[bool]",
        "request_id: str"
        ])
async def handle_get_company_contracts(client_id: str, message: dict):
    """Обработчик получения контрактов компании"""

    company_id = message.get("company_id")
    as_supplier = message.get("as_supplier", True)
    as_customer = message.get("as_customer", True)
    accepted_only = message.get("accepted_only", False)

    if company_id is None:
        return {"error": "Missing required field: company_id"}

    conditions = {}
    if accepted_only:
        conditions["accepted"] = True

    contracts = []
    
    # Получаем контракты где компания выступает поставщиком
    if as_supplier:
        supplier_contracts_data = await just_db.find('contracts',
                                        supplier_company_id=company_id, **conditions)
        for contract_data in supplier_contracts_data:
            contract = Contract(id=contract_data.get('id', 0))
            contract.load_from_base(contract_data)
            contracts.append(contract)
    
    # Получаем контракты где компания выступает заказчиком
    if as_customer:
        customer_contracts_data = await just_db.find('contracts',
                                        customer_company_id=company_id, **conditions)
        for contract_data in customer_contracts_data:
            contract = Contract(id=contract_data.get('id', 0))
            contract.load_from_base(contract_data)
            contracts.append(contract)

    # Убираем дубликаты (если компания одновременно поставщик и заказчик одного контракта)
    unique_contracts = {contract.id: contract for contract in contracts}
    
    return [contract.to_dict() for contract in unique_contracts.values()]