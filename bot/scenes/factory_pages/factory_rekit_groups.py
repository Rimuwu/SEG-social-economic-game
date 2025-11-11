from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import Message, CallbackQuery
from modules.ws_client import get_factories
from oms.utils import callback_generator
from modules.resources import get_resource, get_resource_name, get_resource_emoji

Page = OneUserPage

class FactoryRekitGroups(Page):
    __page_name__ = "factory-rekit-groups"
    __for_blocked_pages__ = ["factory-menu"]
    def get_resource_name(self, resource_key: str) -> str:
        """Получить русское название ресурса"""
        return get_resource_name(resource_key)
    
    async def content_worker(self):
        """Показать группы заводов для перекомплектации"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        try:
            factories = self.scene.get_key(self.__page_name__, 'factories_data')
            if factories is None:
                factories = await get_factories(company_id=company_id)
                await self.scene.update_key(self.__page_name__, 'factories_data', factories)
            
            # get_factories возвращает список напрямую
            if not factories or not isinstance(factories, list):
                return "❌ Не удалось загрузить список заводов"
            
            # Группируем заводы по ресурсам и считаем простаивающие
            idle_count = 0
            resource_groups = {}
            
            for factory in factories:
                complectation = factory.get('complectation')
                
                if complectation is None:
                    idle_count += 1
                else:
                    if complectation not in resource_groups:
                        resource_groups[complectation] = 0
                    resource_groups[complectation] += 1
            
            # Формируем текст групп
            lines = []
            
            if idle_count > 0:
                lines.append(f"⚪️ Простаивающие: *{idle_count}* шт.")
            
            if resource_groups:
                for resource_key, count in resource_groups.items():
                    resource_display = self.get_resource_name(resource_key)
                    lines.append(f"{resource_display}: *{count}* шт.")
            
            if idle_count == 0 and not resource_groups:
                groups_text = "❌ Нет заводов для перекомплектации"
            else:
                groups_text = "\n".join(lines)
            
            return self.content.format(groups_text=groups_text)
            
        except Exception as e:
            return f"❌ Ошибка при загрузке данных: {str(e)}"
    
    async def buttons_worker(self):
        """Кнопки с группами заводов"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        buttons = []
        
        if company_id:
            factories = self.scene.get_key(self.__page_name__, 'factories_data')
            if factories is None:
                factories = await get_factories(company_id=company_id)
                await self.scene.update_key(self.__page_name__, 'factories_data', factories)
            
            # get_factories возвращает список напрямую
            if factories and isinstance(factories, list):
                # Группируем заводы
                idle_count = 0
                resource_groups = {}
                
                for factory in factories:
                    complectation = factory.get('complectation')
                    
                    if complectation is None:
                        idle_count += 1
                    else:
                        if complectation not in resource_groups:
                            resource_groups[complectation] = 0
                        resource_groups[complectation] += 1
                
                # Кнопка для простаивающих заводов
                if idle_count > 0:
                    buttons.append({
                        'text': f'⚪️ Простаивающие ({idle_count})',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'select_group',
                            'idle'
                        )
                    })
                
                # Кнопки для групп заводов по ресурсам
                for resource_key, count in resource_groups.items():
                    resource = get_resource(resource_key)
                    resource_name = resource.label if resource else resource_key
                    resource_emoji = resource.emoji if resource else '📦'
                    
                    buttons.append({
                        'text': f'{resource_emoji} {resource_name} ({count})',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'select_group',
                            resource_key
                        )
                    })
        
        # Кнопка назад
        buttons.append({
            'text': '↪️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back'
            )
        })
        
        self.row_width = 1
        return buttons
    
    @Page.on_callback('select_group')
    async def select_group(self, callback: CallbackQuery, args: list):
        """Выбор группы заводов"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: группа не указана", show_alert=True)
            return
        
        group_type = args[1]  # 'idle' или resource_key
        
        # Сохраняем выбранную группу для следующей страницы
        scene_data = self.scene.get_data('scene')
        scene_data['rekit_group'] = group_type
        await self.scene.set_data('scene', scene_data)
        
        # Переходим на страницу ввода количества
        await self.scene.update_page('factory-rekit-count')
        await callback.answer()
    
    @Page.on_callback('back')
    async def back_to_menu(self, callback: CallbackQuery, args: list):
        """Возврат в меню заводов"""
        await self.scene.update_page('factory-menu')
        await callback.answer()
