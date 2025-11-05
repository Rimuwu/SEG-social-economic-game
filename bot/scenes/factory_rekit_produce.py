from oms import Page
from aiogram.types import CallbackQuery
from oms.utils import callback_generator
from global_modules.logs import Logger
from global_modules.load_config import ALL_CONFIGS, Resources
from modules.ws_client import company_complete_free_factories, get_factories, factory_set_auto, factory_recomplectation

bot_logger = Logger.get_logger("bot")
RESOURCES: Resources = ALL_CONFIGS["resources"]


class FactoryRekitProduce(Page):
    __page_name__ = "factory-rekit-produce"
    
    async def content_worker(self):
        """Показать выбор типа производства с крафтом"""
        scene_data = self.scene.get_data('scene')
        
        group_type = scene_data.get('rekit_group')
        count = scene_data.get('rekit_count')
        resource_key = scene_data.get('rekit_resource')
        
        if not all([group_type, count, resource_key]):
            return "❌ Ошибка: недостаточно данных для перекомплектации"
        
        # Получаем информацию о ресурсе
        resource = RESOURCES.get_resource(resource_key)
        if not resource:
            return "❌ Ошибка: ресурс не найден"
        
        # Формируем текст
        content = "🔄 **Перекомплектация заводов**\n\n"
        content += f"Продукт: {resource.emoji} {resource.label}\n"
        content += f"Количество заводов: {count}\n\n"
        
        # Показываем крафт продукта
        if hasattr(resource, 'production') and resource.production:
            content += "📋 **Крафт:**\n"
            materials = resource.production.materials
            output = resource.production.output
            
            # Формируем список материалов
            materials_list = []
            for mat_key, mat_count in materials.items():
                mat_resource = RESOURCES.get_resource(mat_key)
                if mat_resource:
                    materials_list.append(f"{mat_count}× {mat_resource.emoji} {mat_resource.label}")
            
            if materials_list:
                content += "   " + " + ".join(materials_list) + f" → {output}× {resource.emoji} {resource.label}\n\n"
        
        content += "⏳ _Перекомплектация займёт 1 ход_\n\n"
        content += "Выберите режим производства:\n\n"
        content += "🔄 **Автоматический** - завод будет производить ресурс каждый ход автоматически\n\n"
        content += "🎯 **Не автоматический** - завод нужно запускать вручную"
        
        return content
    
    async def buttons_worker(self):
        """Кнопки выбора режима производства"""
        buttons = [
            {
                'text': '🔄 Автоматический',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'produce_auto'
                ),
                'ignore_row': True
            },
            {
                'text': '🎯 Не автоматический',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'produce_manual'
                ),
                'ignore_row': True
            },
            {
                'text': '↪️ Назад',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'back'
                ),
                'next_line': True
            }
        ]
        
        return buttons
    
    @Page.on_callback('produce_auto')
    async def set_auto_produce(self, callback: CallbackQuery, args: list):
        """Установить автоматическое производство"""
        await self._complete_recomplectation(callback, is_auto=True)
    
    @Page.on_callback('produce_manual')
    async def set_manual_produce(self, callback: CallbackQuery, args: list):
        """Установить неавтоматическое производство"""
        await self._complete_recomplectation(callback, is_auto=False)
    
    async def _complete_recomplectation(self, callback: CallbackQuery, is_auto: bool):
        """Выполнить перекомплектацию с указанным режимом производства"""
        scene_data = self.scene.get_data('scene')
        
        group_type = scene_data.get('rekit_group')
        count = int(scene_data.get('rekit_count'))
        resource_key = scene_data.get('rekit_resource')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            await callback.answer("❌ Ошибка: ID компании не найден", show_alert=True)
            return
        
        # Сначала получаем список заводов для перекомплектации
        bot_logger.info(f"Fetching factories for recomplectation: company_id={company_id}, group_type={group_type}")
        all_factories = await get_factories(company_id=company_id)
        
        if not all_factories or not isinstance(all_factories, list):
            await callback.answer("❌ Не удалось получить список заводов", show_alert=True)
            return
        
        # Фильтруем заводы по группе
        if group_type == 'idle':
            target_factories = [f for f in all_factories if f.get('complectation') is None]
        else:
            target_factories = [f for f in all_factories if f.get('complectation') == group_type]
        
        bot_logger.info(f"Found {len(target_factories)} factories to recomplete")
        
        if not target_factories:
            await callback.answer("❌ Нет заводов для перекомплектации", show_alert=True)
            return
        
        if len(target_factories) < count:
            await callback.answer(f"❌ Недостаточно заводов! Доступно: {len(target_factories)}", show_alert=True)
            return
        
        # Перекомплектуем и устанавливаем is_auto для каждого завода
        success_count = 0
        for i in range(min(count, len(target_factories))):
            factory = target_factories[i]
            factory_id = factory['id']
            
            # Перекомплектация
            rekit_result = await factory_recomplectation(factory_id, resource_key)
            if rekit_result and isinstance(rekit_result, dict) and rekit_result.get('success'):
                # Устанавливаем is_auto
                auto_result = await factory_set_auto(factory_id, is_auto)
                if auto_result:
                    success_count += 1
                    bot_logger.info(f"Successfully recompleted and set is_auto={is_auto} for factory {factory_id}")
                else:
                    bot_logger.error(f"Failed to set is_auto for factory {factory_id}")
            else:
                bot_logger.error(f"Failed to recomplete factory {factory_id}: {rekit_result}")
        
        if success_count > 0:
            resource = RESOURCES.get_resource(resource_key)
            resource_name = f"{resource.emoji} {resource.label}" if resource else resource_key
            mode_text = "🔄 Автоматический" if is_auto else "🎯 Не автоматический"
            
            # Определяем время перекомплектации из lvl (уровень ресурса)
            rekit_time = resource.lvl if resource else 1
            
            # Очищаем временные данные
            scene_data.pop('rekit_group', None)
            scene_data.pop('rekit_count', None)
            scene_data.pop('rekit_resource', None)
            await self.scene.set_data('scene', scene_data)
            
            
            # Возвращаемся в меню заводов
            await self.scene.update_page('factory-menu')
        else:
            await callback.answer("❌ Не удалось перекомплектовать заводы", show_alert=True)
        
        await callback.answer()
    
    @Page.on_callback('back')
    async def back_to_resource(self, callback: CallbackQuery, args: list):
        """Возврат к выбору ресурса"""
        await self.scene.update_page('factory-rekit-resource')
        await callback.answer()
