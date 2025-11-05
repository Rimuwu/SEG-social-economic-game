from oms import Page
from modules.ws_client import get_company
from modules.resources import get_resource_name, get_resource_emoji

class InventoryPage(Page):
    
    __page_name__ = "inventory-page"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        # Получаем данные о складе
        warehouses = company_data.get('warehouses', {})
        warehouse_capacity = company_data.get('warehouse_capacity', 0)
        resources_amount = company_data.get('resources_amount', 0)
        
        # Формируем список ресурсов
        resources_list = []
        if warehouses:
            for resource_key, amount in warehouses.items():
                resource_name = get_resource_name(resource_key)
                resources_list.append(f"*{resource_name}:* {amount} шт.")
        
        # Если склад пуст
        if not resources_list:
            resources_text = "_Склад пуст_"
        else:
            resources_text = "\n".join(resources_list)
        
        # Формируем текст
        text = f"""📦 *Инвентарь компании*

*Заполненность склада:* {resources_amount}/{warehouse_capacity}

*Ресурсы на складе:*
{resources_text}"""
        
        return text
