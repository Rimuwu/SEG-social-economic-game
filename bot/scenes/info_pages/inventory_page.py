from oms import Page
from modules.ws_client import get_company
from modules.resources import get_resource_name, get_resource_emoji

class InventoryPage(Page):
    
    __page_name__ = "inventory-page"
    
    async def data_preparate(self):
        """Предзагрузка данных компании (склад)"""
        company_id = self.scene.get_key('scene', 'company_id')
        company_data = await get_company(id=company_id)
        await self.scene.update_key(self.__page_name__, 'company_data', company_data)
    
    async def content_worker(self):
        company_data = self.scene.get_key(self.__page_name__, 'company_data')
        if isinstance(company_data, str):
            return f"❌ Ошибка загрузки склада: {company_data}"
        warehouses = company_data.get('warehouses', {})
        warehouse_capacity = company_data.get('warehouse_capacity', 0)
        resources_amount = company_data.get('resources_amount', 0)
        resources_list = []
        if warehouses:
            for resource_key, amount in warehouses.items():
                resource_name = get_resource_name(resource_key)
                resources_list.append(f"*{resource_name}:* {amount} шт.")
        if not resources_list:
            resources_text = "_Склад пуст_"
        else:
            resources_text = "\n".join(resources_list)
        
        
        return self.content.format(
            capacity=f"{resources_amount}/{warehouse_capacity}",
            resources_list=resources_text
        )
