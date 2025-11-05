from oms import Page
from aiogram.types import CallbackQuery, Message
from modules.ws_client import get_company, company_take_credit, company_pay_credit, get_session
from oms.utils import callback_generator
from global_modules.bank import get_credit_conditions, calc_credit, CAPITAL
from global_modules.load_config import ALL_CONFIGS

class BankCreditPage(Page):
    
    __page_name__ = "bank-credit-page"
    
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
        credits = company_data.get('credits', [])
        
        # Получаем состояние страницы
        credit_state = scene_data.get('credit_state', 'main')
        
        # Основной экран
        if credit_state == 'main':
            return await self._main_screen(credits, reputation)
        
        # Экран ввода срока кредита
        elif credit_state == 'input_period':
            return await self._input_period_screen(session_data)
        
        # Экран ввода суммы кредита
        elif credit_state == 'input_amount':
            return await self._input_amount_screen(scene_data)
        
        # Экран подтверждения кредита
        elif credit_state == 'confirm':
            return await self._confirm_screen(scene_data, reputation)
        
        # Экран ввода суммы оплаты кредита
        elif credit_state == 'pay_amount':
            return await self._pay_amount_screen(scene_data, company_data)
        
        return "❌ Неизвестное состояние"
    
    async def _main_screen(self, credits, reputation):
        """Основной экран с информацией о кредитах"""
        scene_data = self.scene.get_data('scene')
        success_message = scene_data.get('success_message', '')
        
        text = "💳 *Кредиты*\n\n"
        
        # Показываем успешное сообщение, если есть
        if success_message:
            text += f"✅ {success_message}\n\n"
            # Очищаем сообщение после показа
            scene_data['success_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        # Получаем условия кредитования
        try:
            conditions = get_credit_conditions(reputation)
            
            # Информация об условиях
            percent = conditions.percent * 100
            without_interest = conditions.without_interest
            max_credits = ALL_CONFIGS['settings'].max_credits_per_company
            
            text += f"*Ваши условия:*\n"
            text += f"Процентная ставка: {percent}%\n"
            text += f"Льготный период: {without_interest} ход(ов)\n"
            text += f"Репутация: {reputation} ⭐\n"
            text += f"Лимит кредитов: {len(credits)}/{max_credits}\n\n"
        except ValueError:
            text += "❌ *Кредиты недоступны*\n"
            text += f"Минимальная репутация для кредита: 11\n"
            text += f"Ваша репутация: {reputation} ⭐\n\n"
        
        # Активные кредиты
        if credits and len(credits) > 0:
            text += "*Активные кредиты:*\n\n"
            for i, credit in enumerate(credits, 1):
                total = credit.get("total_to_pay", 0)
                paid = credit.get("paid", 0)
                need_pay = credit.get("need_pay", 0)
                steps_total = credit.get("steps_total", 0)
                steps_now = credit.get("steps_now", 0)
                
                remaining = total - paid
                steps_left = steps_total - steps_now
                
                text += f"*Кредит #{i}*\n"
                text += f"Осталось выплатить: {remaining:,} 💰 (из {total:,})\n".replace(",", " ")
                text += f"Текущий платеж: {need_pay:,} 💰\n".replace(",", " ")
                text += f"Ходов до закрытия: {max(0, steps_left)}/{steps_total}\n"
                
                if need_pay > 0:
                    text += "⚠️ *Требуется оплата!*\n"
                
                text += "\n"
        else:
            text += "_У вас нет активных кредитов_\n"
        
        return text

    async def _input_period_screen(self, session_data):
        """Экран ввода срока кредита"""
        # Получаем текущий ход и максимум
        current_step = session_data.get('step', 0)
        max_step = session_data.get('max_step', 15)
        max_period = max_step - current_step
        
        scene_data = self.scene.get_data('scene')
        error = scene_data.get('error_message', '')
        
        text = f"""⏱ *Взятие кредита*

*Шаг 1: Введите срок кредита*

На какое количество ходов хотите взять кредит?
Минимум: 2 ход
Максимум: {max_period} ход(ов)
(Текущий ход: {current_step}, до конца игры: {max_period})"""
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def _input_amount_screen(self, scene_data):
        """Экран ввода суммы кредита"""
        credit_period = scene_data.get('credit_period', 0)
        error = scene_data.get('error_message', '')
        
        # Получаем лимиты из конфига
        min_credit = CAPITAL.bank.credit.min
        max_credit = CAPITAL.bank.credit.max
        
        text = f"""💰 *Взятие кредита*

✅ Срок: {credit_period} ход(ов)

*Шаг 2: Введите сумму кредита*

Минимум: {min_credit:,} 💰
Максимум: {max_credit:,} 💰""".replace(",", " ")
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def _pay_amount_screen(self, scene_data, company_data):
        """Экран ввода суммы оплаты кредита"""
        pay_credit_index = scene_data.get('pay_credit_index', 0)
        error = scene_data.get('error_message', '')
        credits = company_data.get('credits', [])
        balance = company_data.get('balance', 0)
        
        if pay_credit_index >= len(credits):
            return "❌ Ошибка: кредит не найден"
        
        credit = credits[pay_credit_index]
        total = credit.get("total_to_pay", 0)
        paid = credit.get("paid", 0)
        need_pay = credit.get("need_pay", 0)
        remaining = total - paid
        
        text = f"""💸 *Оплата кредита #{pay_credit_index + 1}*

*Информация о кредите:*
Осталось выплатить: {remaining:,} 💰
Текущий платеж: {need_pay:,} 💰
Ваш баланс: {balance:,} 💰

*Введите сумму для оплаты:*

Минимум: {need_pay:,} 💰 (текущий платеж)
Максимум: {remaining:,} 💰 (весь остаток)""".replace(",", " ")
        
        if error:
            text += f"\n\n❌ {error}"
        
        return text
    
    async def _confirm_screen(self, scene_data, reputation):
        """Экран подтверждения взятия кредита"""
        credit_period = scene_data.get('credit_period', 0)
        credit_amount = scene_data.get('credit_amount', 0)
        
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
        
        text = f"""💳 *Подтверждение кредита*

*Параметры кредита:*
Сумма: {credit_amount:,} 💰
Срок: {credit_period} ход(ов)

*Условия:*
Процентная ставка: {percent}%
Льготный период: {conditions.without_interest} ход(ов)
Ходов с процентами: {extra}

*К оплате:*
Всего к возврату: {total:,} 💰
Платеж за ход: {pay_per_turn:,} 💰

Подтвердите взятие кредита:""".replace(",", " ")
        
        return text
    
    async def buttons_worker(self):
        """Генерация кнопок"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        credit_state = scene_data.get('credit_state', 'main')
        
        buttons = []
        
        # Кнопки для основного экрана
        if credit_state == 'main':
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
        
        # Кнопки для экранов ввода - добавляем кнопку отмены
        elif credit_state in ['input_period', 'input_amount', 'pay_amount']:
            self.row_width = 2
            buttons = [
                {
                    'text': '❌ Отменить',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'cancel_credit'
                    )
                }
            ]
        
        # Кнопки для экрана подтверждения
        elif credit_state == 'confirm':
            self.row_width = 1
            buttons = [
                {
                    'text': '✅ Да, взять кредит',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'confirm_credit'
                    )
                },
                {
                    'text': '❌ Нет, отменить',
                    'callback_data': callback_generator(
                        self.scene.__scene_name__,
                        'cancel_credit'
                    )
                }
            ]
        return buttons
    
    @Page.on_callback('take_credit')
    async def take_credit_handler(self, callback: CallbackQuery, args: list):
        """Начало процесса взятия кредита - запрос срока"""
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
        
        # Устанавливаем состояние ожидания ввода срока
        scene_data['credit_state'] = 'input_period'
        scene_data['error_message'] = ''  # Очищаем ошибки
        await self.scene.set_data('scene', scene_data)
        
        # Обновляем сообщение для показа инструкции
        await self.scene.update_message()
        await callback.answer("💬 Введите срок кредита в сообщении")
    
    @Page.on_callback('pay_credit')
    async def pay_credit_handler(self, callback: CallbackQuery, args: list):
        """Начало процесса оплаты кредита - запрос суммы"""
        # Проверяем структуру args - если первый элемент 'pay_credit', берем второй
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
        
        # Сохраняем индекс кредита и переходим к вводу суммы
        scene_data['pay_credit_index'] = credit_index
        scene_data['credit_state'] = 'pay_amount'
        scene_data['error_message'] = ''  # Очищаем ошибки
        await self.scene.set_data('scene', scene_data)
        
        # Обновляем сообщение для показа экрана ввода суммы
        await self.scene.update_message()
        await callback.answer("💬 Введите сумму для оплаты")
    
    @Page.on_callback('confirm_credit')
    async def confirm_credit_handler(self, callback: CallbackQuery, args: list):
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
            company_id=str(company_id),
            amount=credit_amount,
            period=credit_period
        )
        
        # Проверяем результат
        if isinstance(result, str):
            await callback.answer(f"❌ Ошибка: {result}", show_alert=True)
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
            
            # Сбрасываем состояние и возвращаемся к основному экрану
            scene_data['credit_state'] = 'main'
            scene_data['credit_amount'] = 0
            scene_data['credit_period'] = 0
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        else:
            await callback.answer(
                f"✅ Кредит оформлен!\n"
                f"Сумма: {credit_amount:,} 💰\n"
                f"Срок: {credit_period} ход(ов)".replace(",", " "),
                show_alert=True
            )
            # Сбрасываем состояние и возвращаемся к основному экрану
            scene_data['credit_state'] = 'main'
            scene_data['credit_amount'] = 0
            scene_data['credit_period'] = 0
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
    
    @Page.on_callback('cancel_credit')
    async def cancel_credit_handler(self, callback: CallbackQuery, args: list):
        """Отмена взятия кредита или оплаты"""
        scene_data = self.scene.get_data('scene')
        scene_data['credit_state'] = 'main'
        scene_data['credit_amount'] = 0
        scene_data['credit_period'] = 0
        scene_data['pay_credit_index'] = 0
        scene_data['error_message'] = ''  # Очищаем ошибки
        await self.scene.set_data('scene', scene_data)
        
        await callback.answer("❌ Операция отменена")
        await self.scene.update_message()
    
    @Page.on_text('int')
    async def handle_input(self, message: Message, value: int):
        """Обработка ввода чисел (срок или сумма)"""
        scene_data = self.scene.get_data('scene')
        credit_state = scene_data.get('credit_state', 'main')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        # Ввод срока кредита
        if credit_state == 'input_period':
            # Очищаем предыдущую ошибку
            scene_data['error_message'] = ''
            
            if value < 2:
                scene_data['error_message'] = 'Срок должен быть не менее 2 хода'
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
            
            # Получаем данные компании для проверки максимального срока
            company_data = await get_company(id=company_id)
            session_data = await get_session(session_id=session_id)
            if isinstance(company_data, str):
                scene_data['error_message'] = f'Ошибка: {company_data}'
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
            
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
            scene_data['credit_state'] = 'input_amount'
            await self.scene.set_data('scene', scene_data)
            
            # Обновляем сообщение для показа следующего шага
            await self.scene.update_message()
        
        # Ввод суммы кредита
        elif credit_state == 'input_amount':
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
            scene_data['credit_state'] = 'confirm'
            await self.scene.set_data('scene', scene_data)
            
            # Обновляем сообщение для показа экрана подтверждения
            await self.scene.update_message()
        
        # Ввод суммы оплаты кредита
        elif credit_state == 'pay_amount':
            # Очищаем предыдущую ошибку
            scene_data['error_message'] = ''
            
            # Получаем данные для проверки
            company_data = await get_company(id=company_id)
            if isinstance(company_data, str):
                scene_data['error_message'] = f'Ошибка: {company_data}'
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
            
            credits = company_data.get('credits', [])
            balance = company_data.get('balance', 0)
            pay_credit_index = scene_data.get('pay_credit_index', 0)
            
            if pay_credit_index >= len(credits):
                scene_data['error_message'] = 'Ошибка: кредит не найден'
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
            
            credit = credits[pay_credit_index]
            total = credit.get("total_to_pay", 0)
            paid = credit.get("paid", 0)
            need_pay = credit.get("need_pay", 0)
            remaining = total - paid
            
            # Проверяем минимальную сумму (текущий платеж)
            if value < need_pay:
                scene_data['error_message'] = f'Минимальная сумма оплаты: {need_pay:,} 💰 (текущий платеж)'.replace(",", " ")
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
            
            # Проверяем, что сумма не превышает остаток
            if value > remaining:
                scene_data['error_message'] = f'Сумма превышает остаток по кредиту! Осталось выплатить: {remaining:,} 💰'.replace(",", " ")
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
            
            # Проверяем баланс
            if value > balance:
                scene_data['error_message'] = f'Недостаточно средств! Необходимо: {value:,} 💰, Доступно: {balance:,} 💰'.replace(",", " ")
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
                return
            
            # Оплачиваем кредит
            result = await company_pay_credit(
                company_id=str(company_id),
                credit_index=pay_credit_index,
                amount=value
            )
            
            if isinstance(result, str):
                scene_data['error_message'] = f'Ошибка: {result}'
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
            else:
                # Успешная оплата - показываем уведомление и возвращаемся к главному экрану
                scene_data['credit_state'] = 'main'
                scene_data['pay_credit_index'] = 0
                scene_data['success_message'] = f'Платеж выполнен: {value:,} 💰'.replace(",", " ")
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
