from modules.utils import create_buttons
from modules.ws_client import set_autopay_taxe
from scenes.utils.oneuser_page import OneUserPage
from global_modules.load_config import ALL_CONFIGS, Settings

SETTINGS: Settings = ALL_CONFIGS["settings"]


class UpgradeTaxPage(OneUserPage):
    
    
    __page_name__ = "upgrade-auto-tax-page"
    __for_blocked_pages__ = ["upgrade-menu"]
    async def content_worker(self):
        cost = SETTINGS.tax_autopay_price
        return self.content.format(
            cost=cost
        )
    
    async def buttons_worker(self):
        self.row_width = 1
        buttons = []
        buttons.append(create_buttons(self.scene.__scene_name__, "💰 Купить авто платёж налогов", "upgrade"))
        buttons.append(create_buttons(self.scene.__scene_name__, "⬅ Назад", "to_page", "upgrade-menu"))
        return buttons
        
    
    @OneUserPage.on_callback("upgrade")
    async def upgrade_logistic(self, callback, args):
        company_id = self.scene.get_key("scene", "company_id")
        result = await set_autopay_taxe(company_id=company_id)
        if "error" in result:
            await callback.answer(f"{result['error']}", show_alert=True)
        else:
            await callback.answer("✅ Автоплатеж налогов успешно куплен!", show_alert=True)
            await self.scene.update_page("upgrade-menu")