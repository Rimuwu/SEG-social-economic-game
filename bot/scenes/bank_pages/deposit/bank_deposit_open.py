from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_company, company_take_deposit, get_session
from oms.utils import callback_generator
from global_modules.bank import get_deposit_conditions, calc_deposit, CAPITAL

Page = OneUserPage

class BankDepositOpenAmount(Page):
    """Страница ввода суммы вклада"""
    
    __page_name__ = "bank-deposit-open-amount"
    __for_blocked_pages__ = ["bank-menu"]
    async def data_preparate(self):
        """Кэшируем данные компании для страницы"""
        company_id = self.scene.get_key("scene", "company_id")
        company_data = await get_company(id=company_id)
        await self.scene.update_key(self.__page_name__, "company_data", company_data)
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        error = scene_data.get('error_message', '')
        
        # Получаем данные компании из кэша
        company_data = self.scene.get_key(self.__page_name__, "company_data")
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        balance = company_data.get('balance', 0)
        
        # Получаем лимиты из конфига
        min_deposit = CAPITAL.bank.contribution.min
        max_deposit = CAPITAL.bank.contribution.max
        
        # Форматируем числа
        balance_formatted = f"{balance:,}".replace(",", " ")
        min_deposit_formatted = f"{min_deposit:,}".replace(",", " ")
        max_deposit_formatted = f"{max_deposit:,}".replace(",", " ")
        
        # Формируем текст из шаблона
        text = self.content.format(
            balance=balance_formatted,
            min_deposit=min_deposit_formatted,
            max_deposit=max_deposit_formatted
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
        """Отмена открытия вклада"""
        scene_data = self.scene.get_data('scene')
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-deposit-main')
        await callback.answer("❌ Операция отменена")
    
    @Page.on_text('int')
    async def handle_amount_input(self, message: Message, value: int):
        """Обработка ввода суммы вклада"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        
        # Очищаем предыдущую ошибку
        scene_data['error_message'] = ''
        
        # Получаем лимиты из конфига
        min_deposit = CAPITAL.bank.contribution.min
        max_deposit = CAPITAL.bank.contribution.max
        
        # Получаем баланс из кэша
        company_data = self.scene.get_key(self.__page_name__, "company_data")
        if isinstance(company_data, str):
            scene_data['error_message'] = f'Ошибка: {company_data}'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        balance = company_data.get('balance', 0)
        
        if value < min_deposit:
            scene_data['error_message'] = f'Минимальная сумма вклада: {min_deposit:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        if value > max_deposit:
            scene_data['error_message'] = f'Максимальная сумма вклада: {max_deposit:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        if value > balance:
            scene_data['error_message'] = f'Недостаточно средств! Ваш баланс: {balance:,} 💰'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Сохраняем сумму и переходим к вводу срока
        scene_data['deposit_amount'] = value
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-deposit-open-period')


class BankDepositOpenPeriod(Page):
    """Страница ввода срока вклада"""
    
    __page_name__ = "bank-deposit-open-period"
    async def data_preparate(self):
        """Кэшируем данные компании и сессии для страницы"""
        company_id = self.scene.get_key("scene", "company_id")
        session_id = self.scene.get_key("scene", "session")
        company_data = await get_company(id=company_id)
        session_data = await get_session(session_id=session_id)
        await self.scene.update_key(self.__page_name__, "company_data", company_data)
        await self.scene.update_key(self.__page_name__, "session_data", session_data)
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        deposit_amount = scene_data.get('deposit_amount', 0)
        error = scene_data.get('error_message', '')
        
        # Получаем данные компании и сессии из кэша
        company_data = self.scene.get_key(self.__page_name__, "company_data")
        session_data = self.scene.get_key(self.__page_name__, "session_data")
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        reputation = company_data.get('reputation', 0)
        
        # Получаем текущий ход и максимум
        current_step = session_data.get('step', 0)
        max_step = session_data.get('max_steps', 15)
        max_period = max_step - current_step
        
        # Получаем процентную ставку
        conditions = get_deposit_conditions(reputation)
        percent = conditions.percent * 100
        
        # Форматируем числа
        deposit_amount_formatted = f"{deposit_amount:,}".replace(",", " ")
        
        # Формируем текст из шаблона
        text = self.content.format(
            deposit_amount=deposit_amount_formatted,
            percent=percent,
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
        """Отмена открытия вклада"""
        scene_data = self.scene.get_data('scene')
        scene_data['deposit_amount'] = 0
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-deposit-main')
        await callback.answer("❌ Операция отменена")
    
    @Page.on_text('int')
    async def handle_period_input(self, message: Message, value: int):
        """Обработка ввода срока вклада"""
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('session')
        
        # Очищаем предыдущую ошибку
        scene_data['error_message'] = ''
        
        # Получаем данные сессии для проверки срока из кэша
        session_data = self.scene.get_key(self.__page_name__, "session_data")
        if isinstance(session_data, str):
            scene_data['error_message'] = f'Ошибка: {session_data}'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        current_step = session_data.get('step', 0)
        max_step = session_data.get('max_steps', 15)
        max_period = max_step - current_step
        
        if value < 3:
            scene_data['error_message'] = 'Минимальный срок вклада: 3 хода'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        if value > max_period:
            scene_data['error_message'] = f'Срок не может превышать {max_period} ход(ов)! (Текущий ход: {current_step}, до конца игры: {max_period})'
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            return
        
        # Сохраняем срок и переходим к подтверждению
        scene_data['deposit_period'] = value
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-deposit-open-confirm')


class BankDepositOpenConfirm(Page):
    """Страница подтверждения открытия вклада"""
    
    __page_name__ = "bank-deposit-open-confirm"
    async def data_preparate(self):
        """Кэшируем данные компании для страницы"""
        company_id = self.scene.get_key("scene", "company_id")
        company_data = await get_company(id=company_id)
        await self.scene.update_key(self.__page_name__, "company_data", company_data)
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        deposit_amount = scene_data.get('deposit_amount', 0)
        deposit_period = scene_data.get('deposit_period', 0)
        
        # Получаем данные компании из кэша
        company_data = self.scene.get_key(self.__page_name__, "company_data")
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        reputation = company_data.get('reputation', 0)
        
        # Получаем условия вклада
        conditions = get_deposit_conditions(reputation)
        
        # Рассчитываем параметры вклада
        income_per_turn, total_income = calc_deposit(
            S=deposit_amount,
            r_percent=conditions.percent,
            T=deposit_period
        )
        
        percent = conditions.percent * 100
        final_sum = deposit_amount + total_income
        
        # Форматируем числа
        deposit_amount_formatted = f"{deposit_amount:,}".replace(",", " ")
        income_per_turn_formatted = f"{income_per_turn:,}".replace(",", " ")
        total_income_formatted = f"{total_income:,}".replace(",", " ")
        final_sum_formatted = f"{final_sum:,}".replace(",", " ")
        
        # Формируем текст из шаблона
        text = self.content.format(
            deposit_amount=deposit_amount_formatted,
            deposit_period=deposit_period,
            percent=percent,
            income_per_turn=income_per_turn_formatted,
            total_income=total_income_formatted,
            final_sum=final_sum_formatted
        )
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        self.row_width = 1
        return [
            {
                'text': '✅ Да, открыть вклад',
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
        """Подтверждение открытия вклада"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        deposit_amount = scene_data.get('deposit_amount', 0)
        deposit_period = scene_data.get('deposit_period', 0)
        
        if not company_id:
            await callback.answer("❌ Ошибка: компания не найдена", show_alert=True)
            return
        
        # Открываем вклад
        result = await company_take_deposit(
            company_id=company_id,
            amount=deposit_amount,
            period=deposit_period
        )
        
        # Проверяем результат
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
            # Возвращаемся к главной странице
            scene_data['deposit_amount'] = 0
            scene_data['deposit_period'] = 0
            await self.scene.set_data('scene', scene_data)
            # Инвалидируем кэш компании на главной странице вкладов, чтобы при открытии она обновилась
            await self.scene.update_key('bank-deposit-main', 'company_data', None)
            await self.scene.update_key('bank-deposit-main', 'session_data', None)
            await self.scene.update_page('bank-deposit-main')
        elif isinstance(result, dict) and 'error' in result:
            # Обрабатываем ошибку из API
            error_msg = result['error']
            if 'reputation' in error_msg.lower():
                await callback.answer(
                    "❌ Недостаточная репутация для открытия вклада!\n"
                    "Минимальная репутация: 11 ⭐",
                    show_alert=True
                )
            elif 'balance' in error_msg.lower() or 'insufficient' in error_msg.lower():
                await callback.answer(
                    "❌ Недостаточно средств на балансе!",
                    show_alert=True
                )
            else:
                await callback.answer(f"❌ Ошибка: {error_msg}", show_alert=True)
            
            # Возвращаемся к главной странице
            scene_data['deposit_amount'] = 0
            scene_data['deposit_period'] = 0
            await self.scene.set_data('scene', scene_data)
            # Инвалидируем кэш главной страницы вкладов
            await self.scene.update_key('bank-deposit-main', 'company_data', None)
            await self.scene.update_key('bank-deposit-main', 'session_data', None)
            await self.scene.update_page('bank-deposit-main')
        else:
            # Успешное открытие вклада
            scene_data['deposit_amount'] = 0
            scene_data['deposit_period'] = 0
            scene_data['success_message'] = f'Вклад открыт! Внесено: {deposit_amount:,} 💰 на {deposit_period} ход(ов)'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            
            # Инвалидируем кэш главной страницы вкладов
            await self.scene.update_key('bank-deposit-main', 'company_data', None)
            await self.scene.update_key('bank-deposit-main', 'session_data', None)
            await self.scene.update_page('bank-deposit-main')
            await callback.answer(
                f"✅ Вклад открыт!\n"
                f"Сумма: {deposit_amount:,} 💰\n"
                f"Срок: {deposit_period} ход(ов)".replace(",", " "),
                show_alert=True
            )
    
    @Page.on_callback('cancel')
    async def cancel_handler(self, callback: CallbackQuery, args: list):
        """Отмена открытия вклада"""
        scene_data = self.scene.get_data('scene')
        scene_data['deposit_amount'] = 0
        scene_data['deposit_period'] = 0
        scene_data['error_message'] = ''
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_page('bank-deposit-main')
        await callback.answer("❌ Операция отменена")
