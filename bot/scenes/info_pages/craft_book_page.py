from oms import Page
from modules.utils import create_buttons
from global_modules.load_config import ALL_CONFIGS, Resources
from modules.ws_client import get_company_warehouse
from oms.utils import callback_generator

RESOURCES: Resources = ALL_CONFIGS["resources"]

class CraftBookPage(Page):
    
    __page_name__ = "craft-book-page"
    
    async def data_preparate(self):
        if self.scene.get_key("craft-book-page", "page_number") is None:
            await self.scene.update_key("craft-book-page", "page_number", 0)
        if self.scene.get_key("craft-book-page", "resource") is None:
            await self.scene.update_key("craft-book-page", "resource", None)
        # Кэшируем склад компании для отображения количества материалов
        company_id = self.scene.get_key('scene', 'company_id')
        warehouses = await get_company_warehouse(company_id)
        await self.scene.update_key(self.__page_name__, 'warehouses_data', warehouses)
    
    async def content_worker(self):
        resource = self.scene.get_key("craft-book-page", "resource")
        if resource is None:
            return "📚 *Книга крафтов*\n\n👉 Нажмите на ресурс, чтобы узнать его крафт"
        company_id = self.scene.get_key('scene', 'company_id')
        resource_data = RESOURCES.get_resource(resource)
        resorce_name = f"{resource_data.emoji} {resource_data.label}"
        craft_prod = resource_data.production
        craft_material = craft_prod.materials
        craft_output = craft_prod.output
        craft_list = []
        for i in craft_material.keys():
            mat_res = RESOURCES.get_resource(i)
            craft_list.append(f"{craft_material[i]}× {mat_res.emoji} {mat_res.label}")
        
        craft_text = " + ".join(craft_list)
        craft_text += f" → {craft_output}× {resorce_name}"
        
        warehouses = self.scene.get_key(self.__page_name__, 'warehouses_data')
        resource_in_craft_with_count = ""
        for i in craft_material.keys():
            mat_res = RESOURCES.get_resource(i)
            mat_count_in_warehouse = warehouses["warehouses"].get(i, 0)
            resource_in_craft_with_count += f" - {mat_res.emoji} {mat_res.label}: {mat_count_in_warehouse}\n"
        
        return self.content.format(
            resource=resorce_name,
            craft=craft_text,
            resource_in_craft_with_count=resource_in_craft_with_count
            )
    
    async def buttons_worker(self):
        buttons = []
        self.row_width = 3
        cur_page = self.scene.get_key('craft-book-page', 'page_number')
        produced_resources_keys = RESOURCES.get_produced_resources()
        all_resources = []
        for resource_key in produced_resources_keys:
            resource = RESOURCES.get_resource(resource_key)
            if resource:
                all_resources.append({
                    "id": resource_key,
                    "name": resource.label,
                    "emoji": resource.emoji,
                    "level": resource.lvl if hasattr(resource, 'lvl') else 0
                })
        
        # Сортируем по уровню и имени
        all_resources.sort(key=lambda x: (x["level"], x["name"]))
        
        # Пагинация: 4 элемента на странице
        items_per_page = 4
        total_pages = max(1, (len(all_resources) + items_per_page - 1) // items_per_page)
        
        # Нормализуем номер страницы (цикличность)
        cur_page = cur_page % total_pages
        await self.scene.update_key('craft-book-page', 'page_number', cur_page)
        
        # Получаем элементы для текущей страницы
        start_idx = cur_page * items_per_page
        end_idx = start_idx + items_per_page
        page_resources = all_resources[start_idx:end_idx]
        
        # Создаем кнопки с ресурсами
        for resource in page_resources:
            buttons.append({
                "text": f"{resource['emoji']} {resource['name']}",
                "callback_data": callback_generator(
                    self.scene.__scene_name__,
                    "select_resource",
                    resource["id"]
                ),
                "ignore_row": True
            })
        
        # Добавляем навигацию
        self.row_width = 3
        buttons.append({
            "text": "◀️ Назад",
            "callback_data": callback_generator(self.scene.__scene_name__, "back_page"),
        })
        buttons.append({
            "text": f"📄 {cur_page + 1}/{total_pages}",
            "callback_data": callback_generator(self.scene.__scene_name__, "page_info"),
        })
        buttons.append({
            "text": "Вперёд ▶️",
            "callback_data": callback_generator(self.scene.__scene_name__, "next_page"),
        })
    
        return buttons

    @Page.on_callback('select_resource')
    async def select_resource(self, callback, args: list):
        """Выбор ресурса для просмотра крафта"""
        resource_id = args[1]
        await self.scene.update_key("craft-book-page", "resource", resource_id)
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('next_page')
    async def next_page(self, callback, args: list):
        """Следующая страница"""
        cur_page = self.scene.get_key('craft-book-page', 'page_number')

        # Вычисляем общее количество страниц
        produced_resources_keys = RESOURCES.get_produced_resources()
        items_per_page = 4
        total_pages = max(1, (len(produced_resources_keys) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: после последней страницы идет первая
        new_page = (cur_page + 1) % total_pages
        await self.scene.update_key('craft-book-page', 'page_number', new_page)

        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('back_page')
    async def back_page(self, callback, args: list):
        cur_page = self.scene.get_key('craft-book-page', 'page_number')
        
        # Вычисляем общее количество страниц
        produced_resources_keys = RESOURCES.get_produced_resources()
        items_per_page = 4
        total_pages = max(1, (len(produced_resources_keys) + items_per_page - 1) // items_per_page)
        
        # Зацикливание: перед первой страницей идет последняя
        new_page = (cur_page - 1) % total_pages
        await self.scene.update_key('craft-book-page', 'page_number', new_page)
        
        await self.scene.update_message()
        await callback.answer()
            