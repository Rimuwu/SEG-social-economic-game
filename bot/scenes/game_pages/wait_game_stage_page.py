from oms import Page
from modules.ws_client import get_company, get_company_cell_info
from global_modules.logs import Logger
from global_modules.load_config import ALL_CONFIGS, Cells, Resources
from modules.utils import xy_into_cell

RESOURCES: Resources = ALL_CONFIGS["resources"]

class WaitGameStagePage(Page):
    __page_name__ = "wait-game-stage-page"
    
    async def content_worker(self) -> str:
        company_id = self.scene.get_key("scene", "company_id")
        session = self.scene.get_key("scene", "session")
        company = await get_company(id=company_id, session_id=session)
        if "error" in company:
            return company["error"]
        company_name = company.get("name")
        cell_coord = xy_into_cell(*company.get("cell_position").split(".")[::-1])
        cell_info = await get_company_cell_info(company_id=company_id)
        cell_type = cell_info["data"]["label"]
        cell_res = f"{RESOURCES.get_resource(cell_info['data'].get('resource_id')).emoji} {RESOURCES.get_resource(cell_info['data'].get('resource_id')).label}" 
        return self.content.format(
            company_name=company_name,
            cell_coord=cell_coord,
            cell_type=cell_type,
            cell_res=cell_res
        )
