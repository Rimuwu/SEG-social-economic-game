from typing import Dict, List, Optional

from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery
from modules.ws_client import (
    get_contracts,
    get_company,
    execute_contract,
    cancel_contract,
    decline_contract
)
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ContractExecutePage(OneUserPage):
    """Страница выполнения принятых контрактов."""

    __page_name__ = "contract-execute-page"
    __for_blocked_pages__ = ["contract-main-page"]

    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
        if self.scene.get_key(self.__page_name__, "selected_contract_id") is None:
            await self.scene.update_key(self.__page_name__, "selected_contract_id", None)
        if self.scene.get_key(self.__page_name__, "error") is None:
            await self.scene.update_key(self.__page_name__, "error", None)
        # Предзагрузка и кэширование списка контрактов для выполнения
        contracts = await self._build_contracts_list()
        await self.scene.update_key(self.__page_name__, "contracts_list_execute", contracts)

    async def content_worker(self):
        self.clear_content()
        await self._ensure_contracts_loaded()
        contracts = self.scene.get_key(self.__page_name__, "contracts_list_execute") or []
        selected_id = self.scene.get_key(self.__page_name__, "selected_contract_id")

        if selected_id and not any(c.get("id") == selected_id for c in contracts):
            await self.scene.update_key(self.__page_name__, "selected_contract_id", None)
            selected_id = None

        if not contracts:
            overview_text = "Нет контрактов, готовых к выполнению."
            details_text = ""
        else:
            lines = []
            for contract in contracts:
                marker = "▶️" if contract.get("id") == selected_id else "•"
                lines.append(
                    f"{marker} #{contract.get('id')} — {contract.get('resource_label')}"
                )

            overview_text = "Выберите контракт для выполнения:\n" + "\n".join(lines)

            if selected_id:
                selected_contract = next(
                    (c for c in contracts if c.get("id") == selected_id),
                    None,
                )
                if selected_contract:
                    details_text = "\n\n" + self._format_contract_details(selected_contract)
                else:
                    details_text = ""
            else:
                details_text = "\n\nВыберите контракт для выполнения."

        error = self.scene.get_key(self.__page_name__, "error")
        error_text = f"\n\n❌ Ошибка: {error}" if error else ""

        return self.content.format(
            overview_text=overview_text,
            details_text=details_text,
            error_text=error_text,
        )

    async def buttons_worker(self):
        await self._ensure_contracts_loaded()
        contracts = self.scene.get_key(self.__page_name__, "contracts_list_execute") or []
        selected_id = self.scene.get_key(self.__page_name__, "selected_contract_id")
        page_index = self.scene.get_key(self.__page_name__, "page") or 0

        items_per_page = 5
        total_pages = max(1, (len(contracts) + items_per_page - 1) // items_per_page)
        page_index %= total_pages
        await self.scene.update_key(self.__page_name__, "page", page_index)

        start = page_index * items_per_page
        end = start + items_per_page
        page_contracts = contracts[start:end]

        buttons = []
        self.row_width = 1

        if not page_contracts:
            buttons.append(
                {
                    "text": "Контракты отсутствуют",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "refresh_contracts"
                    ),
                    "ignore_row": True,
                }
            )
        else:
            for contract in page_contracts:
                marker = "▶️" if contract.get("id") == selected_id else "•"
                text = (
                    f"{marker} #{contract.get('id')} — {contract.get('resource_label')}"
                )
                buttons.append(
                    {
                        "text": text,
                        "callback_data": callback_generator(
                            self.scene.__scene_name__,
                            "select_contract",
                            str(contract.get("id")),
                        ),
                        "ignore_row": True,
                    }
                )

        if len(contracts) > items_per_page:
            self.row_width = 3
            buttons.append(
                {
                    "text": "◀️ Назад",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "contracts_prev_page"
                    ),
                }
            )
            buttons.append(
                {
                    "text": f"📄 {page_index + 1}/{total_pages}",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "contracts_page_info"
                    ),
                }
            )
            buttons.append(
                {
                    "text": "Вперёд ▶️",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "contracts_next_page"
                    ),
                }
            )

        self.row_width = 2
        buttons.append(
            {
                "text": "🔄 Обновить",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "refresh_contracts"
                ),
                "ignore_row": True,
            }
        )

        if selected_id and any(c.get("id") == selected_id for c in contracts):
            buttons.append(
                {
                    "text": "🚚 Выполнить",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "execute_contract", str(selected_id)
                    ),
                }
            )
            buttons.append(
                {
                    "text": "❌ Отменить",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "cancel_contract", str(selected_id)
                    ),
                }
            )

        buttons.append({
            "text": "↪️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_page_main"),
            "ignore_row": True
        })
        
        return buttons

    @OneUserPage.on_callback("back_page_main")
    async def back_pagess(self, callback, args):
        await self.scene.update_key(self.__page_name__, "contracts_list_execute", None)
        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_page("contract-main-page")
    
    @OneUserPage.on_callback("select_contract")
    async def select_contract(self, callback: CallbackQuery, args: List[str]):
        if len(args) < 2:
            await callback.answer("Некорректный выбор", show_alert=True)
            return

        try:
            contract_id = int(args[1])
        except ValueError:
            await callback.answer("Некорректный идентификатор", show_alert=True)
            return

        await self.scene.update_key(self.__page_name__, "selected_contract_id", contract_id)
        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_message()

    @OneUserPage.on_callback("contracts_next_page")
    async def next_page(self, callback: CallbackQuery, args: List[str]):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        await self._ensure_contracts_loaded()
        contracts = self.scene.get_key(self.__page_name__, "contracts_list_execute") or []
        items_per_page = 5
        total_pages = max(1, (len(contracts) + items_per_page - 1) // items_per_page)
        await self.scene.update_key(
            self.__page_name__, "page", (page_index + 1) % total_pages
        )
        await self.scene.update_message()

    @OneUserPage.on_callback("contracts_prev_page")
    async def prev_page(self, callback: CallbackQuery, args: List[str]):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        await self._ensure_contracts_loaded()
        contracts = self.scene.get_key(self.__page_name__, "contracts_list_execute") or []
        items_per_page = 5
        total_pages = max(1, (len(contracts) + items_per_page - 1) // items_per_page)
        await self.scene.update_key(
            self.__page_name__, "page", (page_index - 1) % total_pages
        )
        await self.scene.update_message()

    @OneUserPage.on_callback("contracts_page_info")
    async def page_info(self, callback: CallbackQuery, args: List[str]):
        await callback.answer("Страницы контрактов")

    @OneUserPage.on_callback("refresh_contracts")
    async def refresh_contracts(self, callback: CallbackQuery, args: List[str]):
        await self.scene.update_key(self.__page_name__, "contracts_list_execute", None)
        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_message()
        await callback.answer("Данные обновлены")

    @OneUserPage.on_callback("execute_contract")
    async def execute_contract_handler(self, callback: CallbackQuery, args: List[str]):
        contract_id = await self._extract_selected_contract(args)
        if contract_id is None:
            await callback.answer("Контракт не выбран", show_alert=True)
            return
        await self._ensure_contracts_loaded()
        contracts = self.scene.get_key(self.__page_name__, "contracts_list_execute") or []
        contract = next((c for c in contracts if c.get("id") == contract_id), None)
        if contract is None:
            await callback.answer("Контракт не найден", show_alert=True)
            return

        company_id = self._get_company_id()
        if company_id is None or contract.get("supplier_company_id") != company_id:
            await callback.answer("Этот контракт принадлежит другой компании", show_alert=True)
            return

        response = await execute_contract(contract_id=contract_id)
        if isinstance(response, dict) and response.get("error"):
            error_message = str(response.get("error"))
            await self.scene.update_key(self.__page_name__, "error", error_message)
            await self.scene.update_message()
            await callback.answer(error_message, show_alert=True)
            return

        await self.scene.update_key(self.__page_name__, "contracts_list_execute", None)
        await self.scene.update_key(self.__page_name__, "selected_contract_id", None)
        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_message()

        if isinstance(response, dict) and response.get("contract_completed"):
            await callback.answer("✅ Контракт полностью выполнен", show_alert=True)
        else:
            await callback.answer("✅ Поставка выполнена", show_alert=True)

    @OneUserPage.on_callback("cancel_contract")
    async def cancel_contract_handler(self, callback: CallbackQuery, args: List[str]):
        contract_id = await self._extract_selected_contract(args)
        if contract_id is None:
            await callback.answer("Контракт не выбран", show_alert=True)
            return
        await self._ensure_contracts_loaded()
        contracts = self.scene.get_key(self.__page_name__, "contracts_list_execute") or []
        contract = next((c for c in contracts if c.get("id") == contract_id), None)
        if contract is None:
            await callback.answer("Контракт не найден", show_alert=True)
            return

        company_id = self._get_company_id()
        if company_id is None:
            await callback.answer("Компания не найдена", show_alert=True)
            return

        response = await decline_contract(contract_id=contract_id, who_decliner=company_id)
        if isinstance(response, dict) and response.get("error"):
            error_message = str(response.get("error"))
            await self.scene.update_key(self.__page_name__, "error", error_message)
            await self.scene.update_message()
            await callback.answer(error_message, show_alert=True)
            return

        await self.scene.update_key(self.__page_name__, "contracts_list_execute", None)
        await self.scene.update_key(self.__page_name__, "selected_contract_id", None)
        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_message()
        await callback.answer("Контракт отменён", show_alert=True)
        # Инвалидация связанных страниц: мои контракты
        await self.scene.update_key("contract-view-my-page", "contracts_list_my", None)

    async def _ensure_contracts_loaded(self):
        if self.scene.get_key(self.__page_name__, "contracts_list_execute") is None:
            contracts = await self._build_contracts_list()
            await self.scene.update_key(self.__page_name__, "contracts_list_execute", contracts)

    async def _build_contracts_list(self) -> List[Dict]:
        scene_data = self.scene.get_data("scene")
        session_id = scene_data.get("session")
        company_id_raw = scene_data.get("company_id")

        try:
            company_id = int(company_id_raw) if company_id_raw is not None else None
        except (TypeError, ValueError):
            company_id = None

        if session_id is None or company_id is None:
            return []

        response = await get_contracts(session_id=session_id)
        if isinstance(response, dict) and response.get("error"):
            await self.scene.update_key(self.__page_name__, "error", str(response.get("error")))
            return []

        contracts_raw = response if isinstance(response, list) else []

        company_cache: Dict[int, str] = {}
        filtered: List[Dict] = []

        for contract in contracts_raw:
            if not isinstance(contract, dict):
                continue

            try:
                contract_id = int(contract.get("id"))
                supplier_id = int(contract.get("supplier_company_id"))
                customer_id = int(contract.get("customer_company_id"))
            except (TypeError, ValueError):
                continue

            accepted = bool(contract.get("accepted"))
            delivered_this_turn = bool(contract.get("delivered_this_turn"))

            if not accepted:
                continue

            if supplier_id != company_id:
                continue

            resource_id = contract.get("resource")
            resource_obj = RESOURCES.get_resource(resource_id) if resource_id else None
            resource_label = (
                f"{resource_obj.emoji} {resource_obj.label}" if resource_obj else str(resource_id)
            )

            supplier_name = await self._get_company_name(supplier_id, company_cache)
            customer_name = await self._get_company_name(customer_id, company_cache)
            creator_id = contract.get("who_creator")
            creator_name = await self._get_company_name(
                int(creator_id) if creator_id is not None else None,
                company_cache,
            )

            filtered.append(
                {
                    "id": contract_id,
                    "supplier_company_id": supplier_id,
                    "supplier_company_name": supplier_name,
                    "customer_company_id": customer_id,
                    "customer_company_name": customer_name,
                    "resource_id": resource_id,
                    "resource_label": resource_label,
                    "amount_per_turn": contract.get("amount_per_turn"),
                    "duration_turns": contract.get("duration_turns"),
                    "payment_amount": contract.get("payment_amount"),
                    "creator_id": creator_id,
                    "creator_name": creator_name,
                    "delivered_this_turn": delivered_this_turn
                }
            )

        filtered.sort(key=lambda item: item.get("id", 0))
        return filtered

    async def _get_company_name(
        self, company_id: Optional[int], cache: Dict[int, str]
    ) -> str:
        if company_id is None:
            return "Неизвестно"

        if company_id in cache:
            return cache[company_id]

        company_data = await get_company(id=company_id)
        if isinstance(company_data, dict):
            name = company_data.get("name") or f"Компания #{company_id}"
        else:
            name = f"Компания #{company_id}"

        cache[company_id] = name
        return name

    async def _extract_selected_contract(self, args: List[str]) -> Optional[int]:
        if len(args) >= 2:
            try:
                return int(args[1])
            except ValueError:
                return None

        selected_id = self.scene.get_key(self.__page_name__, "selected_contract_id")
        try:
            return int(selected_id) if selected_id is not None else None
        except (TypeError, ValueError):
            return None

    def _get_company_id(self) -> Optional[int]:
        scene_data = self.scene.get_data("scene")
        company_id_raw = scene_data.get("company_id")
        try:
            return int(company_id_raw) if company_id_raw is not None else None
        except (TypeError, ValueError):
            return None

    def _format_contract_details(self, contract: Dict) -> str:
        amount = contract.get("amount_per_turn")
        duration = contract.get("duration_turns")
        payment = contract.get("payment_amount")
        delivered_this_turn = contract.get("delivered_this_turn")

        amount_text = str(amount) if amount is not None else "-"
        duration_text = str(duration) if duration is not None else "-"
        payment_text = str(payment) if payment is not None else "-"

        details = [
            f"🔢 Контракт #{contract.get('id')}",
            f"📦 Ресурс: {contract.get('resource_label')}",
            f"🏭 Поставщик: {contract.get('supplier_company_name')}",
            f"🏬 Покупатель: {contract.get('customer_company_name')}",
            f"📈 Количество за ход: {amount_text}",
            f"⏱️ Длительность: {duration_text} ходов",
            f"💰 Цена: {payment_text}",
            f"🛠️ Создатель: {contract.get('creator_name')}",
            "⚠️ Доставка в этот ход ещё не выполнена." if not delivered_this_turn else "✅ Доставка в этот ход уже выполнена.",
        ]

        return "\n".join(details)
