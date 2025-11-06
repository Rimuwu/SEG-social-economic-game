from .contract_create_page import (
	ContractCreateMain,
	ContractCreateSelectCompany,
	ContractCreateSelectResource,
)
from .contract_main_page import ContractMain
from .contract_view_page import ContractViewPage
from .contract_execute_page import ContractExecutePage


__contract__ = [
	ContractCreateMain,
	ContractCreateSelectCompany,
	ContractCreateSelectResource,
	ContractViewPage,
	ContractExecutePage,
	ContractMain,
]