from oms import Page
from aiogram.types import CallbackQuery
from oms.utils import callback_generator
from modules.ws_client import factory_set_produce, get_factories
from modules.resources import get_resource


class FactoryStartGroups(Page):
    """Страница запуска заводов по группам ресурсов"""
    
    __page_name__ = "factory-start-groups"
    
    def get_resource_name(self, resource_key):
        """Получить отображаемое имя ресурса"""
        if resource_key is None:
            return "Неизвестный ресурс"
        
        resource = get_resource(resource_key)
        if resource:
            emoji = getattr(resource, 'emoji', '')
            label = getattr(resource, 'label', resource_key)
            return f"{emoji} {label}" if emoji else label
        return resource_key
    
    async def content_worker(self):
        """Показать доступные группы ресурсов для запуска"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        # Получаем все заводы компании
        factories = await get_factories(company_id)
        
        if not factories or not isinstance(factories, list):
            return "❌ Не удалось загрузить список заводов"
        
        # Фильтруем заводы готовые к запуску:
        # - complectation != None (скомплектованные)
        # - complectation_stages == 0 (не перекомплектуются)
        # - is_auto = False (не автоматические, требуют ручного запуска)
        # - produce = False (не запущены вручную)
        startable_factories = [
            f for f in factories 
            if f.get('complectation') is not None 
            and f.get('complectation_stages', 0) == 0
            and not f.get('is_auto', False)
            and not f.get('produce', False)  # Проверяем флаг produce, а не is_working
        ]
        
        # Группируем по ресурсам
        groups = {}
        for factory in startable_factories:
            complectation = factory.get('complectation')
            if complectation not in groups:
                groups[complectation] = []
            groups[complectation].append(factory)
        
        # Работающие НЕ автоматические заводы (для статистики)
        working_manual = [
            f for f in factories 
            if f.get('is_working', False)
            and not f.get('is_auto', False)
            and f.get('complectation') is not None
        ]
        
        content = "🏭 **Запуск заводов**\n\n"
        content += f"⏸️ Заводов готовых к запуску: {len(startable_factories)}\n"
        content += f"▶️ Не автоматических заводов работает: {len(working_manual)}\n\n"
        
        if not startable_factories:
            content += "❌ Нет заводов, готовых к запуску.\n\n"
        else:
            content += "📦 **Доступные группы:**\n"
            for resource_key, factories_list in groups.items():
                resource_display = self.get_resource_name(resource_key)
                content += f"  {resource_display}: **{len(factories_list)}** шт. ⏸️\n"
            content += "\nВыберите группу для запуска или запустите все:"
        
        return content
    
    async def buttons_worker(self):
        """Генерация кнопок выбора группы"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        buttons = []
        
        # Получаем заводы
        factories = await get_factories(company_id)
        
        if factories and isinstance(factories, list):
            # Фильтруем заводы готовые к запуску:
            # - complectation != None (скомплектованные)
            # - complectation_stages == 0 (не перекомплектуются)
            # - is_auto = False (не автоматические)
            # - produce = False (не работают)
            startable_factories = [
                f for f in factories 
                if f.get('complectation') is not None 
                and f.get('complectation_stages', 0) == 0
                and not f.get('is_auto', False)
                and not f.get('produce', False)
            ]
            
            if startable_factories:
                # Группируем по ресурсам
                groups = {}
                for factory in startable_factories:
                    complectation = factory.get('complectation')
                    if complectation not in groups:
                        groups[complectation] = []
                    groups[complectation].append(factory)
                
                # Добавляем кнопки для каждой группы
                for resource_key, factories_list in groups.items():
                    resource_display = self.get_resource_name(resource_key)
                    buttons.append({
                        'text': f'{resource_display} ({len(factories_list)} шт.)',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'start_group',
                            resource_key
                        ),
                        'next_line': True
                    })
                
                # Кнопка "Запустить все"
                buttons.append({
                    'text': f'🚀 Запустить все ({len(startable_factories)} шт.)',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'start_all'
                    ),
                    'next_line': True,
                    'ignore_row': True
                })
        
        # Кнопка "Назад"
        buttons.append({
            'text': '↪️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_to_menu'
            ),
            'next_line': True
        })
        
        self.row_width = 1
        return buttons
    
    @Page.on_callback('start_group')
    async def start_group_handler(self, callback: CallbackQuery, args: list):
        """Обработка запуска группы заводов"""
        # args[0] = 'start_group', args[1] = resource_key
        if not args or len(args) < 2:
            await callback.answer("❌ Не указана группа", show_alert=True)
            return
        
        resource_key = args[1]  # Ключ ресурса находится в args[1], а не args[0]!
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        # Получаем заводы
        factories = await get_factories(company_id)
        
        if not factories:
            await callback.answer("❌ Ошибка загрузки заводов", show_alert=True)
            return
        
        # Логируем для отладки
        print(f"=== START GROUP DEBUG for resource: {resource_key} ===")
        for f in factories:
            if f.get('complectation') == resource_key:
                print(f"Factory {f.get('id')}: complectation={f.get('complectation')}, "
                      f"stages={f.get('complectation_stages', 0)}, "
                      f"is_auto={f.get('is_auto', False)}, "
                      f"produce={f.get('produce', False)}, "
                      f"is_working={f.get('is_working', False)}")
        
        # Фильтруем заводы этой группы, готовые к запуску
        target_factories = [
            f['id'] for f in factories 
            if f.get('complectation') == resource_key
            and f.get('complectation_stages', 0) == 0
            and not f.get('is_auto', False)
            and not f.get('produce', False)
        ]
        
        print(f"Target factories to start: {target_factories}")
        
        if not target_factories:
            await callback.answer("❌ Нет заводов для запуска в этой группе", show_alert=True)
            return
        
        # Запускаем заводы группы
        success_count = 0
        for factory_id in target_factories:
            result = await factory_set_produce(factory_id, True)
            if result:
                success_count += 1
        
        if success_count > 0:
            resource_display = self.get_resource_name(resource_key)
            await callback.answer(
                f"✅ Запущено {resource_display}: {success_count} шт.",
                show_alert=True
            )
            await self.scene.update_page('factory-menu')
        else:
            await callback.answer("❌ Ошибка запуска", show_alert=True)
    
    @Page.on_callback('start_all')
    async def start_all_handler(self, callback: CallbackQuery, args: list):
        """Обработка запуска всех заводов"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        # Получаем заводы
        factories = await get_factories(company_id)
        
        if not factories:
            await callback.answer("❌ Ошибка загрузки заводов", show_alert=True)
            return
        
        # Фильтруем заводы готовые к запуску:
        # - complectation != None (скомплектованные)
        # - complectation_stages == 0 (не перекомплектуются)
        # - is_auto = False (не автоматические)
        # - produce = False (не работают)
        target_factories = [
            f['id'] for f in factories 
            if f.get('complectation') is not None 
            and f.get('complectation_stages', 0) == 0
            and not f.get('is_auto', False)
            and not f.get('produce', False)
        ]
        
        if not target_factories:
            await callback.answer("❌ Нет заводов для запуска", show_alert=True)
            return
        
        # Запускаем все (устанавливаем produce=True для каждого)
        success_count = 0
        for factory_id in target_factories:
            result = await factory_set_produce(factory_id, True)
            if result:
                success_count += 1
        
        if success_count > 0:
            await callback.answer(
                f"✅ Запущено заводов: {success_count}",
                show_alert=True
            )
            await self.scene.update_page('factory-menu')
        else:
            await callback.answer("❌ Ошибка запуска", show_alert=True)
    
    @Page.on_callback('back_to_menu')
    async def back_to_menu_handler(self, callback: CallbackQuery, args: list):
        """Возврат в меню заводов"""
        await self.scene.update_page('factory-menu')
