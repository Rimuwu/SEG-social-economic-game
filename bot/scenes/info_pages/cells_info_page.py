from oms import Page
from modules.ws_client import get_company
from modules.utils import xy_into_cell
from modules.resources import get_resource_name
from global_modules.load_config import ALL_CONFIGS, Resources, Cells


RESOURCES : Resources = ALL_CONFIGS["resources"]


class CellsInfo(Page):
    
    __page_name__ = "cells-info-page"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        company_data = await get_company(id=company_id)
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
