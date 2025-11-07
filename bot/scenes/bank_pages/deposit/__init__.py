from .bank_deposit_main import BankDepositMain
from .bank_deposit_view import BankDepositView
from .bank_deposit_open import BankDepositOpenAmount, BankDepositOpenPeriod, BankDepositOpenConfirm

__deposit__ = [
    BankDepositMain,
    BankDepositView,
    BankDepositOpenAmount,
    BankDepositOpenPeriod,
    BankDepositOpenConfirm
]
