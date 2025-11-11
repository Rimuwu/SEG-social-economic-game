from modules.ws_client import get_logistics, get_company, get_city
from scenes.utils.oneuser_page import OneUserPage
from modules.utils import create_buttons
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator


RESOURCES: Resources = ALL_CONFIGS["resources"]

class LogisticInfo(OneUserPage):
    __page_name__ = "logistic-info-page"
    
    
    async def data_preparate(self):
        # Инициализация управляющих ключей
        if self.scene.get_key(self.__page_name__, "set_id") is None:
            await self.scene.update_key(self.__page_name__, "set_id", None)
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
        # Кэшируем список логистик, относящихся к нашей компании (как отправитель, так и получатель)
        session_id = self.scene.get_key("scene", "session")
        company_id = self.scene.get_key("scene", "company_id")
        lst_from = await get_logistics(session_id=session_id, from_company_id=company_id) or []
        lst_to = await get_logistics(session_id=session_id, to_company_id=company_id) or []
        # Объединим без дублей по id
        uniq = {}
        for l in lst_from + lst_to:
            if isinstance(l, dict) and l.get("id") is not None:
                uniq[l["id"]] = l
        await self.scene.update_key(self.__page_name__, "logistics_list", list(uniq.values()))
        # Кэши компаний и городов для подписей
        if self.scene.get_key(self.__page_name__, "companies_cache") is None:
            await self.scene.update_key(self.__page_name__, "companies_cache", {})
        if self.scene.get_key(self.__page_name__, "cities_cache") is None:
            await self.scene.update_key(self.__page_name__, "cities_cache", {})
        # Кэш деталей логистики по id (лениво заполняем в content_worker)
        if self.scene.get_key(self.__page_name__, "logistics_details") is None:
            await self.scene.update_key(self.__page_name__, "logistics_details", {})
    
    
    async def content_worker(self):
        set_id = self.scene.get_key(self.__page_name__, "set_id")
        if set_id is None:
            return "Выберите логистику для просмотра информации."
        # Достаем из кэша, при отсутствии — один раз подкачиваем
        details_cache = self.scene.get_key(self.__page_name__, "logistics_details") or {}
        logistic_data = details_cache.get(set_id)
        if logistic_data is None:
            logistic_data = await get_logistics(logistics_id=set_id)
            if isinstance(logistic_data, dict):
                details_cache[set_id] = logistic_data
                await self.scene.update_key(self.__page_name__, "logistics_details", details_cache)
        logistic_id = set_id

        async def company_name(cid: int) -> str:
            companies_cache = self.scene.get_key(self.__page_name__, "companies_cache") or {}
            if cid in companies_cache:
                return companies_cache[cid]
            comp = await get_company(id=cid)
            name = comp.get("name", f"#{cid}") if isinstance(comp, dict) else f"#{cid}"
            companies_cache[cid] = name
            await self.scene.update_key(self.__page_name__, "companies_cache", companies_cache)
            return name

        async def city_name(city_id: int) -> str:
            cities_cache = self.scene.get_key(self.__page_name__, "cities_cache") or {}
            if city_id in cities_cache:
                return cities_cache[city_id]
            city = await get_city(id=city_id)
            name = city.get("name", f"#{city_id}") if isinstance(city, dict) else f"#{city_id}"
            cities_cache[city_id] = name
            await self.scene.update_key(self.__page_name__, "cities_cache", cities_cache)
            return name

        from_name = f"Компания {await company_name(logistic_data.get('from_company_id'))}"
        if logistic_data.get("to_city_id") in (None, 0):
            to_name = f"Компания {await company_name(logistic_data.get('to_company_id'))}"
        else:
            to_name = f"Город {await city_name(logistic_data.get('to_city_id'))}"

        res_data = RESOURCES.get_resource(logistic_data.get("resource_type"))
        resource = f"{res_data.emoji} {res_data.label} x{logistic_data.get('amount')}"
        step_last = logistic_data.get("waiting_turns")
        status_id = logistic_data.get("status")
        status_label = {
            "in_transit": "В пути",
            "delivered": "Доставлено",
            "waiting_pickup": "Ожидание разгрузки",
            "failed": "Провалено"
        }
        status = status_label.get(status_id, "Неизвестный статус")
        return self.content.format(
            logistic_id=logistic_id,
            from_name=from_name,
            to_name=to_name,
            resource=resource,
            step_last=step_last,
            status=status
        )
    
    async def buttons_worker(self):
        buttons = []
        company_id = self.scene.get_key("scene", "company_id")
        logistic_list = self.scene.get_key(self.__page_name__, "logistics_list") or []
        cur_page = self.scene.get_key(self.__page_name__, "page") or 0

        # Пагинация по 5 записей
        logistic_pages = [logistic_list[i:i + 5] for i in range(0, len(logistic_list), 5)] or [[]]
        page_idx = max(0, min(cur_page, len(logistic_pages) - 1))

        status_emoji = {
            "in_transit": "🚚",
            "waiting_pickup": "📦",
            "failed": "❌",
            "delivered": "✅"
        }

        # Готовим подписи без дополнительных сетевых вызовов, по возможности
        companies_cache = self.scene.get_key(self.__page_name__, "companies_cache") or {}
        cities_cache = self.scene.get_key(self.__page_name__, "cities_cache") or {}

        async def name_for_from(cid: int) -> str:
            if not cid:
                return ""
            if cid in companies_cache:
                return "Вы" if cid == company_id else companies_cache[cid]
            comp = await get_company(id=cid)
            name = comp.get("name", f"#{cid}") if isinstance(comp, dict) else f"#{cid}"
            companies_cache[cid] = name
            await self.scene.update_key(self.__page_name__, "companies_cache", companies_cache)
            return "Вы" if cid == company_id else name

        async def name_for_to(to_company_id: int, to_city_id: int) -> str:
            if to_city_id and to_city_id != 0:
                if to_city_id in cities_cache:
                    return cities_cache[to_city_id]
                city = await get_city(id=to_city_id)
                name = city.get("name", f"#{to_city_id}") if isinstance(city, dict) else f"#{to_city_id}"
                cities_cache[to_city_id] = name
                await self.scene.update_key(self.__page_name__, "cities_cache", cities_cache)
                return name
            if to_company_id:
                if to_company_id in companies_cache:
                    return "Вам" if to_company_id == company_id else companies_cache[to_company_id]
                comp = await get_company(id=to_company_id)
                name = comp.get("name", f"#{to_company_id}") if isinstance(comp, dict) else f"#{to_company_id}"
                companies_cache[to_company_id] = name
                await self.scene.update_key(self.__page_name__, "companies_cache", companies_cache)
                return "Вам" if to_company_id == company_id else name
            return ""

        # Кнопки логистик текущей страницы
        for item in logistic_pages[page_idx]:
            st = status_emoji.get(item.get("status"), "📦")
            from_c = await name_for_from(item.get("from_company_id"))
            to_c = await name_for_to(item.get("to_company_id"), item.get("to_city_id"))
            # Порядок аргументов: scene_name, text, callback_type, *args
            buttons.append(create_buttons(self.scene.__scene_name__, f"{st} {from_c} → {to_c}", "select_logistic", item.get("id")))

        if len(logistic_pages) > 1:
            buttons.append({
                "text": "◀️",
                "callback_data": callback_generator(self.scene.__scene_name__, "logistics_prev")
            })
            buttons.append({
                "text": f"{page_idx + 1}/{len(logistic_pages)}",
                "callback_data": callback_generator(self.scene.__scene_name__, "noop")
            })
            buttons.append({
                "text": "▶️",
                "callback_data": callback_generator(self.scene.__scene_name__, "logistics_next")
            })

        buttons.append({
            "text": "⬅️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_main_page")
        })

        return buttons

    @OneUserPage.on_callback("select_logistic")
    async def on_select_logistic(self, callback, args):
        try:
            set_id = int(args[0]) if args else None
        except Exception:
            set_id = None
        await self.scene.update_key(self.__page_name__, "set_id", set_id)
        await self.scene.update_message()

    @OneUserPage.on_callback("logistics_prev")
    async def on_prev(self, callback, args):
        cur = self.scene.get_key(self.__page_name__, "page") or 0
        cur = max(0, cur - 1)
        await self.scene.update_key(self.__page_name__, "page", cur)
        await self.scene.update_message()

    @OneUserPage.on_callback("logistics_next")
    async def on_next(self, callback, args):
        cur = self.scene.get_key(self.__page_name__, "page") or 0
        lst = self.scene.get_key(self.__page_name__, "logistics_list") or []
        max_page = max(0, (len(lst) - 1) // 5)
        cur = min(max_page, cur + 1)
        await self.scene.update_key(self.__page_name__, "page", cur)
        await self.scene.update_message()

    @OneUserPage.on_callback("back_main_page")
    async def on_back(self, callback, args):
        # Возврат на основную логистическую страницу
        await self.scene.update_page("logistic-main-page")