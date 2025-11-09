from typing import Dict, List, Optional, Tuple

from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_companies, get_company, create_contract
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator


RESOURCES: Resources = ALL_CONFIGS["resources"]


class ContractCreateMain(OneUserPage):
    """Главная страница создания контракта."""

    __page_name__ = "contract-create-page"

    async def data_preparate(self):
        scene_data = self.scene.get_data("scene")
        company_id = scene_data.get("company_id")

        if self.scene.get_key(self.__page_name__, "role") is None:
            await self.scene.update_key(self.__page_name__, "role", "supplier")

        if self.scene.get_key(self.__page_name__, "error") is None:
            await self.scene.update_key(self.__page_name__, "error", None)

        if self.scene.get_key(self.__page_name__, "input_state") is None:
            await self.scene.update_key(self.__page_name__, "input_state", None)

        if (
            self.scene.get_key(self.__page_name__, "supplier_company_id") is None
            and company_id is not None
        ):
            await self._set_company("supplier", company_id)

        if self.scene.get_key(self.__page_name__, "customer_company_id") is None:
            await self.scene.update_key(self.__page_name__, "customer_company_name", None)

    async def content_worker(self):
        await self._ensure_company_name("supplier")
        await self._ensure_company_name("customer")

        role = self.scene.get_key(self.__page_name__, "role") or "supplier"
        role_text = "Поставщик" if role == "supplier" else "Покупатель"

        supplier_text = (
            self.scene.get_key(self.__page_name__, "supplier_company_name")
            or "Не выбрано"
        )
        customer_text = (
            self.scene.get_key(self.__page_name__, "customer_company_name")
            or "Не выбрано"
        )

        resource_text = "Не выбрано"
        resource_id = self.scene.get_key(self.__page_name__, "resource")
        if resource_id:
            resource = RESOURCES.get_resource(resource_id)
            if resource:
                resource_text = f"{resource.emoji} {resource.label}"
                available_amount = await self._get_available_amount_for_selected_resource(
                    resource_id
                )
                if available_amount is not None:
                    resource_text = f"{resource_text} (x{available_amount})"
            else:
                resource_text = resource_id

        amount = self.scene.get_key(self.__page_name__, "amount_per_turn")
        duration = self.scene.get_key(self.__page_name__, "duration_turns")
        payment = self.scene.get_key(self.__page_name__, "payment_amount")

        amount_text = str(amount) if amount else "Не указано"
        duration_text = str(duration) if duration else "Не указано"
        payment_text = str(payment) if payment else "Не указано"

        error = self.scene.get_key(self.__page_name__, "error")
        error_text = f"\n\n❌ Ошибка: {error}" if error else ""

        return self.content.format(
            role_text=role_text,
            supplier_text=supplier_text,
            customer_text=customer_text,
            resource_text=resource_text,
            amount_text=amount_text,
            duration_text=duration_text,
            payment_text=payment_text,
            error_text=error_text,
        )

    async def buttons_worker(self):
        await self._ensure_company_name("supplier")
        await self._ensure_company_name("customer")

        role = self.scene.get_key(self.__page_name__, "role") or "supplier"
        role_text = "Поставщик" if role == "supplier" else "Покупатель"

        supplier_name = (
            self.scene.get_key(self.__page_name__, "supplier_company_name")
            or "Не выбрано"
        )
        customer_name = (
            self.scene.get_key(self.__page_name__, "customer_company_name")
            or "Не выбрано"
        )

        if role == "supplier" and supplier_name != "Не выбрано":
            supplier_name = f"{supplier_name} (вы)"
        if role == "customer" and customer_name != "Не выбрано":
            customer_name = f"{customer_name} (вы)"

        resource_label = "Не выбрано"
        resource_id = self.scene.get_key(self.__page_name__, "resource")
        if resource_id:
            resource = RESOURCES.get_resource(resource_id)
            if resource:
                resource_label = f"{resource.emoji} {resource.label}"
                available_amount = await self._get_available_amount_for_selected_resource(
                    resource_id
                )
                if available_amount is not None:
                    resource_label = f"{resource_label} (x{available_amount})"
            else:
                resource_label = resource_id

        amount = self.scene.get_key(self.__page_name__, "amount_per_turn")
        duration = self.scene.get_key(self.__page_name__, "duration_turns")
        payment = self.scene.get_key(self.__page_name__, "payment_amount")

        amount_text = str(amount) if amount else "N"
        duration_text = str(duration) if duration else "N"
        payment_text = str(payment) if payment else "N"

        self.row_width = 2
        buttons = [
            {
                "text": f"🤝 Роль: {role_text}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "toggle_role"
                ),
                "ignore_row": True,
            },
            {
                "text": f"🏭 Поставщик: {supplier_name}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "open_company_select", "supplier"
                ),
                "ignore_row": True,
            },
            {
                "text": f"🏬 Покупатель: {customer_name}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "open_company_select", "customer"
                ),
                "ignore_row": True,
            },
            {
                "text": f"📦 Ресурс: {resource_label}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "open_resource_select"
                ),
                "ignore_row": True,
            },
            {
                "text": f"📈 Кол-во/ход: {amount_text}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "set_amount_per_turn"
                ),
            },
            {
                "text": f"⏱️ Длительность: {duration_text}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "set_duration_turns"
                ),
            },
            {
                "text": f"💰 Цена: {payment_text}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "set_payment_amount"
                ),
                "ignore_row": True,
            },
            {
                "text": "✅ Создать",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "submit_contract"
                ),
            },
            {
                "text": "🔄 Очистить",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "clear_contract_form"
                ),
            },
        ]

        return buttons

    @OneUserPage.on_text("int")
    async def numeric_input_handler(self, message: Message, value: int):
        input_state = self.scene.get_key(self.__page_name__, "input_state")
        if not input_state:
            return

        await self.scene.update_key(self.__page_name__, "error", None)

        if value <= 0:
            await self.scene.update_key(
                self.__page_name__,
                "error",
                "Число должно быть положительным.",
            )
            await self.scene.update_key(self.__page_name__, "input_state", None)
            await self.scene.update_message()
            return

        if input_state == "amount":
            await self.scene.update_key(self.__page_name__, "amount_per_turn", value)
        elif input_state == "duration":
            await self.scene.update_key(self.__page_name__, "duration_turns", value)
        elif input_state == "payment":
            await self.scene.update_key(self.__page_name__, "payment_amount", value)

        await self.scene.update_key(self.__page_name__, "input_state", None)
        await self.scene.update_message()

    @OneUserPage.on_callback("toggle_role")
    async def toggle_role_handler(self, callback: CallbackQuery, args: list):
        scene_data = self.scene.get_data("scene")
        player_company_id = scene_data.get("company_id")

        if player_company_id is None:
            await callback.answer("❌ Ваша компания не найдена", show_alert=True)
            return

        role = self.scene.get_key(self.__page_name__, "role") or "supplier"
        new_role = "customer" if role == "supplier" else "supplier"

        await self.scene.update_key(self.__page_name__, "role", new_role)

        if new_role == "supplier":
            await self._set_company("supplier", player_company_id)
            await self._set_company("customer", None)
        else:
            await self._set_company("customer", player_company_id)
            await self._set_company("supplier", None)

        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_message()
        await callback.answer("Роль обновлена")

    @OneUserPage.on_callback("open_company_select")
    async def open_company_select_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Некорректный запрос", show_alert=True)
            return

        target = args[1]
        role = self.scene.get_key(self.__page_name__, "role") or "supplier"

        if target == "supplier" and role == "supplier":
            await callback.answer("Вы уже являетесь поставщиком", show_alert=True)
            return

        if target == "customer" and role == "customer":
            await callback.answer("Вы уже являетесь покупателем", show_alert=True)
            return

        await self.scene.update_key("contract-create-select-company-page", "target", target)
        await self.scene.update_key("contract-create-select-company-page", "page", 0)
        await self.scene.update_key("contract-create-select-company-page", "error", None)
        await self.scene.update_page("contract-create-select-company-page")

    @OneUserPage.on_callback("open_resource_select")
    async def open_resource_select_handler(self, callback: CallbackQuery, args: list):
        await self.scene.update_key("contract-create-select-resource-page", "page", 0)
        await self.scene.update_key("contract-create-select-resource-page", "error", None)
        await self.scene.update_page("contract-create-select-resource-page")

    @OneUserPage.on_callback("set_amount_per_turn")
    async def set_amount_handler(self, callback: CallbackQuery, args: list):
        await self.scene.update_key(self.__page_name__, "input_state", "amount")
        await callback.answer("Введите количество ресурса за ход в чат", show_alert=True)

    @OneUserPage.on_callback("set_duration_turns")
    async def set_duration_handler(self, callback: CallbackQuery, args: list):
        await self.scene.update_key(self.__page_name__, "input_state", "duration")
        await callback.answer("Введите длительность контракта в ходах", show_alert=True)

    @OneUserPage.on_callback("set_payment_amount")
    async def set_payment_handler(self, callback: CallbackQuery, args: list):
        await self.scene.update_key(self.__page_name__, "input_state", "payment")
        await callback.answer("Введите оплату за ход в чат", show_alert=True)

    @OneUserPage.on_callback("submit_contract")
    async def submit_contract_handler(self, callback: CallbackQuery, args: list):
        supplier_id = self.scene.get_key(self.__page_name__, "supplier_company_id")
        customer_id = self.scene.get_key(self.__page_name__, "customer_company_id")
        resource = self.scene.get_key(self.__page_name__, "resource")
        amount = self.scene.get_key(self.__page_name__, "amount_per_turn")
        duration = self.scene.get_key(self.__page_name__, "duration_turns")
        payment = self.scene.get_key(self.__page_name__, "payment_amount")

        scene_data = self.scene.get_data("scene")
        session_id = scene_data.get("session")
        creator_company_id = scene_data.get("company_id")

        if not all([supplier_id, customer_id, resource, amount, duration, payment]):
            await callback.answer("❌ Заполните все поля", show_alert=True)
            return

        if supplier_id == customer_id:
            await callback.answer("❌ Компании должны быть разными", show_alert=True)
            return

        if session_id is None or creator_company_id is None:
            await callback.answer("❌ Нет данных сессии или компании", show_alert=True)
            return

        result = await create_contract(
            supplier_company_id=int(supplier_id),
            customer_company_id=int(customer_id),
            session_id=session_id,
            resource=resource,
            amount_per_turn=int(amount),
            duration_turns=int(duration),
            payment_amount=int(payment),
            who_creator=int(creator_company_id),
        )

        if isinstance(result, dict) and result.get("error"):
            await callback.answer(f"❌ {result['error']}", show_alert=True)
            return

        await callback.answer("✅ Контракт создан!", show_alert=True)
        await self._reset_form(keep_role=True)
        await self.scene.update_page("contract-main-page")

    @OneUserPage.on_callback("clear_contract_form")
    async def clear_form_handler(self, callback: CallbackQuery, args: list):
        await self._reset_form(keep_role=True)
        await callback.answer("Форма очищена")
        await self.scene.update_message()

    async def _get_available_amount_for_selected_resource(
        self, resource_id: str
    ) -> Optional[int]:
        role = self.scene.get_key(self.__page_name__, "role") or "supplier"
        if role != "supplier":
            return None

        supplier_id_raw = self.scene.get_key(self.__page_name__, "supplier_company_id")
        scene_data = self.scene.get_data("scene")
        player_company_id_raw = scene_data.get("company_id")

        try:
            supplier_id = int(supplier_id_raw) if supplier_id_raw is not None else None
        except (TypeError, ValueError):
            supplier_id = None

        try:
            player_company_id = (
                int(player_company_id_raw) if player_company_id_raw is not None else None
            )
        except (TypeError, ValueError):
            player_company_id = None

        if (
            supplier_id is None
            or player_company_id is None
            or supplier_id != player_company_id
        ):
            return None

        company_data = await get_company(id=supplier_id)
        if not isinstance(company_data, dict):
            return None

        warehouses = company_data.get("warehouses") or {}
        if not isinstance(warehouses, dict):
            return None

        value = warehouses.get(resource_id)
        try:
            amount = int(value)
        except (TypeError, ValueError):
            return None

        return amount if amount > 0 else None

    async def _reset_form(self, keep_role: bool = False):
        scene_data = self.scene.get_data("scene")
        player_company_id = scene_data.get("company_id")

        if not keep_role:
            await self.scene.update_key(self.__page_name__, "role", "supplier")

        role = self.scene.get_key(self.__page_name__, "role") or "supplier"

        if role == "supplier" and player_company_id is not None:
            await self._set_company("supplier", player_company_id)
            await self._set_company("customer", None)
        elif role == "customer" and player_company_id is not None:
            await self._set_company("customer", player_company_id)
            await self._set_company("supplier", None)
        else:
            await self._set_company("supplier", None)
            await self._set_company("customer", None)

        await self.scene.update_key(self.__page_name__, "resource", None)
        await self.scene.update_key(self.__page_name__, "amount_per_turn", None)
        await self.scene.update_key(self.__page_name__, "duration_turns", None)
        await self.scene.update_key(self.__page_name__, "payment_amount", None)
        await self.scene.update_key(self.__page_name__, "input_state", None)
        await self.scene.update_key(self.__page_name__, "error", None)

    async def _set_company(
        self, target: str, company_id: Optional[int], name: Optional[str] = None
    ):
        id_key = f"{target}_company_id"
        name_key = f"{target}_company_name"

        await self.scene.update_key(self.__page_name__, id_key, company_id)

        if company_id is None:
            await self.scene.update_key(self.__page_name__, name_key, None)
            return

        company_name = name
        if company_name is None:
            company_info = await get_company(id=int(company_id))
            if isinstance(company_info, dict):
                company_name = company_info.get("name", f"Компания #{company_id}")
            else:
                company_name = f"Компания #{company_id}"

        await self.scene.update_key(self.__page_name__, name_key, company_name)

    async def _ensure_company_name(self, target: str):
        name_key = f"{target}_company_name"
        id_key = f"{target}_company_id"

        name = self.scene.get_key(self.__page_name__, name_key)
        company_id = self.scene.get_key(self.__page_name__, id_key)

        if company_id and not name:
            await self._set_company(target, company_id)


class ContractCreateSelectCompany(OneUserPage):
    """Страница выбора компании."""

    __page_name__ = "contract-create-select-company-page"

    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
        if self.scene.get_key(self.__page_name__, "error") is None:
            await self.scene.update_key(self.__page_name__, "error", None)

    async def content_worker(self):
        target = self.scene.get_key(self.__page_name__, "target") or "customer"
        description = (
            "Выберите компанию-покупателя, которая будет получать ресурс."
            if target == "customer"
            else "Выберите компанию-поставщика, которая будет отправлять ресурс."
        )

        error = self.scene.get_key(self.__page_name__, "error")
        error_text = f"\n\n❌ Ошибка: {error}" if error else ""

        return self.content.format(
            description_text=description,
            error_text=error_text,
        )

    async def buttons_worker(self):
        available = await self._get_available_companies()

        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        items_per_page = 5
        total_pages = max(1, (len(available) + items_per_page - 1) // items_per_page)
        page_index %= total_pages
        await self.scene.update_key(self.__page_name__, "page", page_index)

        start = page_index * items_per_page
        end = start + items_per_page
        page_items = available[start:end]

        buttons = []
        self.row_width = 1

        if not page_items:
            buttons.append(
                {
                    "text": "Компаний не найдено",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "no_companies"
                    ),
                    "ignore_row": True,
                }
            )
            return buttons

        for company in page_items:
            name = company.get("name", "Без названия")
            cid = company.get("id")
            buttons.append(
                {
                    "text": f"{name}",
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "select_company", cid
                    ),
                    "ignore_row": True,
                }
            )

        self.row_width = 3
        buttons.append(
            {
                "text": "◀️ Назад",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "back_page"
                ),
            }
        )
        buttons.append(
            {
                "text": f"📄 {page_index + 1}/{total_pages}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "page_info"
                ),
            }
        )
        buttons.append(
            {
                "text": "Вперёд ▶️",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "next_page"
                ),
            }
        )

        return buttons

    @OneUserPage.on_callback("select_company")
    async def select_company_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Некорректный выбор", show_alert=True)
            return

        target = self.scene.get_key(self.__page_name__, "target") or "customer"
        company_id = int(args[1])

        company_info = await get_company(id=company_id)
        if not isinstance(company_info, dict):
            await callback.answer("❌ Не удалось получить данные компании", show_alert=True)
            return

        other_id = self.scene.get_key(
            "contract-create-page",
            "customer_company_id" if target == "supplier" else "supplier_company_id",
        )
        if other_id and int(other_id) == company_id:
            await callback.answer("❌ Компании должны отличаться", show_alert=True)
            return

        await self.scene.update_key(
            "contract-create-page",
            f"{target}_company_id",
            company_id,
        )
        await self.scene.update_key(
            "contract-create-page",
            f"{target}_company_name",
            company_info.get("name", f"Компания #{company_id}"),
        )
        if target == "supplier":
            await self.scene.update_key("contract-create-page", "resource", None)
        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_page("contract-create-page")
        await callback.answer("✅ Компания выбрана")

    @OneUserPage.on_callback("next_page")
    async def next_page_handler(self, callback: CallbackQuery, args: list):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        available = await self._get_available_companies()
        items_per_page = 5
        total_pages = max(1, (len(available) + items_per_page - 1) // items_per_page)

        await self.scene.update_key(
            self.__page_name__, "page", (page_index + 1) % total_pages
        )
        await self.scene.update_message()

    @OneUserPage.on_callback("back_page")
    async def back_page_handler(self, callback: CallbackQuery, args: list):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        available = await self._get_available_companies()
        items_per_page = 5
        total_pages = max(1, (len(available) + items_per_page - 1) // items_per_page)

        await self.scene.update_key(
            self.__page_name__, "page", (page_index - 1) % total_pages
        )
        await self.scene.update_message()

    @OneUserPage.on_callback("page_info")
    async def page_info_handler(self, callback: CallbackQuery, args: list):
        await callback.answer("Страница выбора компании")

    @OneUserPage.on_callback("no_companies")
    async def no_companies_handler(self, callback: CallbackQuery, args: list):
        await callback.answer("Компаний для выбора нет", show_alert=True)

    async def _get_available_companies(self):
        scene_data = self.scene.get_data("scene")
        session_id = scene_data.get("session")
        player_company_id = scene_data.get("company_id")

        target = self.scene.get_key(self.__page_name__, "target") or "customer"
        role = self.scene.get_key("contract-create-page", "role") or "supplier"

        exclude_ids = set()
        if target == "customer":
            supplier_id = self.scene.get_key(
                "contract-create-page", "supplier_company_id"
            )
            if supplier_id:
                exclude_ids.add(int(supplier_id))
            if role == "supplier" and player_company_id:
                exclude_ids.add(int(player_company_id))
        else:
            customer_id = self.scene.get_key(
                "contract-create-page", "customer_company_id"
            )
            if customer_id:
                exclude_ids.add(int(customer_id))
            if role == "customer" and player_company_id:
                exclude_ids.add(int(player_company_id))

        companies_response = await get_companies(session_id=session_id)
        companies = companies_response if isinstance(companies_response, list) else []

        def is_in_prison(company: dict) -> bool:
            value = company.get("in_prison")
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"true", "1", "yes"}
            return bool(value)

        available = [
            company
            for company in companies
            if isinstance(company, dict)
            and company.get("id") is not None
            and int(company["id"]) not in exclude_ids
            and not is_in_prison(company)
        ]

        available.sort(key=lambda item: item.get("name", ""))
        return available


class ContractCreateSelectResource(OneUserPage):
    """Страница выбора ресурса."""

    __page_name__ = "contract-create-select-resource-page"

    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
        if self.scene.get_key(self.__page_name__, "error") is None:
            await self.scene.update_key(self.__page_name__, "error", None)

    async def content_worker(self):
        supplier_name = self.scene.get_key(
            "contract-create-page", "supplier_company_name"
        )
        supplier_text = (
            f"Поставщик: {supplier_name}\n"
            if supplier_name
            else "Сначала укажите поставщика.\n"
        )

        error = self.scene.get_key(self.__page_name__, "error")
        error_text = f"\n\n❌ Ошибка: {error}" if error else ""

        return self.content.format(
            supplier_text=supplier_text,
            error_text=error_text,
        )

    async def buttons_worker(self):
        resource_items, use_inventory = await self._prepare_resources()

        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        items_per_page = 6
        total_pages = max(1, (len(resource_items) + items_per_page - 1) // items_per_page)
        page_index %= total_pages
        await self.scene.update_key(self.__page_name__, "page", page_index)

        start = page_index * items_per_page
        end = start + items_per_page
        page_resources = resource_items[start:end]

        buttons = []
        self.row_width = 2

        if not page_resources:
            empty_text = (
                "На складе нет ресурсов"
                if use_inventory
                else "Ресурсов не найдено"
            )
            buttons.append(
                {
                    "text": empty_text,
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "no_resources"
                    ),
                    "ignore_row": True,
                }
            )
            return buttons

        for resource_id, resource, amount in page_resources:
            if use_inventory and amount is not None:
                text = f"{resource.emoji} {resource.label} (x{amount})"
            else:
                text = f"{resource.emoji} {resource.label}"
            buttons.append(
                {
                    "text": text,
                    "callback_data": callback_generator(
                        self.scene.__scene_name__, "select_resource", resource_id
                    ),
                    "ignore_row": True,
                }
            )

        self.row_width = 3
        buttons.append(
            {
                "text": "◀️ Назад",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "back_page"
                ),
            }
        )
        buttons.append(
            {
                "text": f"📄 {page_index + 1}/{total_pages}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "page_info"
                ),
            }
        )
        buttons.append(
            {
                "text": "Вперёд ▶️",
                "callback_data": callback_generator(
                    self.scene.__scene_name__, "next_page"
                ),
            }
        )

        return buttons

    @OneUserPage.on_callback("select_resource")
    async def select_resource_handler(self, callback: CallbackQuery, args: list):
        if len(args) < 2:
            await callback.answer("❌ Некорректный выбор", show_alert=True)
            return

        resource_id = args[1]
        resource = RESOURCES.get_resource(resource_id)

        if resource is None:
            await callback.answer("❌ Ресурс не найден", show_alert=True)
            return

        inventory, use_inventory = await self._get_supplier_inventory()
        available = inventory.get(resource_id)

        if use_inventory and (available is None or available <= 0):
            await callback.answer("❌ Ресурса нет на складе", show_alert=True)
            return

        await self.scene.update_key("contract-create-page", "resource", resource_id)
        await self.scene.update_key(self.__page_name__, "error", None)
        await self.scene.update_page("contract-create-page")

        if use_inventory and available is not None:
            await callback.answer(
                f"✅ Выбран ресурс: {resource.label} (x{available})",
                show_alert=True,
            )
        else:
            await callback.answer(f"✅ Выбран ресурс: {resource.label}")

    @OneUserPage.on_callback("next_page")
    async def next_page_handler(self, callback: CallbackQuery, args: list):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        resource_items, _ = await self._prepare_resources()
        if not resource_items:
            await callback.answer("Нет доступных ресурсов", show_alert=True)
            return

        items_per_page = 6
        total_pages = max(1, (len(resource_items) + items_per_page - 1) // items_per_page)

        await self.scene.update_key(
            self.__page_name__, "page", (page_index + 1) % total_pages
        )
        await self.scene.update_message()

    @OneUserPage.on_callback("back_page")
    async def back_page_handler(self, callback: CallbackQuery, args: list):
        page_index = self.scene.get_key(self.__page_name__, "page") or 0
        resource_items, _ = await self._prepare_resources()
        if not resource_items:
            await callback.answer("Нет доступных ресурсов", show_alert=True)
            return

        items_per_page = 6
        total_pages = max(1, (len(resource_items) + items_per_page - 1) // items_per_page)

        await self.scene.update_key(
            self.__page_name__, "page", (page_index - 1) % total_pages
        )
        await self.scene.update_message()

    @OneUserPage.on_callback("page_info")
    async def page_info_handler(self, callback: CallbackQuery, args: list):
        await callback.answer("Страница выбора ресурса")

    @OneUserPage.on_callback("no_resources")
    async def no_resources_handler(self, callback: CallbackQuery, args: list):
        await callback.answer("Ресурсы недоступны", show_alert=True)

    async def _prepare_resources(self) -> Tuple[List[Tuple[str, object, Optional[int]]], bool]:
        inventory, use_inventory = await self._get_supplier_inventory()

        resource_items: List[Tuple[str, object, Optional[int]]] = []
        if use_inventory:
            for resource_id, amount in inventory.items():
                resource = RESOURCES.get_resource(resource_id)
                if resource:
                    resource_items.append((resource_id, resource, amount))
        else:
            for resource_id, resource in RESOURCES.resources.items():
                resource_items.append((resource_id, resource, inventory.get(resource_id)))

        resource_items.sort(key=lambda item: (item[1].lvl, item[1].label))
        return resource_items, use_inventory

    async def _get_supplier_inventory(self) -> Tuple[Dict[str, int], bool]:
        supplier_id_raw = self.scene.get_key("contract-create-page", "supplier_company_id")
        scene_data = self.scene.get_data("scene")
        player_company_id_raw = scene_data.get("company_id")
        role = self.scene.get_key("contract-create-page", "role") or "supplier"

        supplier_id: Optional[int]
        player_company_id: Optional[int]

        try:
            supplier_id = int(supplier_id_raw) if supplier_id_raw is not None else None
        except (TypeError, ValueError):
            supplier_id = None

        try:
            player_company_id = (
                int(player_company_id_raw) if player_company_id_raw is not None else None
            )
        except (TypeError, ValueError):
            player_company_id = None

        use_inventory = (
            supplier_id is not None
            and player_company_id is not None
            and supplier_id == player_company_id
            and role == "supplier"
        )

        if supplier_id is None:
            return {}, False

        company_data = await get_company(id=supplier_id)
        warehouses = {}
        if isinstance(company_data, dict):
            warehouses = company_data.get("warehouses") or {}

        inventory: Dict[str, int] = {}
        if isinstance(warehouses, dict):
            for key, value in warehouses.items():
                try:
                    amount = int(value)
                except (TypeError, ValueError):
                    continue
                if amount > 0:
                    inventory[str(key)] = amount

        return inventory, use_inventory