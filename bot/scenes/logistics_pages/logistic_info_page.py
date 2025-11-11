from modules.ws_client import get_logistics, get_company, get_city
from scenes.utils.oneuser_page import OneUserPage
from modules.utils import create_buttons
from global_modules.load_config import ALL_CONFIGS, Resources
from oms.utils import callback_generator


RESOURCES: Resources = ALL_CONFIGS["resources"]

class LogisticInfo(OneUserPage):
    __page_name__ = "logistic-info-page"
    
    
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "set_id") is None:
            await self.scene.update_key(self.__page_name__, "set_id", None)
        if self.scene.get_key(self.__page_name__, "page") is None:
            await self.scene.update_key(self.__page_name__, "page", 0)
    
    
    async def content_worker(self):
        set_id = self.scene.get_key(self.__page_name__, "set_id")
        if set_id is None:
            return "Выберите логистику для просмотра информации."
        logistic_data = await get_logistics(logistics_id=set_id)
        logistic_id = set_id
        comp_from_data = await get_company(id=logistic_data.get("from_company_id"))
        from_name = f"Компания {comp_from_data.get('name')}"
        to_name = ""
        if logistic_data.get("to_city_id") == 0:
            comp_data = await get_company(id=logistic_data.get("to_company_id"))
            to_name = f"Компания {comp_data.get('name')}"
        else:
            city_data = await get_city(id=logistic_data.get("to_city_id"))
            to_name = f"Город {city_data.get('name')}"
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
        logistic_list_from = get_logistics(from_company_id=company_id)
        logistic_list_to = get_logistics(to_company_id=company_id)
        logistic_list = logistic_list_from + logistic_list_to
        cur_page = self.scene.get_key(self.__page_name__, "page")
        
        
        logistic_page = [logistic_list[i:i+5] for i in range(0, len(logistic_list, 5))]
        for res in logistic_page[cur_page]:
            logistic_data = await get_logistics(logistics_id=res.get("id"))
            status_emoji = {
                "in_transit": "🚚",
                "waiting_pickup": "📦",
                "failed": "❌",
                "delivered": "✅"
            }
            status = status_emoji[logistic_data.get("status")]
            
            from_data = None
            to_data = None
            city_data = None
            from_c = ""
            to_c = ""
            
            if logistic_data.get("from_company_id") != 0:
                from_data = await get_company(logistic_data.get("from_company_id"))
            if logistic_data.get("to_company_id") != 0:
                to_data = await get_company(logistic_data.get("to_company_id"))
            if logistic_data.get("to_city_id"):
                city_data = await get_city(id=logistic_data.get("to_city_id"))
            
            if from_data is not None:
                if from_data["id"] == company_id:
                    from_c = "Вы"
                else:
                    from_c = from_data["name"]
            if to_data is not None:
                if to_data["id"] == company_id:
                    to_c = "Вам"
                else:
                    to_c = from_data["name"]
            if city_data is not None:
                to_c = city_data["name"]
                
            buttons.append(create_buttons(self.scene.__scene_name__, text=f"{status} {from_c} → {to_c}"))
        if len(logistic_page) > 1:
            buttons.append({
                "text": "◀️",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_products_prev")
            })
            buttons.append({
                "text": f"{cur_page + 1}/{len(logistic_page)}",
                "callback_data": callback_generator(self.scene.__scene_name__, "noop")
            })
            buttons.append({
                "text": "▶️",
                "callback_data": callback_generator(self.scene.__scene_name__, "city_products_next")
            })

        buttons.append({
            "text": "⬅️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_main_page")
        })
        
        return buttons