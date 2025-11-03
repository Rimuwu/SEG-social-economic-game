from game.session import SessionObject
from global_modules.db.baseclass import BaseClass
from modules.db import just_db
from global_modules.load_config import ALL_CONFIGS, Resources, Improvements, Reputation
from modules.function_way import *
from modules.websocket_manager import websocket_manager
from modules.logs import game_logger

RESOURCES: Resources = ALL_CONFIGS["resources"]
IMPROVEMENTS: Improvements = ALL_CONFIGS['improvements']
REPUTATION: Reputation = ALL_CONFIGS['reputation']

class Contract(BaseClass, SessionObject):
    """ Контракт между компаниями
        
        X товара типа Z за Y монет каждый ход
        
        Жизненный цикл контракта:
        1. Создание (create) - контракт создается без оплаты с accepted=False
        2. Принятие (accept_contract) с полной оплатой или отклонение (decline_contract)
        3. Выполнение (execute_turn) каждый ход - только если принят
        4. При неудаче поставки - если за ход не выполнены этап поставки, отмена с возвратом части денег и штрафом репутации
        5. При успешном завершении - удаление и повышение репутации
        6. Непринятые контракты удаляются в конце хода

    """

    __tablename__ = "contracts"
    __unique_id__ = "id"
    __db_object__ = just_db

    def __init__(self, id: int = 0):
        self.id: int = id

        self.supplier_company_id: int = 0  # Компания-поставщик
        self.customer_company_id: int = 0  # Компания-заказчик
        self.session_id: str = ""  # Сессия, в которой создан контракт

        self.who_creator: int = 0  # Кто создал контракт (ID компании)

        # Что поставляется
        self.resource: str = ""  # Тип ресурса
        self.amount_per_turn: int = 0  # Количество за ход

        # Условия оплаты (только монеты)
        self.payment_amount: int = 0  # Сумма денег

        # Параметры контракта
        self.duration_turns: int = 0  # Длительность в ходах
        self.created_at_step: int = 0  # Ход создания
        self.accepted: bool = False  # Принял ли поставщик контракт
        self.delivered_this_turn: bool = False  # Отправлен ли продукт в текущем ходу

        self.successful_deliveries: int = 0  # Количество успешных поставок

    async def create(self, 
               supplier_company_id: int, 
               customer_company_id: int, 
               session_id: str, who_creator: int,
               resource: str, amount_per_turn: int, duration_turns: int, payment_amount: int
               ):
        """ Создание нового контракта

        Args:
            supplier_company_id: ID компании-поставщика
            customer_company_id: ID компании-заказчика  
            session_id: ID сессии
            resource: Тип ресурса для поставки
            amount_per_turn: Количество за ход
            duration_turns: Длительность в ходах
            payment_amount: Сумма денег за контракт
            who_creator: Кто создал контракт (ID компании)
        """
        from game.company import Company
        
        # Валидация
        if amount_per_turn <= 0 or duration_turns <= 0:
            raise ValueError("Количество и длительность должны быть положительными")

        if payment_amount <= 0:
            raise ValueError("Сумма оплаты должна быть положительной")

        if RESOURCES.get_resource(resource) is None:
            raise ValueError(f"Ресурс {resource} не существует")

        if supplier_company_id == customer_company_id:
            raise ValueError("Компания не может заключить контракт с самой собой")

        supplier = await Company(id=supplier_company_id).reupdate()
        customer = await Company(id=customer_company_id).reupdate()

        if not supplier or not customer:
            raise ValueError("Одна из компаний не найдена")

        creator = await Company(id=who_creator).reupdate()
        if all([
                creator is not None, 
                not await creator.can_create_contract()
            ]):
            raise ValueError("У вас максимальное количество контрактов.")

        self.session_id = session_id
        session = await self.get_session_or_error()

        self.supplier_company_id = supplier_company_id
        self.customer_company_id = customer_company_id

        self.resource = resource
        self.amount_per_turn = amount_per_turn
        self.payment_amount = payment_amount

        self.duration_turns = duration_turns
        self.created_at_step = session.step
    
        self.accepted = False  # По умолчанию контракт не принят
        self.delivered_this_turn = False  # Продукт не отправлен в текущем ходу

        self.who_creator = who_creator

        await self.insert()
        await websocket_manager.broadcast({
            "type": "api-contract_created",
            "data": {
                "session_id": self.session_id,
                "contract": self.to_dict()
            }
        })

        return self

    async def execute_turn(self):
        """ Выполнение поставки за текущий ход """
        from game.company import Company
        from game.logistics import Logistics
        
        session = await self.get_session_or_error()

        if not self.accepted:
            raise ValueError("Контракт не принят")

        if self.delivered_this_turn:
            raise ValueError("Продукт уже отправлен в этом ходе")

        supplier = await Company(id=self.supplier_company_id
                           ).reupdate()
        customer = await Company(id=self.customer_company_id
                           ).reupdate()

        if not supplier or not customer:
            # Отменяем контракт с возвратом
            await self.delete()
            return False

        # Проверяем наличие ресурса у поставщика
        supplier_resource_amount = supplier.warehouses.get(
            self.resource, 0
            )

        if supplier_resource_amount < self.amount_per_turn:
            raise ValueError("У поставщика недостаточно ресурса для выполнения контракта")

        try:
            await Logistics().create(
                from_company_id=supplier.id,
                to_company_id=customer.id,
                resource_type=self.resource,
                amount=self.amount_per_turn,
                session_id=self.session_id
            )

            self.successful_deliveries += 1
            self.delivered_this_turn = True

            # Если это была последняя поставка
            if self.duration_turns == self.successful_deliveries:
                # Добавляем репутацию за успешное выполнение
                await supplier.add_reputation(
                    REPUTATION.contract.completed
                )
                await customer.add_reputation(
                    REPUTATION.contract.completed
                )

                creator_company = await Company(id=self.who_creator).reupdate()
                if creator_company is not None:
                    await creator_company.set_economic_power(
                        self.amount_per_turn, self.resource, 'contract'
                    )

                await self.delete()
                return True

            await self.save_to_base()
            await websocket_manager.broadcast({
                "type": "api-contract_executed",
                "data": {
                    "session_id": self.session_id,
                    "contract_id": self.id,
                    "success": True,
                    "step": session.step
                }
            })
            return True

        except ValueError as e: 
            game_logger.error(f"Ошибка при выполнении контракта: {self.id}: {e}")
            raise ValueError("Ошибка при выполнении контракта")

    async def accept_contract(self, who_accepter: int):
        """ Принятие контракта поставщиком """
        if self.accepted:
            raise ValueError("Контракт уже принят")

        if self.successful_deliveries > 0:
            raise ValueError("Контракт уже начал выполняться")

        if self.who_creator == who_accepter:
            raise ValueError("Нельзя принять контракт, который вы создали")

        # Проверяем и снимаем полную оплату с заказчика
        from game.company import Company

        supplier = await Company(id=self.supplier_company_id
                           ).reupdate()
        customer = await Company(id=self.customer_company_id
                           ).reupdate()
        
        if not supplier or not customer:
            raise ValueError("Одна из компаний не найдена")

        if customer.balance < self.payment_amount:
            raise ValueError("У заказчика недостаточно средств для оплаты контракта")
        
        try:
            await customer.remove_balance(self.payment_amount)
            await supplier.add_balance(self.payment_amount)
        except ValueError as e:
            raise ValueError(f"Ошибка оплаты: {e}")

        self.accepted = True
        await self.save_to_base()

        await websocket_manager.broadcast({
            "type": "api-contract_accepted",
            "data": {
                "session_id": self.session_id,
                "contract_id": self.id
            }
        })
        
        return self

    async def decline_contract(self, who_decliner: int):
        """ Отклонение контракта поставщиком """
        if self.accepted:
            raise ValueError("Нельзя отклонить уже принятый контракт")

        if self.successful_deliveries > 0:
            raise ValueError("Контракт уже начал выполняться")

        if self.who_creator == who_decliner:
            raise ValueError("Нельзя отклонить контракт, который вы создали")

        await websocket_manager.broadcast({
            "type": "api-contract_declined",
            "data": {
                "session_id": self.session_id,
                "contract_id": self.id
            }
        })

        await self.delete()
        return self

    async def cancel_with_refund(self, who_canceller: int):
        """ Отмена контракта с возвратом части денег и штрафом репутации """
        from game.company import Company
        
        if not self.accepted:
            raise ValueError("Контракт не принят, чтобы его отменить")
        
        if self.who_creator != who_canceller:
            raise ValueError("Нельзя отменить контракт, если вы его не создавали")
        
        supplier = await Company(id=self.supplier_company_id).reupdate()
        customer = await Company(id=self.customer_company_id).reupdate()

        not_executed = self.duration_turns - self.successful_deliveries

        if supplier and customer:
            # Возвращаем деньги за оставшиеся поставки
            if not_executed <= 0:
                refund_amount = 0
            else:
                refund_amount = self.payment_amount // not_executed

            try:
                if supplier.balance >= refund_amount:
                    await supplier.remove_balance(refund_amount)
                    await customer.add_balance(refund_amount)
                # Штраф репутации за невыполнение
                await supplier.remove_reputation(
                    REPUTATION.contract.failed
                )
            except ValueError:
                # Если не удалось вернуть деньги - больший штраф
                await supplier.remove_reputation(
                    REPUTATION.contract.failed * 2
                    )

        await websocket_manager.broadcast({
            "type": "api-contract_cancelled",
            "data": {
                "session_id": self.session_id,
                "contract_id": self.id,
                "reason": "Поставщик не смог выполнить поставку"
            }
        })

        await self.delete()
        return self

    async def on_new_game_step(self):
        """ Проверка контракта при новом ходе

            Сбрасывает статус доставки
            Удаляет непринятые контракты в конце хода
        """
        # Если контракт не принят в конце хода - удаляем
        if not self.accepted:
            await websocket_manager.broadcast({
                "type": "api-contract_expired",
                "data": {
                    "session_id": self.session_id,
                    "contract_id": self.id,
                    "reason": "Контракт не был принят до конца хода"
                }
            })

            await self.delete()
            return True  # Контракт удален

        else:
            if not self.delivered_this_turn:
                # Отменяем контракт с возвратом части денег и штрафом репутации
                await self.cancel_with_refund(self.who_creator)
                return True

            self.delivered_this_turn = False
            await self.save_to_base()
            return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "supplier_company_id": self.supplier_company_id,
            "customer_company_id": self.customer_company_id,
            "who_creator": self.who_creator,
            "session_id": self.session_id,
            "resource": self.resource,
            "amount_per_turn": self.amount_per_turn,
            "payment_amount": self.payment_amount,
            "duration_turns": self.duration_turns,
            "created_at_step": self.created_at_step,
            "accepted": self.accepted,
            "delivered_this_turn": self.delivered_this_turn
        }

    async def delete(self):
        await just_db.delete(self.__tablename__, id=self.id)

        await websocket_manager.broadcast({
            "type": "api-contract_deleted",
            "data": {
                    "session_id": self.session_id,
                    "contract_id": self.id
                }
            })