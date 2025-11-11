from typing import Optional, TYPE_CHECKING
from modules.validation import validate_username
from game.stages import leave_from_prison
from global_modules.models.cells import Cells
from modules.generate import generate_number
from modules.websocket_manager import websocket_manager
from global_modules.db.baseclass import BaseClass
from modules.db import just_db
from game.session import SessionObject, SessionStages
from global_modules.load_config import ALL_CONFIGS, Resources, Improvements, Settings, Capital, Reputation
from global_modules.bank import calc_credit, get_credit_conditions, check_max_credit_steps, calc_deposit, get_deposit_conditions, check_max_deposit_steps
from game.factory import Factory
from modules.logs import game_logger

if TYPE_CHECKING:
    from game.user import User
    from game.contract import Contract
    from game.exchange import Exchange

RESOURCES: Resources = ALL_CONFIGS["resources"]
CELLS: Cells = ALL_CONFIGS['cells']
IMPROVEMENTS: Improvements = ALL_CONFIGS['improvements']
SETTINGS: Settings = ALL_CONFIGS['settings']
CAPITAL: Capital = ALL_CONFIGS['capital']
REPUTATION: Reputation = ALL_CONFIGS['reputation']

class Company(BaseClass, SessionObject):

    __tablename__ = "companies"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id
        self.name: str = ""

        self.reputation: int = 0
        self.balance: int = 0
        self.economic_power: int = 0

        self.in_prison: bool = False
        self.prison_end_step: Optional[int] = None
        self.prison_reason: Optional[str] = None

        self.credits: list = []
        self.deposits: list = []

        self.improvements: dict = {}
        self.warehouses: dict = {}

        self.session_id: str = ""
        self.cell_position: str = "" # 3.1

        self.tax_debt: int = 0  # Задолженность по налогам
        self.overdue_steps: int = 0  # Количество просроченных ходов

        self.secret_code: int = 0 # Для вступления другими игроками

        self.last_turn_income: int = 0  # Доход за прошлый ход
        self.this_turn_income: int = 0  # Доход за текущий ход

        self.business_type: str = "small"  # Тип бизнеса: "small" или "big"
        self.owner: int = 0

        self.start_step_capital: int = 0  # Капитал на начало шага

        self.fast_logistic: bool = False
        self.fast_complectation: bool = False
        self.autopay_taxes: bool = False

    async def set_owner(self, user_id: int):
        if self.owner != 0:
            game_logger.warning(f"Попытка установить владельца компании {self.name} ({self.id}), но владелец уже установлен: {self.owner}.")
            raise ValueError("Владелец уже установлен.")

        if user_id in [user.id for user in await self.users] is False:
            game_logger.warning(f"Пользователь {user_id} не является членом компании {self.name} ({self.id}) при попытке назначения владельцем.")
            raise ValueError("Пользователь не является членом компании.")

        self.owner = user_id
        await self.save_to_base()
        game_logger.info(f"Пользователь {user_id} назначен владельцем компании {self.name} ({self.id}).")

    async def create(self, name: str, session_id: str):
        self.name = name

        with_this_name = await just_db.find_one(
            self.__tablename__, name=name, session_id=session_id)

        if with_this_name:
            game_logger.warning(f"Попытка создать компанию с уже существующим именем '{name}' в сессии {session_id}.")
            raise ValueError(f"Компания с именем '{name}' уже существует.")

        self.session_id = session_id
        session = await self.get_session_or_error()

        if not await session.can_add_company():
            raise ValueError("Неактивная сессия для добавления компании.")

        name = validate_username(name)
        self.name = name

        # Генерируем уникальный секретный код
        not_in_use = True
        while not_in_use:
            self.secret_code = generate_number(6)
            if not await just_db.find_one("companies",
                                    secret_code=self.secret_code):
                not_in_use = False

        self.improvements = SETTINGS.start_improvements_level.__dict__

        self.balance = CAPITAL.start
        self.reputation = REPUTATION.start

        await self.insert()
        await websocket_manager.broadcast({
            "type": "api-create_company",
            "data": {
                'session_id': self.session_id,
                'company': await self.to_dict()
            }
        })
        game_logger.info(f"Создана новая компания '{self.name}' ({self.id}) в сессии {self.session_id} с секретным кодом {self.secret_code}.")
        return self

    async def can_user_enter(self):
        session = await self.get_session_or_error()
        if not session or session.stage != "FreeUserConnect":
            return False

        if len(await self.users) >= session.max_players_in_company:
            return False
        return True

    @property
    async def users(self) -> list['User']:
        from game.user import User

        users: list[User] = await just_db.find(
            User.__tablename__, to_class=User, 
            company_id=self.id
        ) # type: ignore
        return users

    async def set_position(self, x: int, y: int, 
                           from_updater: bool = False):
        if isinstance(x, int) is False or isinstance(y, int) is False:
            raise ValueError("Координаты должны быть целыми числами.")

        session = await self.get_session_or_error()
        if not await session.can_select_cell(x, y):
            game_logger.warning(f"Компания {self.name} ({self.id}) не может выбрать клетку ({x}, {y}) в сессии {self.session_id}.")
            raise ValueError("Невозможно выбрать эту клетку - либо она занята, либо находится вне карты.")

        if session.stage != SessionStages.CellSelect.value:
            game_logger.warning(f"Компания {self.name} ({self.id}) пытается изменить позицию на этапе {session.stage}. Возможно подразумевается change_position")
            raise ValueError("Невозможно изменить позицию на данном этапе игры.")

        old_position = self.cell_position
        self.cell_position = f"{x}.{y}"

        await self.save_to_base()
        await self.reupdate()
        game_logger.info(f"Компания {self.name} ({self.id}) установила позицию на клетку ({x}, {y}).")

        # Если все компании выбрали клетки, переходим к следующему этапу
        await session.reupdate()
        if await session.all_companies_have_cells() and not from_updater:
            await session.update_stage(SessionStages.Game)
            await session.save_to_base()

        imps = await self.get_improvements()
        col = imps['factory']['tasksPerTurn']
        col_complect = col // 3
        cell_type: str = await self.get_cell_type() # type: ignore

        for _ in range(col):
            res = None

            if col_complect > 0:
                res = SETTINGS.start_complectation.get(cell_type, None)

            await Factory().create(self.id, res, True)
            col_complect -= 1

        await websocket_manager.broadcast({
            "type": "api-company_set_position",
            "data": {
                "company_id": self.id,
                "old_position": old_position,
                "new_position": self.cell_position
            }
        })
        return True

    def get_position(self):
        if not self.cell_position:
            return None

        try:
            x, y = map(int, self.cell_position.split('.'))
            return (x, y)
        except Exception:
            return None

    async def delete(self):
        await just_db.delete(self.__tablename__, **{self.__unique_id__: self.id})

        for user in await self.users: await user.leave_from_company()
        for factory in await self.get_factories(): await factory.delete()
        for exchange in await self.exchanges: await exchange.delete()
        for contract in await self.get_contracts(): await contract.delete()

        await websocket_manager.broadcast({
            "type": "api-company_deleted",
            "data": {
                "company_id": self.id
            }
        })
        game_logger.info(f"Компания {self.name} ({self.id}) удалена из сессии {self.session_id}.")
        return True

    async def get_max_warehouse_size(self) -> int:
        imps = await self.get_improvements()
        if 'warehouse' not in imps:
            return 0

        base_size = imps['warehouse']['capacity']
        return base_size

    async def get_warehouse_free_size(self) -> int:
        return await self.get_max_warehouse_size() - self.get_resources_amount()

    async def add_resource(self, 
                     resource: str, amount: int, 
                     ignore_space: bool = False,
                     max_space: bool = False
                     ):
        """
            ignore_space - игнорировать проверку места на складе
            max_space - добавить максимально возможное количество
        """
        if RESOURCES.get_resource(resource) is None:
            game_logger.warning(f"Попытка добавить несуществующий ресурс '{resource}' компании {self.name} ({self.id}).")
            raise ValueError(f"Ресурс '{resource}' не существует.")

        if amount <= 0:
            game_logger.warning(f"Попытка добавить отрицательное количество ресурса '{resource}' ({amount}) компании {self.name} ({self.id}).")
            raise ValueError("Количество должно быть положительным целым числом.")

        if not max_space:
            if self.get_resources_amount() + amount > await self.get_max_warehouse_size() and not ignore_space:
                game_logger.warning(f"Недостаточно места на складе компании {self.name} ({self.id}) для добавления {amount} единиц '{resource}'. Свободно: {self.get_warehouse_free_size()}")
                raise ValueError("Недостаточно места на складе.")
        if max_space:
            free_space = await self.get_warehouse_free_size()
            if amount > free_space:
                amount = free_space
            if amount <= 0: return False

        if resource in self.warehouses:
            self.warehouses[resource] += amount
        else:
            self.warehouses[resource] = amount

        await self.save_to_base()
        await websocket_manager.broadcast({
            "type": "api-company_resource_added",
            "data": {
                "company_id": self.id,
                "resource": resource,
                "amount": amount
            }
        })
        game_logger.info(f"Компания {self.name} ({self.id}) получила {amount} единиц ресурса '{resource}'. Всего на складе: {self.warehouses[resource]}")
        return True

    async def remove_resource(self, resource: str, amount: int):
        if RESOURCES.get_resource(resource) is None:
            game_logger.warning(f"Попытка удалить несуществующий ресурс '{resource}' у компании {self.name} ({self.id}).")
            raise ValueError(f"Ресурс '{resource}' не существует.")

        if amount <= 0:
            game_logger.warning(f"Попытка удалить отрицательное количество ресурса '{resource}' ({amount}) у компании {self.name} ({self.id}).")
            raise ValueError("Количество должно быть положительным целым числом.")

        if resource not in self.warehouses or self.warehouses[resource] < amount:
            game_logger.warning(f"Недостаточно ресурса '{resource}' у компании {self.name} ({self.id}) для удаления {amount} единиц. Доступно: {self.warehouses.get(resource, 0)}")
            raise ValueError(f"Недостаточно ресурса '{resource}' для удаления.")

        self.warehouses[resource] -= amount
        if self.warehouses[resource] == 0:
            del self.warehouses[resource]

        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_resource_removed",
            "data": {
                "company_id": self.id,
                "resource": resource,
                "amount": amount
            }
        })
        game_logger.info(f"Компания {self.name} ({self.id}) потратила {amount} единиц ресурса '{resource}'. Осталось: {self.warehouses.get(resource, 0)}")
        return True

    def get_resources_amount(self):
        count = 0
        for amount in self.warehouses.values(): 
            count += amount
        return count

    async def set_economic_power(self, count: int, item: str, e_type: str):
        mod = 1

        if e_type == "production":
            mod = 1
        elif e_type == "exchange":
            mod = 2
        elif e_type == "city_sell":
            mod = 3
        elif e_type == "contract":
            mod = 4

        resource = RESOURCES.get_resource(item)  # type: ignore
        if not resource:
            dif = 0
        else:
            dif = resource.basePrice

        self.economic_power += int(count * dif * mod)
        await self.save_to_base()

    async def get_my_cell_info(self):
        cell_type_key = await self.get_cell_type()
        if not cell_type_key: return None

        result = CELLS.types.get(cell_type_key)
        return result

    async def get_cell_type(self):
        position = self.get_position()

        if not position: return None
        x, y = position

        session = await self.get_session()
        if not session: return None

        index = y * session.map_size["cols"] + x

        if index < 0 or index >= len(session.cells):
            return None
        return session.cells[index]

    async def get_improvements(self):
        """ Возвращает данные улучшений для компании
        """
        cell_type = await self.get_cell_type()
        if cell_type is None: return {}

        data = {}

        for iml_key in self.improvements.keys():
            data[iml_key] = IMPROVEMENTS.get_improvement(
                cell_type, iml_key, str(self.improvements[iml_key])
            ).__dict__

        return data

    async def add_balance(self, amount: int, income_percent: float = 1.0):
        if not isinstance(income_percent, float):
            raise ValueError("Процент дохода должен быть числом с плавающей точкой.")

        if income_percent < 0:
            raise ValueError("Процент дохода должен быть неотрицательным.")

        if not isinstance(amount, int):
            raise ValueError("Сумма должна быть целым числом.")

        if amount <= 0:
            raise ValueError("Сумма должна быть положительным целым числом.")

        old_balance = self.balance
        self.balance += amount
        self.this_turn_income += int(amount * income_percent)

        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_balance_changed",
            "data": {
                "company_id": self.id,
                "old_balance": old_balance,
                "new_balance": self.balance
            }
        })

        game_logger.info(f"Компания {self.name} ({self.id}) получила {amount} денежных средств. Новый баланс: {self.balance}")
        return True

    async def remove_balance(self, amount: int):
        if not isinstance(amount, int):
            raise ValueError("Сумма должна быть целым числом.")

        if amount <= 0:
            raise ValueError("Сумма должна быть положительным целым числом.")

        if self.balance < amount:
            raise ValueError("Недостаточно средств для списания.")

        old_balance = self.balance
        self.balance -= amount
        
        await self.save_to_base()
        await websocket_manager.broadcast({
            "type": "api-company_balance_changed",
            "data": {
                "company_id": self.id,
                "old_balance": old_balance,
                "new_balance": self.balance
            }
        })

        game_logger.info(f"Компания {self.name} ({self.id}) потратила {amount} денежных средств. Новый баланс: {self.balance}")
        return True

    async def improve(self, improvement_type: str):
        """ Улучшает указанное улучшение на 1 уровень, если это возможно.
        """

        self.in_prison_check()

        # my_improvements = self.get_improvements()
        imp_lvl_now = self.improvements.get(
            improvement_type, None)
        cell_type = await self.get_cell_type()

        if cell_type is None:
            raise ValueError("Невозможно определить тип клетки для улучшений.")

        if imp_lvl_now is None:
            raise ValueError(f"Тип улучшения '{improvement_type}' не найден.")

        imp_next_lvl = IMPROVEMENTS.get_improvement(
                cell_type, improvement_type, 
                str(imp_lvl_now + 1)
            )

        if imp_next_lvl is None:
            raise ValueError(f"Нет следующего уровня для улучшения '{improvement_type}'.")

        cost = imp_next_lvl.cost
        await self.remove_balance(cost)

        self.improvements[improvement_type] = imp_lvl_now + 1
        await self.save_to_base()

        if improvement_type == 'factory':
            imp = await self.get_improvements()
            col_need = imp['factory']['tasksPerTurn']
            col_now = len(await self.get_factories())

            for _ in range(col_need - col_now):
                await Factory().create(self.id)

        await websocket_manager.broadcast({
            "type": "api-company_improvement_upgraded",
            "data": {
                "company_id": self.id,
                "improvement_type": improvement_type,
                "new_level": self.improvements[improvement_type]
            }
        })
        return True

    async def add_reputation(self, amount: int):
        if not isinstance(amount, int):
            raise ValueError("Сумма должна быть целым числом.")

        if amount <= 0:
            raise ValueError("Сумма должна быть положительным целым числом.")

        old_reputation = self.reputation
        self.reputation += amount

        await self.save_to_base()
        await websocket_manager.broadcast({
            "type": "api-company_reputation_changed",
            "data": {
                "company_id": self.id,
                "old_reputation": old_reputation,
                "new_reputation": self.reputation
            }
        })

        game_logger.info(f"Репутация компании {self.name} ({self.id}) увеличена на {amount}. Новая репутация: {self.reputation}")
        return True

    async def remove_reputation(self, amount: int, reason: Optional[str] = None):
        if not isinstance(amount, int):
            raise ValueError("Сумма должна быть целым числом.")

        if amount <= 0:
            raise ValueError("Сумма должна быть положительным целым числом.")

        old_reputation = self.reputation
        self.reputation = max(0, self.reputation - amount)

        if self.reputation != old_reputation:

            await self.save_to_base()
            await websocket_manager.broadcast({
                "type": "api-company_reputation_changed",
                "data": {
                    "company_id": self.id,
                    "old_reputation": old_reputation,
                    "new_reputation": self.reputation
                }
            })

            if self.reputation <= REPUTATION.prison.on_reputation: 
                await self.to_prison(
                    "Достигнута критическая репутация для получения санкций. " + (reason or "")
                )

            game_logger.info(f"Репутация компании {self.name} ({self.id}) уменьшена на {amount}, по причине: {reason}. Новая репутация: {self.reputation}")
            return True
        return False

    async def take_credit(self, c_sum: int, steps: int):
        """ 
            Сумма кредита у нас между минимумом и максимумом
            Количество шагов у нас 
        """
        self.in_prison_check()

        if not isinstance(c_sum, int) or not isinstance(steps, int):
            game_logger.warning(f"Компания {self.name} ({self.id}) пытается взять кредит с неверными типами данных: сумма={type(c_sum)}, шаги={type(steps)}")
            raise ValueError("Сумма и шаги должны быть целыми числами.")

        if c_sum <= 0 or steps <= 0:
            game_logger.warning(f"Компания {self.name} ({self.id}) пытается взять кредит с неположительными значениями: сумма={c_sum}, шаги={steps}")
            raise ValueError("Сумма и шаги должны быть положительными целыми числами.")

        if steps <= 1:
            raise ValueError("Нельзя взять кредит на 1 ход")

        credit_condition = get_credit_conditions(self.reputation)
        if not credit_condition.possible:
            game_logger.warning(f"Компания {self.name} ({self.id}) не может взять кредит с текущей репутацией {self.reputation}")
            raise ValueError("Кредит невозможен с текущей репутацией.")

        total, pay_per_turn, extra = calc_credit(
            c_sum, credit_condition.without_interest, credit_condition.percent, steps
            )

        session = await self.get_session_or_error()

        if not check_max_credit_steps(steps, 
                                      session.step, 
                                      session.max_steps):
            game_logger.warning(f"Компания {self.name} ({self.id}) пытается взять кредит на {steps} шагов, что превышает оставшееся время игры")
            raise ValueError("Срок кредита превышает максимальное количество шагов игры.")

        if len(self.credits) >= SETTINGS.max_credits_per_company:
            game_logger.warning(f"Компания {self.name} ({self.id}) достигла максимального количества кредитов ({SETTINGS.max_credits_per_company})")
            raise ValueError("Достигнуто максимальное количество активных кредитов для этой компании.")

        if c_sum > CAPITAL.bank.credit.max:
            game_logger.warning(f"Компания {self.name} ({self.id}) пытается взять кредит {c_sum}, превышающий максимум {CAPITAL.bank.credit.max}")
            raise ValueError(f"Сумма кредита превышает максимальный лимит {CAPITAL.bank.credit.max}.")

        elif c_sum < CAPITAL.bank.credit.min:
            game_logger.warning(f"Компания {self.name} ({self.id}) пытается взять кредит {c_sum}, меньше минимума {CAPITAL.bank.credit.min}")
            raise ValueError(f"Сумма кредита ниже минимального лимита {CAPITAL.bank.credit.min}.")

        credit_data = {
            "total_to_pay": total,
            "need_pay": 0,
            "paid": 0,

            "steps_total": steps,
            "steps_now": 0
        }
        self.credits.append(credit_data)

        await self.save_to_base()
        await self.add_balance(c_sum, 0.0) # деньги без процентов в доход

        await websocket_manager.broadcast({
            "type": "api-company_credit_taken",
            "data": {
                "company_id": self.id,
                "amount": c_sum,
                "steps": steps
            }
        })
        game_logger.info(f"Компания {self.name} ({self.id}) взяла кредит на сумму {c_sum} на {steps} шагов. К доплате: {total}")
        return credit_data

    async def credit_paid_step(self):
        """ Вызывается при каждом шаге игры для компании.
            Начисляет плату по кредитам, если они есть.
        """

        for index, credit in enumerate(self.credits):

            if credit["steps_now"] < credit["steps_total"]:
                steps_left = max(1, credit["steps_total"] - credit["steps_now"])
                credit["need_pay"] += (credit["total_to_pay"] - credit['need_pay'] - credit ['paid']) // steps_left
                credit["steps_now"] += 1

            elif credit["steps_now"] == credit["steps_total"]:
                # Последний день - начисляем всю оставшуюся сумму
                # credit["need_pay"] += credit["total_to_pay"] - credit['paid']
                credit["steps_now"] += 1

            elif credit["steps_now"] > credit["steps_total"]:
                # Просрочка - не увеличиваем steps_now больше, но снижаем репутацию
                await self.remove_reputation(
                    REPUTATION.credit.lost,
                    reason=f"Репутация снижена на {REPUTATION.credit.lost} за просрочку по кредитам."
                    )

            if credit["steps_now"] - credit["steps_total"] > REPUTATION.credit.max_overdue:
                await self.to_prison(
                    reason=f"Превышена максимальная просрочка по кредитам. ({REPUTATION.credit.max_overdue} ходов)"
                )

        await self.save_to_base()

    async def remove_credit(self, credit_index: int):
        """ Удаляет кредит с индексом credit_index.
        """

        if credit_index < 0 or credit_index >= len(self.credits):
            raise ValueError("Недействительный индекс кредита.")

        del self.credits[credit_index]
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_credit_removed",
            "data": {
                "company_id": self.id,
                "credit_index": credit_index
            }
        })
        return True

    async def pay_credit(self, credit_index: int, amount: int):
        """ Платит указанную сумму по кредиту с индексом credit_index.
        """

        self.in_prison_check()

        if not isinstance(credit_index, int) or not isinstance(amount, int):
            raise ValueError("Индекс кредита и сумма должны быть целыми числами.")

        if credit_index < 0 or credit_index >= len(self.credits):
            raise ValueError("Недействительный индекс кредита.")

        if amount <= 0:
            raise ValueError("Сумма должна быть положительным целым числом.")

        if self.balance < amount:
            raise ValueError("Недостаточно средств для оплаты кредита.")

        credit = self.credits[credit_index]

        # if amount < credit["need_pay"]:
        #     raise ValueError(
        #         "Сумма платежа должна быть не менее требуемой для этого хода.")

        # Досрочное закрытие кредита - можно заплатить больше чем need_pay
        remaining_debt = credit["total_to_pay"] - credit["paid"]
        if amount > remaining_debt:
            amount = remaining_debt

        # Снимаем деньги с баланса
        await self.remove_balance(amount)

        # Обновляем информацию по кредиту
        credit["paid"] += amount
        credit["need_pay"] = max(0, credit["need_pay"] - amount)

        # Если кредит полностью выплачен, удаляем его
        if credit["paid"] >= credit["total_to_pay"]:
            await self.remove_credit(credit_index)

            max_credit = CAPITAL.bank.credit.max
            max_rep = REPUTATION.credit.gained
            reputation_gain = int((amount / max_credit) * max_rep)
            await self.add_reputation(
                max(reputation_gain, 1)
            )
        else:
            self.credits[credit_index] = credit
            await self.save_to_base()

        remaining = credit["total_to_pay"] - credit["paid"] if credit["paid"] < credit["total_to_pay"] else 0

        await websocket_manager.broadcast({
            "type": "api-company_credit_paid",
            "data": {
                "company_id": self.id,
                "credit_index": credit_index,
                "amount": amount,
                "remaining": remaining
            }
        })
        return True

    async def to_prison(self, reason: Optional[str] = None):
        """ Сажает компанию в тюрьму за неуплату кредитов
        """

        # Сажается на Х ходов и после шедулером выкидывается с пустой компанией
        session = await self.get_session_or_error()

        end_step = session.step + REPUTATION.prison.stages

        self.in_prison = True
        self.prison_end_step = end_step
        self.prison_reason = reason

        self.reputation = REPUTATION.start
        self.credits = []
        self.deposits = []

        self.tax_debt = 0
        self.overdue_steps = 0
        self.this_turn_income = 0

        for i in await self.get_factories():
            i.is_auto = False
            await i.save_to_base()

        for i in await self.get_contracts():
            await i.delete()

        for i in await self.exchanges:
            await i.delete()

        await self.save_to_base()
        await session.create_step_schedule(
            end_step,
            leave_from_prison,
            session_id=self.session_id,
            company_id=self.id
        )

        await websocket_manager.broadcast({
            "type": "api-company_to_prison",
            "data": {
                "company_id": self.id,
                "end_step": end_step
            }
        })
        game_logger.info(f"Компания {self.name} ({self.id}) отправлена в тюрьму до шага {end_step} в сессии {self.session_id} по причине: {reason}")

    async def leave_prison(self):
        """ Выход из тюрьмы по времени
        """

        if not self.in_prison:
            raise ValueError("Компания не находится в тюрьме.")

        self.in_prison = False
        self.prison_end_step = None
        self.prison_reason = None

        await self.save_to_base()
        await websocket_manager.broadcast({
            "type": "api-company_left_prison",
            "data": {
                "company_id": self.id
            }
        })
        game_logger.info(f"Компания {self.name} ({self.id}) освобождена из тюрьмы в сессии {self.session_id}")
        return True

    def in_prison_check(self):
        """ Находится ли компания в тюрьме (Вызов ошибки для удобства)
        """
        if self.in_prison:
            raise ValueError("Компания уже находится в тюрьме.")

        return self.in_prison

    async def business_tax(self) -> float:
        """ Определяет налоговую ставку в зависимости от типа бизнеса.
        """

        session = await self.get_session_or_error()

        big_mod = session.get_event_effects().get(
            'tax_rate_large', CAPITAL.bank.tax.big_business
        )

        small_mod = session.get_event_effects().get(
            'tax_rate_small', CAPITAL.bank.tax.small_business
        )

        if self.business_type == "big":
            return big_mod
        return small_mod

    async def taxate(self):
        """ Начисляет налоги в зависимости от типа бизнеса. Вызывается каждый ход.
        """

        if self.tax_debt > 0:
            self.overdue_steps += 1
            await self.remove_reputation(
                REPUTATION.tax.late,
                reason=f"Репутация снижена на {REPUTATION.tax.late} за просрочку по налогам."
                )
            game_logger.warning(f"Компания {self.name} ({self.id}) имеет просроченный налоговый долг. Просрочка: {self.overdue_steps} шагов")

        if self.overdue_steps > REPUTATION.tax.not_paid_stages:
            game_logger.warning(f"Компания {self.name} ({self.id}) превысила максимальную просрочку по налогам ({self.overdue_steps} > {REPUTATION.tax.not_paid_stages}). Отправляется в тюрьму")
            self.overdue_steps = 0
            self.tax_debt = 0

            # if self.reputation > 0:
            #     await self.remove_reputation(
            #         self.reputation,
            #         f"Репутация снижена на {self.reputation} за просрочку по налогам."
            #         )

            await self.to_prison(
                reason=f'Превышена максимальная просрочка по налогам. ({REPUTATION.tax.not_paid_stages} ходов)'
            )
            return

        percent = await self.business_tax()
        tax_amount = int(self.last_turn_income * percent)

        self.tax_debt += tax_amount
        await self.save_to_base()


    async def pay_taxes(self, amount: int):
        """ Платит указанную сумму по налогам.
        """

        self.in_prison_check()

        if not isinstance(amount, int):
            raise ValueError("Сумма должна быть целым числом.")

        if amount <= 0:
            raise ValueError("Сумма должна быть положительным целым числом.")

        if self.tax_debt <= 0:
            raise ValueError("Нет налогового долга для оплаты.")

        if self.balance < amount:
            raise ValueError("Недостаточно средств для оплаты налогов.")

        if amount > self.tax_debt: amount = self.tax_debt

        # Снимаем деньги с баланса
        await self.remove_balance(amount)

        # Обновляем информацию по налогам
        self.tax_debt -= amount
        if self.tax_debt <= 0:
            self.tax_debt = 0
            self.overdue_steps = 0
            await self.add_reputation(REPUTATION.tax.paid)

        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_tax_paid",
            "data": {
                "company_id": self.id,
                "amount": amount,
                "remaining": self.tax_debt
            }
        })
        return True

    async def take_deposit(self, d_sum: int, steps: int):
        """ 
            Создаёт вклад на указанную сумму и срок
            d_sum - сумма вклада
            steps - срок вклада в ходах
        """
        self.in_prison_check()

        if not isinstance(d_sum, int) or not isinstance(
                steps, int):
            raise ValueError("Сумма и шаги должны быть целыми числами.")

        if d_sum <= 0 or steps <= 0:
            raise ValueError("Сумма и шаги должны быть положительными целыми числами.")

        deposit_condition = get_deposit_conditions(
            self.reputation)

        if not deposit_condition.possible:
            raise ValueError("Депозит невозможен с текущей репутацией.")

        income_per_turn, total_income = calc_deposit(
            d_sum, deposit_condition.percent, steps
        )

        session = await self.get_session_or_error()

        if not check_max_deposit_steps(steps, 
                                       session.step, 
                                       session.max_steps):
            raise ValueError("Срок депозита превышает максимальное количество шагов игры.")

        if d_sum > CAPITAL.bank.contribution.max:
            raise ValueError(f"Сумма депозита превышает максимальный лимит {CAPITAL.bank.contribution.max}.")

        elif d_sum < CAPITAL.bank.contribution.min:
            raise ValueError(f"Сумма депозита ниже минимального лимита {CAPITAL.bank.contribution.min}.")

        if self.balance < d_sum:
            raise ValueError("Недостаточно средств для создания депозита.")

        deposit_data = {
            "initial_sum": d_sum,
            "current_balance": d_sum,  # Баланс вклада (сумма + накопленные проценты)
            "income_per_turn": income_per_turn,
            "total_earned": 0,  # Сколько уже заработано процентов

            "steps_total": steps,
            "steps_now": 0,
            
            "can_withdraw_from": session.step + 3  # Можно забрать через 3 хода
        }

        # Снимаем деньги с баланса компании
        await self.remove_balance(d_sum)

        self.deposits.append(deposit_data)
        await self.save_to_base()

        game_logger.info(f"Компания {self.name} ({self.id}) создала депозит на сумму {d_sum} на {steps} шагов. Доход в ход: {income_per_turn}, всего к получению: {total_income}")

        await websocket_manager.broadcast({
            "type": "api-company_deposit_taken",
            "data": {
                "company_id": self.id,
                "amount": d_sum,
                "steps": steps
            }
        })
        return deposit_data

    async def deposit_income_step(self):
        """ Вызывается при каждом шаге игры для компании.
            Начисляет доход по вкладам на баланс вклада (не на счёт компании).
            Автоматически снимает депозиты по окончании срока.
        """
        
        session = await self.get_session()
        if not session: return False

        for index, deposit in enumerate(self.deposits):
            if deposit["steps_now"] < deposit["steps_total"]:
                # Начисляем проценты на баланс вклада
                deposit["current_balance"] += deposit["income_per_turn"]
                deposit["total_earned"] += deposit["income_per_turn"]

            deposit["steps_now"] += 1

            # Если срок депозита истек, то снимаем
            if deposit["steps_now"] > deposit["steps_total"]:

                if self.in_prison is False:
                    await self.withdraw_deposit(index)

        await self.save_to_base()

    async def withdraw_deposit(self, deposit_index: int):
        """ Забирает депозит с индексом deposit_index.
            Возвращает всю сумму (начальная + проценты) на счёт компании.
        """
        self.in_prison_check()

        if not isinstance(deposit_index, int):
            raise ValueError("Индекс депозита должен быть целым числом.")
    
        if deposit_index < 0 or deposit_index >= len(
                self.deposits):
            raise ValueError("Недействительный индекс депозита.")

        deposit = self.deposits[deposit_index]

        session = await self.get_session_or_error()

        # Проверяем, можно ли забрать деньги (прошло минимум 3 хода)
        if session.step < deposit["can_withdraw_from"]:
            raise ValueError(f"Нельзя забрать депозит. Доступно с шага {deposit['can_withdraw_from']}.")

        # Возвращаем весь баланс вклада на счёт компании
        amount_to_return = deposit["current_balance"]
        await self.add_balance(amount_to_return, 0.0)  # Деньги без учёта в доходе

        # Удаляем вклад
        del self.deposits[deposit_index]
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_deposit_withdrawn",
            "data": {
                "company_id": self.id,
                "deposit_index": deposit_index,
                "amount": amount_to_return
            }
        })
        return True


    async def raw_in_step(self):
        """ Вызывается при каждом шаге игры для компании.
            Определеяет сколько сырья выдать компании в ход.
        """

        imps = await self.get_improvements()
        if 'station' not in imps:
            return 0

        perturn = imps['station']['productsPerTurn']
        return perturn


    async def get_factories(self) -> list['Factory']:
        """ Возвращает список фабрик компании.
        """
        return [factory for factory in await just_db.find(
            "factories", to_class=Factory, company_id=self.id)] # type: ignore

    async def complect_factory(self, factory_id: int, 
                               resource: str):
        """ Укомплектовать фабрику с указанным ID ресурсом.
            Запускает этап комплектации.
        """

        factory = await Factory(factory_id).reupdate()
        if not factory:
            raise ValueError("Фабрика не найдена.")
        if factory.company_id != self.id:
            raise ValueError("Фабрика не принадлежит этой компании.")

        await factory.pere_complete(resource)

    async def complete_free_factories(self, 
                        find_resource: Optional[str],
                        new_resource: str,
                        count: int,
                        produce_status: bool = False
                        ):
        """ Переукомплектовать фабрики с типом ресурса (без него) на новый ресурс.
            Запускает этап комплектации.
        """

        free_factories: list[Factory] = []
        for f in await self.get_factories():
            if f.complectation == find_resource and f.produce == produce_status:
                free_factories.append(f)

        limit = 0
        for factory in free_factories:
            if limit >= count: break

            limit += 1
            await factory.pere_complete(new_resource)

    async def auto_manufacturing(self, 
                                 factory_id: int, 
                                 status: bool
                                 ):
        """ Включает или выключает авто производство на фабрике с указанным ID.
        """

        factory = await Factory(factory_id).reupdate()
        if not factory:
            raise ValueError("Фабрика не найдена.")

        if factory.company_id != self.id:
            raise ValueError("Фабрика не принадлежит этой компании.")

        await factory.set_auto(status)

    async def factory_set_produce(self, factory_id: int, produce: bool):
        """ Включает или выключает производство на фабрике с указанным ID.
        """

        factory = await Factory(factory_id).reupdate()
        if not factory:
            raise ValueError("Фабрика не найдена.")
        if factory.company_id != self.id:
            raise ValueError("Фабрика не принадлежит этой компании.")

        await factory.set_produce(produce)

    async def get_contracts(self) -> list['Contract']:
        """ Получает все контракты компании """
        from game.contract import Contract

        contracts: list[Contract] = await just_db.find(
            Contract.__tablename__, to_class=Contract,
            supplier_company_id=self.id
        ) # type: ignore

        contracts += await just_db.find(
            Contract.__tablename__, to_class=Contract,
            customer_company_id=self.id
        ) # type: ignore

        return contracts

    async def get_max_contracts(self) -> int:
        """ Получает максимальное количество активных контрактов """
        contracts_level = str(
            self.improvements.get('contracts', 1)
        )
        contracts_config = IMPROVEMENTS.contracts.levels[
            contracts_level
        ]
        
        session = await self.get_session_or_error()
        
        try:
            mx_c = contracts_config.max

            minus = session.get_event().get(
                'contracts_limit_decrease', 0)

            return mx_c - minus
        except Exception as e:
            game_logger.error(f"Ошибка при получении максимального количества контрактов для компании {self.name} ({self.id}): {e}")
            return 5

    async def can_create_contract(self) -> bool:
        """ Проверяет, может ли компания создать новый контракт """

        return len(await self.get_contracts()
                   ) < await self.get_max_contracts()

    async def on_new_game_stage(self, step: int):
        """ Вызывается при переходе на новый игровой этап.
            Обновляет доходы, списывает налоги и т.д.
        """
        from game.contract import Contract

        self.start_step_capital = self.balance

        self.last_turn_income = self.this_turn_income
        self.this_turn_income = 0

        session = await self.get_session_or_error()

        # Определяем тип бизнеса
        if step != 1:
            if self.last_turn_income >= CAPITAL.bank.tax.big_on:
                self.business_type = "big"
                await self.save_to_base()

        # Начисляем проценты по вкладам
        try:
            await self.deposit_income_step()
        except Exception as e:
            game_logger.error(f"Ошибка при начислении процентов по вкладам для компании {self.name} ({self.id}): {e}")

        # Начисляем плату по кредитам
        try:
            await self.credit_paid_step()
        except Exception as e:
            game_logger.error(f"Ошибка при начислении платы по кредитам для компании {self.name} ({self.id}): {e}")

        # Начисляем налоги
        try:
            await self.taxate()
        except Exception as e:
            game_logger.error(f"Ошибка при начислении налогов для компании {self.name} ({self.id}): {e}")

        cell_info = await self.get_my_cell_info()
        if cell_info:
            resource_id = cell_info.resource_id

            mod = session.get_event_effects().get(
                'resource_extraction_speed', 1.0
            )

            cell_type = await self.get_cell_type()
            if session.get_event().get('cell_type') == cell_type:
                mod *= session.get_event().get('income_multiplier', 1.0)

            raw_col = int(await self.raw_in_step() * mod)

            if resource_id and raw_col > 0:
                await self.add_resource(
                        resource_id, raw_col,
                        max_space=True
                )
                game_logger.info(f"Компания {self.name} ({self.id}) добыла {raw_col} единиц ресурса '{resource_id}' на шаге {step}")


        factories = await self.get_factories()
        for factory in factories:
            try:
                await factory.on_new_game_stage()
            except Exception as e:
                game_logger.error(f"Ошибка при обновлении фабрики {factory.id} для компании {self.name} ({self.id}): {e}")

        # contracts = await self.get_contracts()
        # for contract in contracts:
        #     try:
        #         await contract.on_new_game_step()
        #     except Exception as e:
        #         game_logger.error(f"Ошибка при обновлении контракта {contract.id} для компании {self.name} ({self.id}): {e}")

    @property
    async def exchanges(self) -> list['Exchange']:
        from game.exchange import Exchange

        exchanges: list[Exchange] = await just_db.find(
            Exchange.__tablename__, to_class=Exchange,
            company_id = self.id,
            session_id = self.session_id
        ) # type: ignore

        return exchanges

    async def to_dict(self):
        """Возвращает полный статус компании со всеми данными"""
        
        cell_data = await self.get_my_cell_info()
        
        return {
            # Основная информация
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "session_id": self.session_id,
            "secret_code": self.secret_code,

            # Финансовые данные
            "balance": self.balance,
            "last_turn_income": self.last_turn_income,
            "this_turn_income": self.this_turn_income,
            "business_type": self.business_type,
            "economic_power": self.economic_power,

            # Репутация и статус
            "reputation": self.reputation,
            "in_prison": self.in_prison,
            "prison_end_step": self.prison_end_step,
            "prison_reason": self.prison_reason,

            # Позиция и местоположение
            "cell_position": self.cell_position,
            "position_coords": self.get_position(),
            "cell_type": await self.get_cell_type(),
            "cell_info": cell_data.__dict__ if await self.get_my_cell_info() else None,

            # Налоги
            "tax_debt": self.tax_debt,
            "overdue_steps": self.overdue_steps,
            "tax_rate": await self.business_tax(),
            
            # Кредиты и депозиты
            "credits": self.credits,
            "deposits": self.deposits,

            # Улучшения и ресурсы
            "improvements": self.improvements,
            "improvements_data": await self.get_improvements(),
            "warehouses": self.warehouses,
            "warehouse_capacity": await self.get_max_warehouse_size(),
            "warehouse_free_size": await self.get_warehouse_free_size(),
            "resources_amount": self.get_resources_amount(),
            "raw_per_turn": await self.raw_in_step(),

            # Пользователи и фабрики
            "users": [user.to_dict() for user in await self.users],
            "factories": [await factory.to_dict() for factory in await self.get_factories()],
            "factories_count": len(await self.get_factories()),

            # Дополнительные возможности
            "can_user_enter": await self.can_user_enter(),

            "exchanges": [
                change.to_dict() for change in await self.exchanges
            ],

            "contracts": [
                contract.to_dict() for contract in await self.get_contracts()
            ],

            "fast_complectation": self.fast_complectation,
            "fast_logistic": self.fast_logistic,
            "autopay_taxes": self.autopay_taxes,

            "profit": self.profit,
            "start_step_capital": self.start_step_capital
        }

    async def set_fast_logistic(self): 
        if self.fast_logistic:
            raise ValueError("Компания уже имеет быструю логистику.")

        upgrade_price = SETTINGS.fast_logistic_price
        await self.remove_balance(upgrade_price)

        self.fast_logistic = True
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_fast_logistic_set",
            "data": {
                "company_id": self.id,
                "fast_logistic": self.fast_logistic
            }
        })

    async def set_fast_complectation(self):
        if self.fast_complectation:
            raise ValueError("Компания уже имеет быструю комплектацию.")

        upgrade_price = SETTINGS.fast_complectation_price
        await self.remove_balance(upgrade_price)

        self.fast_complectation = True
        await self.save_to_base()
        
        await websocket_manager.broadcast({
            "type": "api-company_fast_complectation_set",
            "data": {
                "company_id": self.id,
                "fast_complectation": self.fast_complectation
            }
        })

    async def change_position(self, x: int, y: int):

        change_price = SETTINGS.change_location_price
        business_type = self.business_type

        assert isinstance(x, int) and isinstance(y, int), "Координаты должны быть целыми числами."

        session = await self.get_session_or_error()
        if not await session.can_select_cell(x, y, True):
            game_logger.warning(
                f"Компания {self.name} ({self.id}) не может выбрать клетку ({x}, {y}) в сессии {self.session_id}."
                )
            raise ValueError("Невозможно выбрать эту клетку - либо она занята, либо находится вне карты.")

        price = change_price.get(business_type, 100_000)
        await self.remove_balance(price)

        old_position = self.cell_position
        self.cell_position = f"{x}.{y}"

        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_set_position",
            "data": {
                "company_id": self.id,
                "old_position": old_position,
                "new_position": self.cell_position
            }
        })

    @property
    def profit(self) -> int:
        """ Возвращает прибыль компании за последний ход. """
        profit = self.balance - self.start_step_capital
        return profit

    async def set_autopay_taxes(self):
        """ Разовое улучшение автоматической уплаты налогов. """

        await self.remove_balance(SETTINGS.tax_autopay_price)

        self.autopay_taxes = True
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-company_set_autopay_taxes",
            "data": {
                "company_id": self.id
            }
        })