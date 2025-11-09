from scenes.utils.oneuser_page import OneUserPage
from modules.ws_client import get_logistics, logistics_pickup
from modules.utils import create_buttons


class LogisticMain(OneUserPage):
    __page_name__ = "logistic-main-page"
    async def content_worker(self):
        session_id = self.scene.get_key("scene", "session")
        company_id = self.scene.get_key("scene", "company_id")
        logistic = await get_logistics(session_id=session_id)
        logistic_company = await get_logistics(session_id=session_id, company_id=company_id)
        count_logistic = len(logistic)
        count_our_logistic = 0
        count_deliver = 0
        for l in logistic:
            if int(l["to_company_id"]) == int(company_id):
                if l["status"] == "in_transit":
                    count_our_logistic += 1
                elif l["status"] == "waiting_pickup":
                    count_deliver += 1
        return self.content.format(
            count_logistic=count_logistic,
            count_our_logistic=count_our_logistic,
            count_deliver=count_deliver
        ) 
    async def buttons_worker(self):
        self.row_width = 1
        buttons = []
        session_id = self.scene.get_key("scene", "session")
        company_id = self.scene.get_key("scene", "company_id")
        logistic_company = await get_logistics(session_id=session_id, company_id=company_id)
        count_deliver = 0
        for l in logistic:
            if l["to_company_id"] == company_id:
                if l["status"] == "waiting_pickup":
                    count_deliver += 1
        if count_deliver > 0:
            buttons.append(create_buttons(self.scene.__scene_name__, "📦 Забрать доставку", "pickup"))
        buttons.append(create_buttons(self.scene.__scene_name__, "⬅ Назад", "to_page", "main-page"))
        return buttons
    
    @OneUserPage.on_callback("pickup")
    async def pickup_logistic(self, callback, args):
        session_id = self.scene.get_key("scene", "session")
        company_id = self.scene.get_key("scene", "company_id")
        logistic_company = await get_logistics(session_id=session_id, company_id=company_id)
        id_for_pickup = []
        for l in logistic_company:
            if l["to_company_id"] == company_id and l["status"] == "waiting_pickup":
                id_for_pickup.append(l["id"])
        errors_count = 0
        for l in range(len(id_for_pickup)):
            result = await logistics_pickup(company_id=session_id, logistics_id=id_for_pickup[l])
            if "error" in result:
                errors_count += 1
        await callback.answer(f"Забор завершён! Ошибок при заборе: {errors_count}, освободите место в инвентаре", show_alert=True)
         
        