from oms import Page
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_company, company_take_deposit, company_withdraw_deposit, get_session
from oms.utils import callback_generator
from global_modules.bank import get_deposit_conditions, calc_deposit, CAPITAL, check_max_deposit_steps
from global_modules.logs import Logger

bot_logger = Logger.get_logger("bot")


class BankDepositPage(Page):
    
    __page_name__ = "bank-deposit-page"
    
    async def content_worker(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        # Получаем данные компании
        company_data = await get_company(id=company_id)
        session_data = await get_session(session_id=session_id)
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        reputation = company_data.get('reputation', 0)
        deposits = company_data.get('deposits', [])
        balance = company_data.get('balance', 0)
        
        # Получаем состояние страницы
        deposit_state = scene_data.get('deposit_state', 'main')
        
        # Основной экран
        if deposit_state == 'main':
            return await self._main_screen(deposits, reputation, balance, session_data)
        
        # Экран просмотра конкретного вклада
        elif deposit_state == 'view_deposit':
            return await self._view_deposit_screen(scene_data, deposits, session_data)
        
        # Экран ввода суммы вклада
        elif deposit_state == 'input_amount':
            return await self._input_amount_screen(scene_data, balance, reputation)
        
        # Экран ввода срока вклада
        elif deposit_state == 'input_period':
            return await self._input_period_screen(scene_data, session_data, reputation)
        
        # Экран подтверждения вклада
        elif deposit_state == 'confirm':
            return await self._confirm_screen(scene_data, reputation)
        
        return "❌ Неизвестное состояние"
    
    async def _main_screen(self, deposits, reputation, balance, session_data):
        """Основной экран с информацией о вкладах"""
        scene_data = self.scene.get_data('scene')
        success_message = scene_data.get('success_message', '')
        
        current_step = session_data.get('step', 0)
        max_step = session_data.get('max_steps', 15)
        
        text = "🏦 *Вклады*\n\n"
        
        # Показываем успешное сообщение, если есть
        if success_message:
            text += f"✅ {success_message}\n\n"
            # Очищаем сообщение после показа
            scene_data['success_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        # Получаем условия вклада
        try:
            conditions = get_deposit_conditions(reputation)
            
            # Информация об условиях
            percent = conditions.percent * 100
            
            text += f"*Ваши условия:*\n"
            text += f"💰 Баланс: {balance:,} 💰\n".replace(",", " ")
            text += f"📈 Процентная ставка: {percent}% в ход\n"
            text += f"⭐ Репутация: {reputation}\n"
            text += f"⏱ Минимальный срок: 3 хода\n\n"
        except ValueError:
            text += "❌ *Вклады недоступны*\n"
            text += f"Минимальная репутация для вклада: 11\n"
            text += f"Ваша репутация: {reputation} ⭐\n\n"
        
        # Проверяем, можно ли сделать новый вклад
        can_make_deposit = (max_step - current_step) >= 3
        if not can_make_deposit:
            text += "⚠️ *Новые вклады недоступны*\n"
            text += f"До конца игры осталось меньше 3 ходов\n"
            text += f"(Текущий ход: {current_step}, до конца: {max_step - current_step})\n\n"
        
        # Информация о количестве активных вкладов
        if deposits and len(deposits) > 0:
            text += f"*Активные вклады:* {len(deposits)} шт.\n"
            text += "_Нажмите на кнопку вклада для подробной информации_\n"
        else:
            text += "_У вас нет активных вкладов_\n"
        
        return text
    
    async def _view_deposit_screen(self, scene_data, deposits, session_data):
        """Экран просмотра конкретного вклада"""
        deposit_index = scene_data.get('viewing_deposit_index', 0)
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
    
    async def _input_amount_screen(self, scene_data, balance, reputation):
        """Экран ввода суммы вклада"""
        error = scene_data.get('error_message', '')
        
        # Получаем лимиты из конфига
        min_deposit = CAPITAL.bank.contribution.min
        max_deposit = CAPITAL.bank.contribution.max
        
        text = f"""💰 *Открытие вклада*

*Шаг 1: Введите сумму вклада*

Ваш баланс: {balance:,} 💰
Минимум: {min_deposit:,} 💰
Максимум: {max_deposit:,} 💰

Введите сумму, которую хотите внести на вклад:""".replace(",", " ")
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def _input_period_screen(self, scene_data, session_data, reputation):
        """Экран ввода срока вклада"""
        deposit_amount = scene_data.get('deposit_amount', 0)
        error = scene_data.get('error_message', '')
        
        # Получаем текущий ход и максимум
        current_step = session_data.get('step', 0)
        max_step = session_data.get('max_steps', 15)
        max_period = max_step - current_step
        
        # Получаем процентную ставку
        conditions = get_deposit_conditions(reputation)
        percent = conditions.percent * 100
        
        text = f"""⏱ *Открытие вклада*

✅ Сумма вклада: {deposit_amount:,} 💰
📈 Процентная ставка: {percent}% в ход

*Шаг 2: Введите срок вклада*

Минимум: 3 хода (минимальный срок блокировки)
Максимум: {max_period} ход(ов)
(Текущий ход: {current_step}, до конца игры: {max_period})

Введите количество ходов:""".replace(",", " ")
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def _confirm_screen(self, scene_data, reputation):
        """Экран подтверждения открытия вклада"""
        deposit_amount = scene_data.get('deposit_amount', 0)
        deposit_period = scene_data.get('deposit_period', 0)
        
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
        
        text = f"""🏦 *Подтверждение вклада*

*Параметры вклада:*
💵 Сумма вклада: {deposit_amount:,} 💰
⏱ Срок: {deposit_period} ход(ов)

*Условия:*
📈 Процентная ставка: {percent}% в ход
🔒 Минимальный срок: 3 хода
(Забрать вклад можно будет через 3 хода)

*Доход:*
📈 Доход за ход: {income_per_turn:,} 💰
✅ Общий доход: {total_income:,} 💰
💰 Итоговая сумма: {final_sum:,} 💰

Подтвердите открытие вклада:""".replace(",", " ")
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        deposit_state = scene_data.get('deposit_state', 'main')
        
        buttons = []
        
        # Кнопки для основного экрана
        if deposit_state == 'main':
            # Получаем данные компании и сессии
            company_data = await get_company(id=company_id)
            session_data = await get_session(session_id=session_id)
            
            if isinstance(company_data, dict) and isinstance(session_data, dict):
                reputation = company_data.get('reputation', 0)
                deposits = company_data.get('deposits', [])
                current_step = session_data.get('step', 0)
                max_step = session_data.get('max_steps', 15)
                
                # Проверяем возможность сделать вклад
                can_make_deposit = (max_step - current_step) >= 3
                
                if can_make_deposit:
                    try:
                        get_deposit_conditions(reputation)
                        buttons.append({
                            'text': '💰 Открыть вклад',
                            'callback_data': callback_generator(
                                self.scene.__scene_name__,
                                'open_deposit'
                            )
                        })
                    except ValueError:
                        pass
                
                # Кнопки для вкладов - теперь все кликабельны
                if deposits and len(deposits) > 0:
                    bot_logger.info(f"Processing {len(deposits)} deposits. Current step: {current_step}")
                    for i, deposit in enumerate(deposits):
                        can_withdraw_from = deposit.get("can_withdraw_from", 0)
                        current_balance = deposit.get("current_balance", 0)
                        
                        bot_logger.info(f"Deposit #{i+1}: can_withdraw_from={can_withdraw_from}, current_step={current_step}, can_withdraw={current_step >= can_withdraw_from}")
                        
                        # Можно забрать, если текущий ход >= can_withdraw_from
                        if current_step >= can_withdraw_from:
                            buttons.append({
                                'text': f'🔓 Вклад #{i+1} ({current_balance:,} 💰)'.replace(",", " "),
                                'callback_data': callback_generator(
                                    self.scene.__scene_name__,
                                    'view_deposit',
                                    str(i)
                                )
                            })
                        else:
                            # Показываем когда можно будет забрать
                            can_withdraw_in = can_withdraw_from - current_step
                            buttons.append({
                                'text': f'🔒 Вклад #{i+1} (через {can_withdraw_in} ход(ов))'.replace(",", " "),
                                'callback_data': callback_generator(
                                    self.scene.__scene_name__,
                                    'view_deposit',
                                    str(i)
                                )
                            })
                        
                buttons.append({
                    'text': f'⬅️ Назад',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'back_to_bank'
                    )
                })
        
        # Кнопки для экрана просмотра вклада
        elif deposit_state == 'view_deposit':
            company_data = await get_company(id=company_id)
            session_data = await get_session(session_id=session_id)
            
            if isinstance(company_data, dict) and isinstance(session_data, dict):
                deposits = company_data.get('deposits', [])
                deposit_index = scene_data.get('viewing_deposit_index', 0)
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
                                'withdraw_deposit',
                                str(deposit_index)
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
                
        
        # Кнопки для экранов ввода - добавляем кнопку отмены
        elif deposit_state in ['input_amount', 'input_period']:
            buttons = [
                {
                    'text': '❌ Отменить',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'cancel_deposit'
                    )
                }
            ]
        
        # Кнопки для экрана подтверждения
        elif deposit_state == 'confirm':
            buttons = [
                {
                    'text': '✅ Да, открыть вклад',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'confirm_deposit'
                    )
                },
                {
                    'text': '❌ Нет, отменить',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'cancel_deposit'
                    )
                }
            ]
        
        self.row_width = 1
        return buttons
    
    @Page.on_callback('open_deposit')
    async def open_deposit_handler(self, callback: CallbackQuery, args: list):
        """Начало процесса открытия вклада - запрос суммы"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        # Проверяем репутацию и время до конца игры
        company_data = await get_company(id=company_id)
        session_data = await get_session(session_id=session_id)
        
        if isinstance(company_data, dict) and isinstance(session_data, dict):
            reputation = company_data.get('reputation', 0)
            current_step = session_data.get('step', 0)
            max_step = session_data.get('max_steps', 15)
            
            # Проверяем минимальное время до конца игры
            if (max_step - current_step) < 3:
                await callback.answer(
                    "❌ Вклады недоступны!\n"
                    "До конца игры осталось меньше 3 ходов.",
                    show_alert=True
                )
                return
            
            # Проверяем репутацию
            try:
                get_deposit_conditions(reputation)
            except ValueError:
                await callback.answer(
                    "❌ Недостаточная репутация для открытия вклада!\n"
                    "Минимальная репутация: 11 ⭐",
                    show_alert=True
                )
                return
        
        # Устанавливаем состояние ожидания ввода суммы
        scene_data['deposit_state'] = 'input_amount'
        scene_data['error_message'] = ''  # Очищаем ошибки
        await self.scene.set_data('scene', scene_data)
        
        # Обновляем сообщение для показа инструкции
        await self.scene.update_message()
        await callback.answer("💬 Введите сумму вклада")
    
    @Page.on_callback('view_deposit')
    async def view_deposit_handler(self, callback: CallbackQuery, args: list):
        """Просмотр информации о конкретном вкладе"""
        # Проверяем структуру args
        if args and args[0] == 'view_deposit':
            if len(args) < 2:
                await callback.answer("❌ Ошибка: не указан индекс вклада", show_alert=True)
                return
            deposit_index = int(args[1])
        elif args and len(args) > 0:
            deposit_index = int(args[0])
        else:
            await callback.answer("❌ Ошибка: не указан индекс вклада", show_alert=True)
            return
        
        scene_data = self.scene.get_data('scene')
        
        # Устанавливаем состояние просмотра вклада
        scene_data['deposit_state'] = 'view_deposit'
        scene_data['viewing_deposit_index'] = deposit_index
        await self.scene.set_data('scene', scene_data)
        
        # Обновляем сообщение для показа информации о вкладе
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('back_to_main')
    async def back_to_main_handler(self, callback: CallbackQuery, args: list):
        """Возврат к основному экрану вкладов"""
        scene_data = self.scene.get_data('scene')
        
        # Возвращаемся на основной экран
        scene_data['deposit_state'] = 'main'
        scene_data['viewing_deposit_index'] = None
        await self.scene.set_data('scene', scene_data)
        
        # Обновляем сообщение
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('withdraw_deposit')
    async def withdraw_deposit_handler(self, callback: CallbackQuery, args: list):
        """Изъятие вклада"""
        # Проверяем структуру args
        if args and args[0] == 'withdraw_deposit':
            if len(args) < 2:
                await callback.answer("❌ Ошибка: не указан индекс вклада", show_alert=True)
                return
            deposit_index = int(args[1])
        elif args and len(args) > 0:
            deposit_index = int(args[0])
        else:
            await callback.answer("❌ Ошибка: не указан индекс вклада", show_alert=True)
            return
        
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
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
            company_id=str(company_id),
            deposit_index=deposit_index
        )
        
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
        elif isinstance(result, dict) and 'error' in result:
            await callback.answer(f"❌ Ошибка: {result['error']}", show_alert=True)
        else:
            # Успешное изъятие - возвращаемся к основному экрану
            scene_data['success_message'] = f'Вклад изъят! Получено: {current_balance:,} 💰'.replace(",", " ")
            scene_data['deposit_state'] = 'main'
            scene_data['viewing_deposit_index'] = None
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            await callback.answer(f"✅ Вклад изъят: {current_balance:,} 💰".replace(",", " "), show_alert=True)
    
    @Page.on_callback('confirm_deposit')
    async def confirm_deposit_handler(self, callback: CallbackQuery, args: list):
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
            company_id=str(company_id),
            amount=deposit_amount,
            period=deposit_period
        )
        
        # Проверяем результат
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
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
            
            # Сбрасываем состояние и возвращаемся к основному экрану
            scene_data['deposit_state'] = 'main'
            scene_data['deposit_amount'] = 0
            scene_data['deposit_period'] = 0
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        else:
            # Успешное открытие вклада
            scene_data['deposit_state'] = 'main'
            scene_data['deposit_amount'] = 0
            scene_data['deposit_period'] = 0
            scene_data['success_message'] = f'Вклад открыт! Внесено: {deposit_amount:,} 💰 на {deposit_period} ход(ов)'.replace(",", " ")
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
            await callback.answer(
                f"✅ Вклад открыт!\n"
                f"Сумма: {deposit_amount:,} 💰\n"
                f"Срок: {deposit_period} ход(ов)".replace(",", " "),
                show_alert=True
            )
    
    @Page.on_callback('cancel_deposit')
    async def cancel_deposit_handler(self, callback: CallbackQuery, args: list):
        """Отмена открытия вклада"""
        scene_data = self.scene.get_data('scene')
        scene_data['deposit_state'] = 'main'
        scene_data['deposit_amount'] = 0
        scene_data['deposit_period'] = 0
        scene_data['error_message'] = ''  # Очищаем ошибки
        await self.scene.set_data('scene', scene_data)
        
        await callback.answer("❌ Операция отменена")
        await self.scene.update_message()
    
    
    @Page.on_callback('back_to_bank')
    async def back_to_bank_handler(self, callback: CallbackQuery, args: list):
        scene_data = self.scene.get_data('scene')
        scene_data['deposit_state'] = 'main'
        scene_data['deposit_amount'] = 0
        scene_data['deposit_period'] = 0
        scene_data['error_message'] = ''  # Очищаем ошибки
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_page('bank-menu')
    
    @Page.on_text('int')
    async def handle_input(self, message: Message, value: int):
        """Обработка ввода чисел (сумма или срок)"""
        scene_data = self.scene.get_data('scene')
        deposit_state = scene_data.get('deposit_state', 'main')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        # Ввод суммы вклада
        if deposit_state == 'input_amount':
            # Очищаем предыдущую ошибку
            scene_data['error_message'] = ''
            
            # Получаем лимиты из конфига
            min_deposit = CAPITAL.bank.contribution.min
            max_deposit = CAPITAL.bank.contribution.max
            
            # Получаем баланс
            company_data = await get_company(id=company_id)
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
            scene_data['deposit_state'] = 'input_period'
            await self.scene.set_data('scene', scene_data)
            
            # Обновляем сообщение для показа следующего шага
            await self.scene.update_message()
        
        # Ввод срока вклада
        elif deposit_state == 'input_period':
            # Очищаем предыдущую ошибку
            scene_data['error_message'] = ''
            
            # Получаем данные сессии для проверки срока
            session_data = await get_session(session_id=session_id)
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
            scene_data['deposit_state'] = 'confirm'
            await self.scene.set_data('scene', scene_data)
            
            # Обновляем сообщение для показа экрана подтверждения
            await self.scene.update_message()
