from scenes.utils.oneuser_page import OneUserPage
from modules.ws_client import get_logistics, logistics_pickup
from modules.utils import create_buttons


class LogisticMain(OneUserPage):
    __page_name__ = "logistic-main-page"

    async def data_preparate(self):
        """Кэшируем список логистик сессии один раз за цикл рендера.
        Сохраняем под ключом 'logistics_data'. После любых мутаций (pickup) инвалидация.
        """
        session_id = self.scene.get_key("scene", "session")
        logistics_list = await get_logistics(session_id=session_id) or []
        await self.scene.update_key(self.__page_name__, "logistics_data", logistics_list)

    async def _calc_counts(self, logistics_list, company_id: int):
        count_logistic = len(logistics_list)
        count_our_logistic = 0  # В пути к нам
        count_deliver = 0       # Ожидает разгрузки у нас
        for l in logistics_list:
            to_company = l.get("to_company_id")
            status = l.get("status")
            if to_company == company_id:
                if status == "in_transit":
                    count_our_logistic += 1
                elif status == "waiting_pickup":
                    count_deliver += 1
        return count_logistic, count_our_logistic, count_deliver

    async def content_worker(self):
        company_id = self.scene.get_key("scene", "company_id")
        logistics_list = self.scene.get_key(self.__page_name__, "logistics_data") or []
        count_logistic, count_our_logistic, count_deliver = await self._calc_counts(logistics_list, company_id)
        return self.content.format(
            count_logistic=count_logistic,
            count_our_logistic=count_our_logistic,
            count_deliver=count_deliver
        )

    async def buttons_worker(self):
        self.row_width = 1
        buttons = []
        company_id = self.scene.get_key("scene", "company_id")
        logistics_list = self.scene.get_key(self.__page_name__, "logistics_data") or []
        _, _, count_deliver = await self._calc_counts(logistics_list, company_id)
        if count_deliver > 0:
            buttons.append(create_buttons(self.scene.__scene_name__, "📦 Забрать доставку", "pickup"))
        buttons.append(create_buttons(self.scene.__scene_name__, "⬅ Назад", "to_page", "main-page"))
        return buttons

    @OneUserPage.on_callback("pickup")
    async def pickup_logistic(self, callback, args):
        """Забираем все доставки в статусе waiting_pickup, адресованные нашей компании.
        После выполнения инвалидация кэша и обновление страницы.
        """
        company_id = self.scene.get_key("scene", "company_id")
        # Получаем только логистики адресованные компании, чтобы не тащить весь список повторно если он очень большой.
        logistics_list = await get_logistics(to_company_id=company_id) or []
        ids_for_pickup = [l.get("id") for l in logistics_list if l.get("to_company_id") == company_id and l.get("status") == "waiting_pickup"]
        errors_count = 0
        for logist_id in ids_for_pickup:
            result = await logistics_pickup(logistics_id=logist_id, company_id=company_id)
            if isinstance(result, dict) and "error" in result:
                errors_count += 1
        # Инвалидация кэша
        await self.scene.update_key(self.__page_name__, "logistics_data", None)
        await callback.answer(f"Забор завершён! Ошибок: {errors_count}. Освободите место в инвентаре.", show_alert=True)
        await self.scene.update_message()
        
