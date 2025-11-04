from oms import Page
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_company, company_take_credit, get_session
from oms.utils import callback_generator
from global_modules.bank import get_credit_conditions, calc_credit, CAPITAL


class BankCreditTakePeriod(Page):
    """Страница ввода срока кредита"""
    
    __page_name__ = "bank-credit-take-period"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('session')
        error = scene_data.get('error_message', '')
        
        # Получаем данные сессии
        session_data = await get_session(session_id=session_id)
        
        # Получаем текущий ход и максимум
        current_step = session_data.get('step', 0)
        max_step = session_data.get('max_step', 15)
        max_period = max_step - current_step
        
        text = self.content.format(
            max_period=max_period,
            current_step=current_step
        )
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        self.row_width = 2
        return [
            {
                'text': '❌ Отменить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'cancel'
                )
            }
        ]
    
    @Page.on_callback('cancel')
    async def cancel_handler(self, callback: CallbackQuery, args: list):
        """Отмена взятия кредита"""
        scene_data = self.scene.get_data('scene')
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-credit-main')
        await callback.answer("❌ Операция отменена")
    
    @Page.on_text('int')
    async def handle_period_input(self, message: Message, value: int):
        """Обработка ввода срока кредита"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        # Очищаем предыдущую ошибку
        scene_data['error_message'] = ''
        
        if value < 2:
            scene_data['error_message'] = 'Срок должен быть не менее 2 хода'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Получаем данные для проверки максимального срока
        session_data = await get_session(session_id=session_id)
        
        current_step = session_data.get('step')
        max_step = session_data.get('max_steps')
        max_period = max_step - current_step
        
        if value > max_period:
            scene_data['error_message'] = f'Срок не может превышать {max_period} ход(ов)! (Текущий ход: {current_step}, до конца игры: {max_period})'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Сохраняем срок и переходим к вводу суммы
        scene_data['credit_period'] = value
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-credit-take-amount')


class BankCreditTakeAmount(Page):
    """Страница ввода суммы кредита"""
    
    __page_name__ = "bank-credit-take-amount"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        credit_period = scene_data.get('credit_period', 0)
        error = scene_data.get('error_message', '')
        
        # Получаем лимиты из конфига
        min_credit = CAPITAL.bank.credit.min
        max_credit = CAPITAL.bank.credit.max
        
        text = self.content.format(
            credit_period=credit_period,
            min_credit=f"{min_credit:,}".replace(",", " "),
            max_credit=f"{max_credit:,}".replace(",", " ")
        )
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        self.row_width = 2
        return [
            {
                'text': '❌ Отменить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'cancel'
                )
            }
        ]
    
    @Page.on_callback('cancel')
    async def cancel_handler(self, callback: CallbackQuery, args: list):
        """Отмена взятия кредита"""
        scene_data = self.scene.get_data('scene')
        scene_data['credit_period'] = 0
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-credit-main')
        await callback.answer("❌ Операция отменена")
    
    @Page.on_text('int')
    async def handle_amount_input(self, message: Message, value: int):
        """Обработка ввода суммы кредита"""
        scene_data = self.scene.get_data('scene')
        
        # Очищаем предыдущую ошибку
        scene_data['error_message'] = ''
        
        # Получаем лимиты из конфига
        min_credit = CAPITAL.bank.credit.min
        max_credit = CAPITAL.bank.credit.max
        
        if value < min_credit:
            scene_data['error_message'] = f'Минимальная сумма кредита: {min_credit:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        if value > max_credit:
            scene_data['error_message'] = f'Максимальная сумма кредита: {max_credit:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Сохраняем сумму и переходим к подтверждению
        scene_data['credit_amount'] = value
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-credit-take-confirm')


class BankCreditTakeConfirm(Page):
    """Страница подтверждения взятия кредита"""
    
    __page_name__ = "bank-credit-take-confirm"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        credit_period = scene_data.get('credit_period', 0)
        credit_amount = scene_data.get('credit_amount', 0)
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        reputation = company_data.get('reputation', 0)
        
        # Получаем условия кредитования
        conditions = get_credit_conditions(reputation)
        
        # Расчитываем параметры кредита
        total, pay_per_turn, extra = calc_credit(
            S=credit_amount,
            free=conditions.without_interest,
            r_percent=conditions.percent,
            T=credit_period
        )
        
        percent = conditions.percent * 100
        
        text = self.content.format(
            credit_amount=f"{credit_amount:,}".replace(",", " "),
            credit_period=credit_period,
            percent=percent,
            without_interest=conditions.without_interest,
            extra=extra,
            total=f"{total:,}".replace(",", " "),
            pay_per_turn=f"{pay_per_turn:,}".replace(",", " ")
        )
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        self.row_width = 1
        return [
            {
                'text': '✅ Да, взять кредит',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'confirm'
                )
            },
            {
                'text': '❌ Нет, отменить',
                'callback_data': callback_generator(
                    self.scene.__scene_name__,
                    'cancel'
                )
            }
        ]
    
    @Page.on_callback('confirm')
    async def confirm_handler(self, callback: CallbackQuery, args: list):
        """Подтверждение взятия кредита"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        credit_amount = scene_data.get('credit_amount', 0)
        credit_period = scene_data.get('credit_period', 0)
        
        if not company_id:
            await callback.answer("❌ Ошибка: компания не найдена", show_alert=True)
            return
        
        # Берем кредит
        result = await company_take_credit(
            company_id=company_id,
            amount=credit_amount,
            period=credit_period
        )
        
        # Проверяем результат
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
            # Возвращаемся к главной странице
            scene_data['credit_amount'] = 0
            scene_data['credit_period'] = 0
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_page('bank-credit-main')
        elif isinstance(result, dict) and 'error' in result:
            # Обрабатываем ошибку из API
            error_msg = result['error']
            if 'reputation' in error_msg.lower():
                await callback.answer(
                    "❌ Недостаточная репутация для взятия кредита!\n"
                    "Минимальная репутация: 11 ⭐",
                    show_alert=True
                )
            else:
                await callback.answer(f"❌ Ошибка: {error_msg}", show_alert=True)
            
            # Возвращаемся к главной странице
            scene_data['credit_amount'] = 0
            scene_data['credit_period'] = 0
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_page('bank-credit-main')
        else:
            await callback.answer(
                f"✅ Кредит оформлен!\n"
                f"Сумма: {credit_amount:,} 💰\n"
                f"Срок: {credit_period} ход(ов)".replace(",", " "),
                show_alert=True
            )
            # Возвращаемся к главной странице с сообщением об успехе
            scene_data['credit_amount'] = 0
            scene_data['credit_period'] = 0
            scene_data['success_message'] = f'Кредит оформлен: {credit_amount:,} 💰 на {credit_period} ход(ов)'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_page('bank-credit-main')
    
    @Page.on_callback('cancel')
    async def cancel_handler(self, callback: CallbackQuery, args: list):
        """Отмена взятия кредита"""
        scene_data = self.scene.get_data('scene')
        scene_data['credit_amount'] = 0
        scene_data['credit_period'] = 0
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-credit-main')
        await callback.answer("❌ Операция отменена")
