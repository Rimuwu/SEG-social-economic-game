from scenes.utils.oneuser_page import OneUserPage
from aiogram.types import CallbackQuery
from modules.ws_client import get_company, get_session
from oms.utils import callback_generator
from global_modules.bank import get_deposit_conditions

Page = OneUserPage

class BankDepositMain(Page):
    """Главная страница вкладов со списком активных вкладов"""
    
    __page_name__ = "bank-deposit-main"
    __for_blocked_pages__ = ["bank-menu"]
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
        
        if not company_id:
            return "❌ Ошибка: компания не найдена"
        
        # Получаем данные компании и сессии из кэша (загружается в data_preparate)
        company_data = self.scene.get_key(self.__page_name__, "company_data")
        session_data = self.scene.get_key(self.__page_name__, "session_data")
        
        if isinstance(company_data, str):
            return f"❌ Ошибка при получении данных: {company_data}"
        
        reputation = company_data.get('reputation', 0)
        deposits = company_data.get('deposits', [])
        balance = company_data.get('balance', 0)
        
        # Получаем сообщение об успехе, если есть
        success_message = scene_data.get('success_message', '')
        
        current_step = session_data.get('step', 0)
        max_step = session_data.get('max_steps', 15)
        
        # Получаем условия вклада
        try:
            conditions = get_deposit_conditions(reputation)
            
            # Параметры для шаблона
            percent = conditions.percent * 100
            balance_formatted = f"{balance:,}".replace(",", " ")
            
            # Проверяем, можно ли сделать новый вклад
            can_make_deposit = (max_step - current_step) >= 3
            if not can_make_deposit:
                availability_section = f"⚠️ *Новые вклады недоступны*\nДо конца игры осталось меньше 3 ходов\n(Текущий ход: {current_step}, до конца: {max_step - current_step})\n\n"
            else:
                availability_section = ""
            
            # Информация о количестве активных вкладов
            if deposits and len(deposits) > 0:
                active_deposits_section = f"*Активные вклады:* {len(deposits)} шт.\n_Нажмите на кнопку вклада для подробной информации_"
            else:
                active_deposits_section = "_У вас нет активных вкладов_"
            
            # Формируем текст из шаблона
            text = self.content.format(
                balance=balance_formatted,
                percent=percent,
                reputation=reputation,
                availability_section=availability_section,
                active_deposits_section=active_deposits_section
            )
            
        except ValueError:
            # Если репутация недостаточна
            text = f"🏦 *Вклады*\n\n❌ *Вклады недоступны*\nМинимальная репутация для вклада: 11\nВаша репутация: {reputation} ⭐\n\n"
            
            # Информация о количестве активных вкладов даже при недостаточной репутации
            if deposits and len(deposits) > 0:
                text += f"*Активные вклады:* {len(deposits)} шт.\n_Нажмите на кнопку вклада для подробной информации_"
            else:
                text += "_У вас нет активных вкладов_"
        
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
        session_id = scene_data.get('session')
        
        buttons = []
        
        # Получаем данные компании и сессии из кэша
        company_data = self.scene.get_key(self.__page_name__, "company_data")
        session_data = self.scene.get_key(self.__page_name__, "session_data")
        
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
            
            # Кнопки для вкладов - все кликабельны
            if deposits and len(deposits) > 0:
                for i, deposit in enumerate(deposits):
                    can_withdraw_from = deposit.get("can_withdraw_from", 0)
                    current_balance = deposit.get("current_balance", 0)
                    
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
        
        self.row_width = 1
        return buttons
    
    @Page.on_callback('open_deposit')
    async def open_deposit_handler(self, callback: CallbackQuery, args: list):
        """Начало процесса открытия вклада - переход на страницу ввода суммы"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('company_id')
        session_id = scene_data.get('session')
        
        # Проверяем репутацию и время до конца игры (используем кэш)
        company_data = self.scene.get_key(self.__page_name__, "company_data")
        session_data = self.scene.get_key(self.__page_name__, "session_data")
        
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
        
    # Переходим на страницу ввода суммы вклада
        await self.scene.update_page('bank-deposit-open-amount')
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
        
        # Сохраняем индекс вклада для просмотра
        scene_data['viewing_deposit_index'] = deposit_index
        await self.scene.set_data('scene', scene_data)
        
    # Переходим на страницу просмотра вклада
        await self.scene.update_page('bank-deposit-view')
        await callback.answer()
