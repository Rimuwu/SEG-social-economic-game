from oms import Page
from aiogram.types import CallbackQuery
from modules.ws_client import get_company, company_withdraw_deposit, get_session
from oms.utils import callback_generator


class BankDepositView(Page):
    """Страница просмотра конкретного вклада"""
    
    __page_name__ = "bank-deposit-view"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        deposit_index = scene_data.get('viewing_deposit_index', 0)
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        # Получаем данные компании и сессии
        company_data = await get_company(id=company_id)
        session_data = await get_session(session_id=session_id)
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        deposits = company_data.get('deposits', [])
        current_step = session_data.get('step', 0)
        
        if deposit_index < 0 or deposit_index >= len(deposits):
            return "❌ Ошибка: вклад не найден"
        
        deposit = deposits[deposit_index]
        can_withdraw_from = deposit.get("can_withdraw_from", 0)
        current_balance = deposit.get("current_balance", 0)
        initial_sum = deposit.get("initial_sum", 0)
        total_earned = deposit.get("total_earned", 0)
        income_per_turn = deposit.get("income_per_turn", 0)
        steps_total = deposit.get("steps_total", 0)
        steps_now = deposit.get("steps_now", 0)
        
        can_withdraw_in = can_withdraw_from - current_step
        steps_left = steps_total - steps_now
        
        # Определяем статус вклада
        if can_withdraw_in <= 0:
            status_icon = "🔓"
            status_text = "✅ Доступен для снятия"
        else:
            status_icon = "🔒"
            status_text = f"⏳ Заблокирован еще {can_withdraw_in} ход(ов)"
        
        # Рассчитываем доходность
        if initial_sum > 0:
            profit_percent = (total_earned / initial_sum) * 100
        else:
            profit_percent = 0
        
        text = f"""{status_icon} *Вклад #{deposit_index + 1}*

*Финансовая информация:*
💵 Начальная сумма: {initial_sum:,} 💰
💰 Текущий баланс: {current_balance:,} 💰
📈 Заработано: {total_earned:,} 💰 (+{profit_percent:.1f}%)
💸 Доход за ход: {income_per_turn:,} 💰

*Информация о сроках:*
⏱ Общий срок вклада: {steps_total} ход(ов)
⏳ Прошло ходов: {steps_now} / {steps_total}
🔄 Осталось ходов: {steps_left}

*Статус:*
{status_text}

_Вклад можно забрать через 3 хода после открытия, независимо от общего срока_""".replace(",", " ")
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        deposit_index = scene_data.get('viewing_deposit_index', 0)
        
        buttons = []
        
        # Получаем данные для проверки возможности снятия
        company_data = await get_company(id=company_id)
        session_data = await get_session(session_id=session_id)
        
        if isinstance(company_data, dict) and isinstance(session_data, dict):
            deposits = company_data.get('deposits', [])
            current_step = session_data.get('step', 0)
            
            if deposit_index >= 0 and deposit_index < len(deposits):
                deposit = deposits[deposit_index]
                can_withdraw_from = deposit.get("can_withdraw_from", 0)
                current_balance = deposit.get("current_balance", 0)
                
                # Кнопка забрать вклад (если доступно)
                if current_step >= can_withdraw_from:
                    buttons.append({
                        'text': f'💰 Забрать вклад ({current_balance:,} 💰)'.replace(",", " "),
                        'callback_data': callback_generator(
                            self.scene.__scene_name__,
                            'withdraw_deposit'
                        )
                    })
        
        # Кнопка возврата к списку вкладов
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(
                self.scene.__scene_name__,
                'back_to_main'
            )
        })
        
        self.row_width = 1
        return buttons
    
    @Page.on_callback('withdraw_deposit')
    async def withdraw_deposit_handler(self, callback: CallbackQuery, args: list):
        """Изъятие вклада"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        deposit_index = scene_data.get('viewing_deposit_index', 0)
        
        if not company_id:
            await callback.answer("❌ Ошибка: компания не найдена", show_alert=True)
            return
        
        # Получаем данные компании и сессии
        company_data = await get_company(id=company_id)
        session_data = await get_session(session_id=session_id)
        
        if isinstance(company_data, str):
            await callback.answer(f"❌ Ошибка: {company_data}", show_alert=True)
            return
        
        deposits = company_data.get('deposits', [])
        current_step = session_data.get('step', 0)
        
        if deposit_index < 0 or deposit_index >= len(deposits):
            await callback.answer("❌ Ошибка: вклад не найден", show_alert=True)
            return
        
        deposit = deposits[deposit_index]
        can_withdraw_from = deposit.get("can_withdraw_from", 0)
        current_balance = deposit.get("current_balance", 0)
        
        # Проверяем, можно ли забрать вклад
        if current_step < can_withdraw_from:
            can_withdraw_in = can_withdraw_from - current_step
            await callback.answer(
                f"❌ Вклад заблокирован!\n"
                f"Можно забрать через: {can_withdraw_in} ход(ов)",
                show_alert=True
            )
            return
        
        # Изымаем вклад
        result = await company_withdraw_deposit(
            company_id=company_id,
            deposit_index=deposit_index
        )
        
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
        elif isinstance(result, dict) and 'error' in result:
            await callback.answer(f"❌ Ошибка: {result['error']}", show_alert=True)
        else:
            # Успешное изъятие - возвращаемся к основному экрану
            scene_data['success_message'] = f'Вклад изъят! Получено: {current_balance:,} 💰'.replace(",", " ")
            scene_data['viewing_deposit_index'] = None
            await self.scene.set_data('scene', scene_data)
            
            await self.scene.update_page('bank-deposit-main')
            await callback.answer(f"✅ Вклад изъят: {current_balance:,} 💰".replace(",", " "), show_alert=True)
    
    @Page.on_callback('back_to_main')
    async def back_to_main_handler(self, callback: CallbackQuery, args: list):
        """Возврат к основному экрану вкладов"""
        scene_data = self.scene.get_data('scene')
        
        # Очищаем индекс просматриваемого вклада
        scene_data['viewing_deposit_index'] = None
        await self.scene.set_data('scene', scene_data)
        
        # Переходим на главную страницу вкладов
        await self.scene.update_page('bank-deposit-main')
        await callback.answer()
