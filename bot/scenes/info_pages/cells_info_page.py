from oms import Page
from modules.ws_client import get_company
from modules.utils import xy_into_cell
from modules.resources import get_resource_name
from global_modules.load_config import ALL_CONFIGS, Resources, Cells


RESOURCES : Resources = ALL_CONFIGS["resources"]


class CellsInfo(Page):
    
    __page_name__ = "cells-info-page"
    
    async def data_preparate(self):
        company_id = self.scene.get_key('scene', 'company_id')
        company_data = await get_company(id=company_id)
        await self.scene.update_key(self.__page_name__, 'company_data', company_data)
    
    async def content_worker(self):
        company_data = self.scene.get_key(self.__page_name__, 'company_data')
        if isinstance(company_data, str):
            return f"❌ Ошибка загрузки клетки: {company_data}"
        cell_info = company_data.get('cell_info', {})
        position_coords = company_data.get('position_coords', [0, 0])
        resource_data = RESOURCES.get_resource(cell_info["resource_id"])
        text_res = f"{resource_data.emoji} {resource_data.label}"
        cell_position = xy_into_cell(position_coords[0], position_coords[1])
        return self.content.format(
            type_cell=cell_info["label"],
            res=text_res,
            cell_cord=cell_position
        )
