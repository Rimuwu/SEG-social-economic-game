from oms import Page
from aiogram.types import CallbackQuery
from modules.ws_client import get_company
from oms.utils import callback_generator
from global_modules.bank import get_credit_conditions
from global_modules.load_config import ALL_CONFIGS


class BankCreditMain(Page):
    """Главная страница кредитов со списком активных кредитов"""
    
    __page_name__ = "bank-credit-main"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        reputation = company_data.get('reputation', 0)
        credits = company_data.get('credits', [])
        
        # Получаем сообщение об успехе, если есть
        success_message = scene_data.get('success_message', '')
        
        # Получаем условия кредитования
        try:
            conditions = get_credit_conditions(reputation)
            
            # Параметры для шаблона
            percent = conditions.percent * 100
            without_interest = conditions.without_interest
            max_credits = ALL_CONFIGS['settings'].max_credits_per_company
            
            # Формируем секцию с активными кредитами
            if credits and len(credits) > 0:
                credits_list = "*Активные кредиты:*\n\n"
                for i, credit in enumerate(credits, 1):
                    total = credit.get("total_to_pay", 0)
                    paid = credit.get("paid", 0)
                    need_pay = credit.get("need_pay", 0)
                    steps_total = credit.get("steps_total", 0)
                    steps_now = credit.get("steps_now", 0)
                    
                    remaining = total - paid
                    steps_left = steps_total - steps_now
                    
                    total_formatted = f"{total:,}".replace(",", " ")
                    remaining_formatted = f"{remaining:,}".replace(",", " ")
                    need_pay_formatted = f"{need_pay:,}".replace(",", " ")
                    
                    credits_list += f"*Кредит #{i}*\n"
                    credits_list += f"Осталось выплатить: {remaining_formatted} 💰 (из {total_formatted})\n"
                    credits_list += f"Текущий платеж: {need_pay_formatted} 💰\n"
                    credits_list += f"Ходов до закрытия: {max(0, steps_left)}/{steps_total}\n"
                    
                    if need_pay > 0:
                        credits_list += "⚠️ *Требуется оплата!*\n"
                    
                    credits_list += "\n"
                
                active_credits_section = credits_list
            else:
                active_credits_section = "_У вас нет активных кредитов_"
            
            # Формируем текст из шаблона
            text = self.content.format(
                percent=percent,
                without_interest=without_interest,
                reputation=reputation,
                credits_count=len(credits),
                max_credits=max_credits,
                active_credits_section=active_credits_section
            )
            
        except ValueError:
            # Если репутация недостаточна
            text = f"💳 *Кредиты*\n\n❌ *Кредиты недоступны*\nМинимальная репутация для кредита: 11\nВаша репутация: {reputation} ⭐"
        
        # Добавляем сообщение об успехе, если есть
        if success_message:
            text = f"✅ {success_message}\n\n" + text
            # Очищаем сообщение после показа
            scene_data['success_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        buttons = []
        self.row_width = 1
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        
        if isinstance(company_data, dict):
            reputation = company_data.get('reputation', 0)
            credits = company_data.get('credits', [])
            
            # Проверяем возможность взять кредит (репутация и лимит)
            max_credits = ALL_CONFIGS['settings'].max_credits_per_company
            can_take_credit = len(credits) < max_credits
            
            if can_take_credit:
                try:
                    get_credit_conditions(reputation)
                    buttons.append({
                        'text': '💰 Взять кредит',
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'take_credit'
                        )
                    })
                except ValueError:
                    pass
            
            # Кнопки для оплаты кредитов
            if credits and len(credits) > 0:
                for i, credit in enumerate(credits):
                    total = credit.get("total_to_pay", 0)
                    paid = credit.get("paid", 0)
                    remaining = total - paid
                    
                    if remaining > 0:
                        buttons.append({
                            'text': f'💸 Оплатить кредит #{i+1} (осталось {remaining:,} 💰)'.replace(",", " "),
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'pay_credit',
                                str(i)
                            )
                        })
        
        return buttons
    
    @Page.on_callback('take_credit')
    async def take_credit_handler(self, callback: CallbackQuery, args: list):
        """Начало процесса взятия кредита - переход на страницу ввода срока"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        # Проверяем репутацию и количество кредитов перед началом процесса
        company_data = await get_company(id=company_id)
        if isinstance(company_data, dict):
            reputation = company_data.get('reputation', 0)
            credits = company_data.get('credits', [])
            
            # Проверяем максимальное количество кредитов
            max_credits = ALL_CONFIGS['settings'].max_credits_per_company
            if len(credits) >= max_credits:
                await callback.answer(
                    f"❌ Достигнут лимит кредитов!\n"
                    f"Максимум кредитов на компанию: {max_credits}\n"
                    f"Погасите существующие кредиты перед взятием новых.",
                    show_alert=True
                )
                return
            
            # Проверяем репутацию
            try:
                get_credit_conditions(reputation)
            except ValueError:
                await callback.answer(
                    "❌ Недостаточная репутация для взятия кредита!\n"
                    "Минимальная репутация: 11 ⭐",
                    show_alert=True
                )
                return
        
        # Переходим на страницу ввода срока кредита
        await self.scene.update_page('bank-credit-take-period')
        await callback.answer("💬 Введите срок кредита в сообщении")
    
    @Page.on_callback('pay_credit')
    async def pay_credit_handler(self, callback: CallbackQuery, args: list):
        """Начало процесса оплаты кредита - переход на страницу оплаты"""
        # Проверяем структуру args
        if args and args[0] == 'pay_credit':
            if len(args) < 2:
                await callback.answer("❌ Ошибка: не указан индекс кредита", show_alert=True)
                return
            credit_index = int(args[1])
        elif args and len(args) > 0:
            credit_index = int(args[0])
        else:
            await callback.answer("❌ Ошибка: не указан индекс кредита", show_alert=True)
            return
        
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        if not company_id:
            await callback.answer("❌ Ошибка: компания не найдена", show_alert=True)
            return
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        if isinstance(company_data, str):
            await callback.answer(f"❌ Ошибка: {company_data}", show_alert=True)
            return
        
        credits = company_data.get('credits', [])
        
        if credit_index < 0 or credit_index >= len(credits):
            await callback.answer("❌ Ошибка: кредит не найден", show_alert=True)
            return
        
        credit = credits[credit_index]
        total = credit.get("total_to_pay", 0)
        paid = credit.get("paid", 0)
        remaining = total - paid
        
        if remaining <= 0:
            await callback.answer("✅ Этот кредит уже полностью погашен", show_alert=True)
            return
        
        # Сохраняем индекс кредита и переходим к странице оплаты
        scene_data['pay_credit_index'] = credit_index
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-credit-pay')
        await callback.answer("💬 Введите сумму для оплаты")
