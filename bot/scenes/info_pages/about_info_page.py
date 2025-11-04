from oms import Page
from aiogram.types import Message
from modules.ws_client import get_company, get_company_users
from pprint import pprint

class AboutInfo(Page):
    
    __page_name__ = "about-info-menu"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        # Получаем данные о компании
        company_data = await get_company(id=company_id)
        
        if not company_data:
            return "❌ Не удалось загрузить данные компании"
        
        # Формируем текст
        content = "📊 *Информация о компании*\n\n"
        
        # Название компании
        company_name = company_data.get('name', 'Неизвестно')
        content += f"🏢 *Название:* {company_name}\n"
        
        # Баланс
        balance = company_data.get('balance', 0)
        content += f"💰 *Баланс:* {balance:,}\n"
        
        # Тип компании
        business_type = company_data.get('business_type', 'unknown')
        business_type_display = "Малый бизнес" if business_type == 'small' else "Большой бизнес"
        content += f"📈 *Тип:* {business_type_display}\n"
        
        # Владелец компании
        owner_id = company_data.get('owner')
        users_list = company_data.get('users', [])
        
        # Находим владельца в списке пользователей
        owner_username = None
        other_users = []
        
        for user in users_list:
            if user.get('id') == owner_id:
                owner_username = user.get('username', f"ID: {owner_id}")
            else:
                other_users.append(user.get('username', f"ID: {user.get('id')}"))
        
        if owner_username:
            content += f"👤 *Владелец:* {owner_username}\n"
        else:
            content += f"👤 *Владелец:* ID: {owner_id}\n"

        # Другие участники
        if other_users:
            content += "👥 *Участники:*\n"
            for username in other_users:
                content += f"  • {username}\n"
        else:
            content += "👥 *Участники:* Нет других участников\n"
        
        return content
        