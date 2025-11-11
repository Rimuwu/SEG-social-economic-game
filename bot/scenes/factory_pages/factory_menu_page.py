
from aiogram.types import Message, CallbackQuery
from modules.ws_client import get_factories, factory_set_auto, factory_set_produce, factory_recomplectation
from oms.utils import callback_generator
from modules.resources import get_resource_name
from scenes.utils.oneuser_page import OneUserPage


Page = OneUserPage

class FactoryMenu(Page):
    __for_blocked_pages__ = ['factory-start-groups', 'factory-rekit-groups', 'factory-rekit-count', 'factory-rekit-resource', 'factory-rekit-produce', 'factory-select-mode', 'factory-change-mode']
    __page_name__ = "factory-menu"
    def get_resource_name(self, resource_key: str) -> str:
        """Получить русское название ресурса"""
        return get_resource_name(resource_key)
    
    async def data_preparate(self):
        """Один запрос списка заводов + производных групп.
        Кэшируем до явной инвалидации после операций изменения режима / запуска / перекомплектации.
        """
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        if not company_id:
            await self.scene.update_key(self.__page_name__, "factories_data", [])
            return
        factories = await get_factories(company_id=company_id) or []
        await self.scene.update_key(self.__page_name__, "factories_data", factories)

    async def content_worker(self):
        factories = self.scene.get_key(self.__page_name__, "factories_data") or []
        if not isinstance(factories, list):
            return "❌ Не удалось загрузить список заводов"
        total = len(factories)

        idle_factories = []
        auto_factories = {}
        manual_factories = {}
        recomplecting_factories = {}

        for f in factories:
            comp = f.get('complectation')
            stages = f.get('complectation_stages', 0)
            is_auto = f.get('is_auto', False)
            if stages > 0:
                recomplecting_factories.setdefault(comp, []).append(f)
            elif comp is None:
                idle_factories.append(f)
            elif is_auto:
                auto_factories.setdefault(comp, []).append(f)
            else:
                manual_factories.setdefault(comp, []).append(f)

        def fmt_group(title, groups, extra=None):
            if not groups:
                return ''
            lines = [f"\n{title}"]
            for r, lst in groups.items():
                name = self.get_resource_name(r) if r else '—'
                if extra == 'rekit':
                    max_stages = max(x.get('complectation_stages', 0) for x in lst)
                    lines.append(f"  {name}: *{len(lst)}* шт. (осталось {max_stages} ход(-ов))")
                elif extra == 'manual':
                    working = sum(1 for x in lst if x.get('is_working', False))
                    stopped = len(lst) - working
                    if working and stopped:
                        status = f" (▶️ {working} / ⏸️ {stopped})"
                    elif working:
                        status = " (▶️ все работают)"
                    elif stopped:
                        status = " (⏸️ все остановлены)"
                    else:
                        status = ''
                    lines.append(f"  {name}: *{len(lst)}* шт.{status}")
                else:
                    lines.append(f"  {name}: *{len(lst)}* шт.")
            return "\n".join(lines) + "\n"

        recomplecting_text = fmt_group("⏳ *Перекомплектуются:*", recomplecting_factories, 'rekit')
        auto_text = fmt_group("🔄 *Автоматические заводы* (производят каждый ход):", auto_factories)
        manual_text = fmt_group("⚡ *Не автоматические заводы:*", manual_factories, 'manual')
        idle_text = f"\n⚪️ *Простаивают:* {len(idle_factories)} шт.\n"
        empty_message = '' if (auto_factories or manual_factories or idle_factories or recomplecting_factories) else "\nУ вас пока нет активных заводов."

        return self.content.format(
            total=total,
            recomplecting_text=recomplecting_text,
            auto_text=auto_text,
            manual_text=manual_text,
            idle_text=idle_text,
            empty_message=empty_message
        )
    
    async def buttons_worker(self):
        """Кнопки управления заводами"""
        buttons = [
            {
                'text': '▶️ Запустить заводы',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'start_factories'
                )
            },
            {
                'text': '🔄 Перекомплектовать',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'rekit'
                )
            },
            {
                'text': '🔀 Изменить режим',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'change_mode'
                )
            }
        ]
        
        self.row_width = 2
        return buttons
    
    @Page.on_callback('start_factories')
    async def show_start_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу запуска заводов"""
        await self.scene.update_page('factory-start-groups')
        await callback.answer()
    
    @Page.on_callback('buy_factories')
    async def show_buy_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу покупки заводов"""
        # TODO: Реализовать страницу покупки заводов
        await callback.answer("🚧 Страница покупки заводов в разработке", show_alert=True)
        # await self.scene.update_page('factory-buy')
    
    @Page.on_callback('change_mode')
    async def show_change_mode_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу изменения режима производства"""
        await self.scene.update_page('factory-change-mode')
        await callback.answer()
    
    @Page.on_callback('rekit')
    async def show_rekit_menu(self, callback: CallbackQuery, args: list):
        """Переход на страницу выбора группы заводов для перекомплектации"""
        await self.scene.update_page('factory-rekit-groups')
        await callback.answer()

    async def post_handle(self, h_type: str):
        """После любых действий на дочерних страницах логично инвалидировать factories_data."""
        # Если активная страница вернулась на меню после операции – сбрасываем кэш
        if self.scene.page == self.__page_name__:
            await self.scene.update_key(self.__page_name__, 'factories_data', None)
