from oms import Page
from aiogram.types import Message
from modules.ws_client import get_company, get_company_users

class AboutInfo(Page):
    
    __page_name__ = "about-info-menu"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        company_data = await get_company(id=company_id)
        name = company_data.get('name', 'Неизвестно')
        balance = company_data.get('balance', 0)
        business_type = company_data.get('business_type', 'unknown')
        type_b = "Малый бизнес" if business_type == 'small' else "Большой бизнес"
        owner_id = company_data.get('owner')
        users_list = company_data.get('users', [])
        owner_username = None
        other_users = []
        
        for user in users_list:
            if user.get('id') == owner_id:
                owner_username = user.get('username', f"ID: {owner_id}")
            else:
                other_users.append(user.get('username', f"ID: {user.get('id')}"))
        
        if other_users:
            text_users = "\n"
            for username in other_users:
                text_users += f"  • {username}\n"
        else:
            text_users = "Нет других участников"

        return self.content.format(
            name=name,
            balance=balance,
            type_b=type_b,
            owner=owner_username,
            text_users=text_users
        )
