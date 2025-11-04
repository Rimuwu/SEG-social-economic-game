from oms import Page
from aiogram.types import CallbackQuery
from oms.utils import callback_generator
from modules.ws_client import get_factories, factory_set_produce, factory_set_auto
from modules.resources import get_resource
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class FactoryChangeMode(Page):
    """Страница изменения режима производства заводов"""
    
    __page_name__ = "factory-change-mode"
    
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
        """Показать доступные группы для изменения режима"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        change_mode_stage = scene_data.get('change_mode_stage', 'select_type')
        error_message = scene_data.get('change_mode_error')
        
        # Очищаем ошибку после отображения
        if error_message:
            scene_data.pop('change_mode_error', None)
            await self.scene.set_data('scene', scene_data)
        
        # Получаем все заводы компании
        factories = await get_factories(company_id)
        
        if not factories or not isinstance(factories, list):
            return "❌ Не удалось загрузить список заводов"
        
        if change_mode_stage == 'select_type':
            # Фильтруем заводы по типу (автоматические и неавтоматические)
            # Только скомплектованные заводы (complectation != None) и не в перекомплектации
            auto_factories = [
                f for f in factories 
                if f.get('is_auto', False) 
                and f.get('complectation') is not None
                and f.get('complectation_stages', 0) == 0
            ]
            manual_factories = [
                f for f in factories 
                if not f.get('is_auto', False) 
                and f.get('complectation') is not None
                and f.get('complectation_stages', 0) == 0
            ]
            
            content = "🔄 **Изменение режима производства**\n\n"
            content += "Выберите тип заводов для изменения:\n\n"
            content += f"🤖 **Автоматические:** {len(auto_factories)} шт.\n"
            content += f"   _Можно сделать неавтоматическими_\n\n"
            content += f"👤 **Неавтоматические:** {len(manual_factories)} шт.\n"
            content += f"   _Можно сделать автоматическими_\n"
            
            return content
            
        elif change_mode_stage == 'select_group':
            # Показываем группы ресурсов выбранного типа
            factory_type = scene_data.get('change_mode_type')
            
            if factory_type == 'auto':
                filtered_factories = [
                    f for f in factories 
                    if f.get('is_auto', False) 
                    and f.get('complectation') is not None
                    and f.get('complectation_stages', 0) == 0
                ]
                mode_text = "автоматических"
                target_mode = "неавтоматический"
            else:
                filtered_factories = [
                    f for f in factories 
                    if not f.get('is_auto', False) 
                    and f.get('complectation') is not None
                    and f.get('complectation_stages', 0) == 0
                ]
                mode_text = "неавтоматических"
                target_mode = "автоматический"
            
            # Группируем по ресурсам
            groups = {}
            for factory in filtered_factories:
                complectation = factory.get('complectation')
                if complectation not in groups:
                    groups[complectation] = []
                groups[complectation].append(factory)
            # Формируем текст
            content = f"🔄 **Изменение режима {mode_text} заводов**\n\n"
            content += f"Выберите группу для изменения на {target_mode} режим:\n\n"
            
            if not groups:
                content += f"❌ Нет {mode_text} заводов для изменения"
            else:
                content += "📦 **Доступные группы:**\n"
                for resource_key, factories_list in groups.items():
                    resource_name = self.get_resource_name(resource_key)
                    content += f"• {resource_name}: **{len(factories_list)}** шт.\n"
            
            return content
            
        elif change_mode_stage == 'enter_count':
            # Показываем запрос количества заводов
            factory_type = scene_data.get('change_mode_type')
            resource_key = scene_data.get('change_mode_resource')
            
            if factory_type == 'auto':
                mode_text = "автоматических"
                target_mode = "неавтоматический"
            else:
                mode_text = "неавтоматических"
                target_mode = "автоматический"
            
            # Получаем количество доступных заводов в группе
            if factory_type == 'auto':
                filtered_factories = [
                    f for f in factories 
                    if f.get('is_auto', False) 
                    and f.get('complectation') is not None
                    and f.get('complectation_stages', 0) == 0
                ]
            else:
                filtered_factories = [
                    f for f in factories 
                    if not f.get('is_auto', False) 
                    and f.get('complectation') is not None
                    and f.get('complectation_stages', 0) == 0
                ]
            
            # Фильтруем по ресурсу
            if resource_key != 'all':
                available_count = sum(1 for f in filtered_factories if f.get('complectation') == resource_key)
                resource_name = self.get_resource_name(resource_key)
            else:
                available_count = len(filtered_factories)
                resource_name = "Все заводы"
            
            content = f"🔄 **Изменение режима {mode_text} заводов**\n\n"
            
            # Показываем ошибку, если она есть
            if error_message:
                content += f"❌ **{error_message}**\n\n"
            
            content += f"Группа: {resource_name}\n"
            content += f"Доступно заводов: **{available_count}**\n\n"
            content += f"Введите количество заводов для перевода в {target_mode} режим:"
            
            return content
    
    async def buttons_worker(self):
        """Генерация кнопок в зависимости от этапа"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        change_mode_stage = scene_data.get('change_mode_stage', 'select_type')
        
        buttons = []
        
        # Получаем заводы
        factories = await get_factories(company_id)
        
        if not factories or not isinstance(factories, list):
            buttons.append({
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'back_to_menu'
                ),
                'next_line': True
            })
            return buttons
        
        if change_mode_stage == 'select_type':
            # Кнопки выбора типа заводов
            auto_factories = [
                f for f in factories 
                if f.get('is_auto', False) 
                and f.get('complectation') is not None
                and f.get('complectation_stages', 0) == 0
            ]
            manual_factories = [
                f for f in factories 
                if not f.get('is_auto', False) 
                and f.get('complectation') is not None
                and f.get('complectation_stages', 0) == 0
            ]
            
            if auto_factories:
                buttons.append({
                    'text': f'🤖 Автоматические ({len(auto_factories)})',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'select_type',
                        'auto'
                    ),
                    'ignore_row': True
                })
            
            if manual_factories:
                buttons.append({
                    'text': f'👤 Неавтоматические ({len(manual_factories)})',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'select_type',
                        'manual'
                    ),
                    'ignore_row': True
                })
            
        elif change_mode_stage == 'select_group':
            # Кнопки выбора группы ресурсов
            factory_type = scene_data.get('change_mode_type')
            
            if factory_type == 'auto':
                filtered_factories = [
                    f for f in factories 
                    if f.get('is_auto', False) 
                    and f.get('complectation') is not None
                    and f.get('complectation_stages', 0) == 0
                ]
            else:
                filtered_factories = [
                    f for f in factories 
                    if not f.get('is_auto', False) 
                    and f.get('complectation') is not None
                    and f.get('complectation_stages', 0) == 0
                ]
            
            # Группируем по ресурсам
            groups = {}
            for factory in filtered_factories:
                complectation = factory.get('complectation')
                if complectation not in groups:
                    groups[complectation] = []
                groups[complectation].append(factory)
            
            # Добавляем кнопки для каждой группы
            for resource_key, factories_list in sorted(groups.items()):
                resource_name = self.get_resource_name(resource_key)
                buttons.append({
                    'text': f'{resource_name} ({len(factories_list)})',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'select_group',
                        resource_key
                    ),
                    'ignore_row': True
                })
            
            # Кнопка "Все заводы"
            if len(groups) > 1:
                total_count = sum(len(factories_list) for factories_list in groups.values())
                buttons.append({
                    'text': f'✅ Все заводы ({total_count})',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'select_group',
                        'all'
                    ),
                    'ignore_row': True
                })
        
        elif change_mode_stage == 'enter_count':
            # На этапе ввода количества только кнопка назад
            pass
        
        # Кнопка "Назад"
        buttons.append({
            'text': '↪️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back' if change_mode_stage in ['select_group', 'enter_count'] else 'back_to_menu'
            ),
            'next_line': True
        })
        
        self.row_width = 1
        return buttons
    
    @Page.on_callback('select_type')
    async def select_type_handler(self, callback: CallbackQuery, args: list):
        """Обработка выбора типа заводов"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: тип не указан", show_alert=True)
            return
        
        factory_type = args[1]  # 'auto' или 'manual'
        scene_data = self.scene.get_data('scene')
        
        # Сохраняем выбранный тип
        scene_data['change_mode_type'] = factory_type
        scene_data['change_mode_stage'] = 'select_group'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('select_group')
    async def select_group_handler(self, callback: CallbackQuery, args: list):
        """Обработка выбора группы - переход к вводу количества"""
        if len(args) < 2:
            await callback.answer("❌ Ошибка: группа не указана", show_alert=True)
            return
        
        resource_key = args[1]  # ключ ресурса или 'all'
        scene_data = self.scene.get_data('scene')
        
        # Сохраняем выбранный ресурс
        scene_data['change_mode_resource'] = resource_key
        scene_data['change_mode_stage'] = 'enter_count'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_text('int')
    async def handle_text_input(self, message, value: int):
        """Обработка ввода количества заводов"""
        scene_data = self.scene.get_data('scene')
        
        if value <= 0:
            # Сохраняем ошибку и обновляем страницу
            scene_data['change_mode_error'] = "Количество должно быть больше 0"
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Сохраняем количество
        scene_data['change_mode_count'] = value
        await self.scene.set_data('scene', scene_data)
        
        # Выполняем изменение режима
        await self._perform_mode_change()
    
    async def _perform_mode_change(self):
        """Выполнить изменение режима для заводов"""
        scene_data = self.scene.get_data('scene')
        
        resource_key = scene_data.get('change_mode_resource')
        count = scene_data.get('change_mode_count')
        factory_type = scene_data.get('change_mode_type')
        company_id = scene_data.get('company_id')
        
        if not all([company_id, factory_type, resource_key, count]):
            await self._set_status("❌ Ошибка: недостаточно данных", "error")
            return
        
        # Получаем заводы
        factories = await get_factories(company_id)
        
        if not factories or not isinstance(factories, list):
            await self._set_status("❌ Не удалось загрузить заводы", "error")
            return
        
        # Фильтруем заводы по типу
        if factory_type == 'auto':
            filtered_factories = [
                f for f in factories 
                if f.get('is_auto', False) 
                and f.get('complectation') is not None
                and f.get('complectation_stages', 0) == 0
            ]
            target_auto = False  # Делаем неавтоматическими
            action_text = "переведены в неавтоматический режим"
        else:
            filtered_factories = [
                f for f in factories 
                if not f.get('is_auto', False) 
                and f.get('complectation') is not None
                and f.get('complectation_stages', 0) == 0
            ]
            target_auto = True  # Делаем автоматическими
            action_text = "переведены в автоматический режим"
        
        # Фильтруем по группе
        if resource_key != 'all':
            target_factories = [
                f for f in filtered_factories 
                if f.get('complectation') == resource_key
            ]
        else:
            target_factories = filtered_factories
        
        # Проверяем доступное количество
        if count > len(target_factories):
            scene_data['change_mode_error'] = f"Доступно только {len(target_factories)} заводов"
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Берём нужное количество заводов
        target_factories = target_factories[:count]
        
        if not target_factories:
            await self._set_status("❌ Нет заводов для изменения", "error")
            await self.scene.update_page('factory-menu')
            return
        
        # Изменяем режим для каждого завода
        success_count = 0
        failed_count = 0
        
        for factory in target_factories:
            factory_id = factory.get('id')
            if not factory_id:
                failed_count += 1
                continue
            
            try:
                if target_auto:
                    # Переводим в автоматический режим
                    result = await factory_set_auto(factory_id=factory_id, is_auto=True)
                else:
                    # Переводим в неавтоматический режим
                    # Сначала делаем не-авто, затем останавливаем производство
                    result = await factory_set_auto(factory_id=factory_id, is_auto=False)
                
                if result and result.get('success'):
                    success_count += 1
                else:
                    failed_count += 1
                    bot_logger.error(f"Failed to change mode for factory {factory_id}: {result}")
            except Exception as e:
                failed_count += 1
                bot_logger.error(f"Error changing mode for factory {factory_id}: {e}")
        
        # Формируем сообщение
        if success_count > 0:
            message = f"✅ Заводов {action_text}: {success_count}"
            if failed_count > 0:
                message += f"\n⚠️ Ошибок: {failed_count}"
            await self._set_status(message, "success")
        else:
            await self._set_status(f"❌ Не удалось изменить режим ни одного завода", "error")
        
        # Очищаем данные и возвращаемся в меню
        scene_data['change_mode_stage'] = 'select_type'
        scene_data.pop('change_mode_type', None)
        scene_data.pop('change_mode_resource', None)
        scene_data.pop('change_mode_count', None)
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('factory-menu')
    
    def _set_status(self, message: str, level: str = "info"):
        """Установить статусное сообщение"""
        scene_data = self.scene.get_data('scene')
        if not scene_data:
            scene_data = {}
        scene_data['status'] = message
        scene_data['status_level'] = level
        return self.scene.set_data('scene', scene_data)
    
    @Page.on_callback('change_group')
    async def change_group_handler(self, callback: CallbackQuery, args: list):
        """УСТАРЕВШИЙ ОБРАБОТЧИК - теперь используется select_group + текстовый ввод"""
        # Оставляем для обратной совместимости, но функционал перенесён
        await callback.answer("⚠️ Используйте новый интерфейс", show_alert=True)
    
    @Page.on_callback('back')
    async def back_handler(self, callback: CallbackQuery, args: list):
        """Возврат к предыдущему этапу"""
        scene_data = self.scene.get_data('scene')
        current_stage = scene_data.get('change_mode_stage', 'select_type')
        
        if current_stage == 'enter_count':
            # Возврат к выбору группы
            scene_data['change_mode_stage'] = 'select_group'
            scene_data.pop('change_mode_resource', None)
            scene_data.pop('change_mode_count', None)
            scene_data.pop('change_mode_error', None)
        elif current_stage == 'select_group':
            # Возврат к выбору типа
            scene_data['change_mode_stage'] = 'select_type'
            scene_data.pop('change_mode_type', None)
        
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('back_to_menu')
    async def back_to_menu_handler(self, callback: CallbackQuery, args: list):
        """Возврат в меню заводов"""
        # Очищаем данные
        scene_data = self.scene.get_data('scene')
        scene_data.pop('change_mode_stage', None)
        scene_data.pop('change_mode_type', None)
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('factory-menu')
        await callback.answer()
