from .bank_page import BankPage
from .deposit import __deposit__
from .credit import __credit__

__bank__ = [
    BankPage
]

__bank__.extend(__deposit__)
__bank__.extend(__credit__)
