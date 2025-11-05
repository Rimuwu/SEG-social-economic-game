from oms import Page
from aiogram.types import CallbackQuery, Message
from oms.utils import callback_generator
from modules.ws_client import (
    get_sessions, get_session, create_session, delete_session, update_session_stage,
    get_companies, get_company, notforgame_update_company_name,
    get_users, get_user, update_user, delete_user
)
from global_modules.logs import Logger
import math

bot_logger = Logger.get_logger("bot")


class AdminPanelPage(Page):
    
    __page_name__ = "admin-panel-page"
    
    async def data_preparate(self):
        """Инициализация данных админ-панели"""
        scene_data = self.scene.get_data('scene')
        
        # Инициализируем состояние, если его нет
        if 'admin_state' not in scene_data:
            scene_data['admin_state'] = 'main'  # main, sessions, companies, users
            scene_data['admin_substate'] = None  # create_session, delete_session, change_stage и т.д.
            scene_data['admin_page'] = 0  # Для пагинации
            scene_data['admin_temp_data'] = {}  # Временные данные
            await self.scene.set_data('scene', scene_data)
    
    async def content_worker(self):
        """Контент админ-панели"""
        scene_data = self.scene.get_data('scene')
        admin_state = scene_data.get('admin_state', 'main')
        admin_substate = scene_data.get('admin_substate')
        
        # Главное меню
        if admin_state == 'main':
            return await self._main_menu()
        
        # === СЕССИИ ===
        elif admin_state == 'sessions':
            if admin_substate is None:
                return await self._sessions_menu_content()
            elif admin_substate == 'input_create':
                return await self._session_input_create()
            elif admin_substate == 'list_delete':
                return await self._session_list_delete()
            elif admin_substate == 'confirm_delete':
                return await self._session_confirm_delete()
            elif admin_substate == 'list_change_stage':
                return await self._session_list_change_stage()
            elif admin_substate == 'select_stage':
                return await self._session_select_stage()
        
        # === КОМПАНИИ ===
        elif admin_state == 'companies':
            if admin_substate is None:
                return await self._companies_menu_content()
            elif admin_substate == 'list':
                return await self._companies_list()
            elif admin_substate == 'input_info':
                return await self._company_input_info()
            elif admin_substate == 'show_info':
                return await self._company_show_info()
            elif admin_substate == 'input_rename_id':
                return await self._company_input_rename_id()
            elif admin_substate == 'input_rename_name':
                return await self._company_input_rename_name()
        
        # === ПОЛЬЗОВАТЕЛИ ===
        elif admin_state == 'users':
            if admin_substate is None:
                return await self._users_menu_content()
            elif admin_substate == 'list':
                return await self._users_list()
            elif admin_substate == 'input_rename_id':
                return await self._user_input_rename_id()
            elif admin_substate == 'input_rename_name':
                return await self._user_input_rename_name()
            elif admin_substate == 'input_delete_id':
                return await self._user_input_delete_id()
            elif admin_substate == 'confirm_delete':
                return await self._user_confirm_delete()
        
        return "❌ Неизвестное состояние"
    
    # ============================================
    # ГЛАВНОЕ МЕНЮ
    # ============================================
    
    async def _main_menu(self):
        return """🔧 *Админ-панель*

Добро пожаловать в панель администратора!

Выберите раздел для работы:"""
    
    async def buttons_worker(self):
        """Генерация кнопок в зависимости от состояния"""
        scene_data = self.scene.get_data('scene')
        admin_state = scene_data.get('admin_state', 'main')
        admin_substate = scene_data.get('admin_substate')
        
        # Главное меню
        if admin_state == 'main':
            return await self._main_menu_buttons()
        
        # Сессии
        elif admin_state == 'sessions':
            if admin_substate is None:
                return await self._sessions_menu_buttons()
            elif admin_substate == 'input_create':
                return await self._session_create_input_buttons()
            elif admin_substate == 'list_delete':
                return await self._session_delete_buttons()
            elif admin_substate == 'confirm_delete':
                return await self._session_confirm_buttons()
            elif admin_substate == 'list_change_stage':
                return await self._session_change_stage_list_buttons()
            elif admin_substate == 'select_stage':
                return await self._session_select_stage_buttons()
        
        # Компании
        elif admin_state == 'companies':
            if admin_substate is None:
                return await self._companies_menu_buttons()
            elif admin_substate == 'list':
                return await self._companies_list_buttons()
            elif admin_substate == 'show_info':
                return await self._company_info_back_button()
        
        # Пользователи
        elif admin_state == 'users':
            if admin_substate is None:
                return await self._users_menu_buttons()
            elif admin_substate == 'list':
                return await self._users_list_buttons()
            elif admin_substate == 'confirm_delete':
                return await self._user_confirm_delete_buttons()
        
        return []
    
    async def _main_menu_buttons(self):
        """Кнопки главного меню"""
        buttons = [
            {'text': '🎮 Сессии', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'sessions')},
            {'text': '🏢 Компании', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'companies')},
            {'text': '👥 Пользователи', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'users')},
            {'text': '⬅️ Назад', 'callback_data': callback_generator(self.scene.__scene_name__, 'admin_back')},
        ]
        self.row_width = 1
        return buttons
    
    # ============================================
    # СЕССИИ - МЕНЮ И ОБРАБОТЧИКИ
    # ============================================
    
    async def _sessions_menu_buttons(self):
        """Кнопки меню сессий"""
        buttons = [
            {'text': '➕ Создать', 'callback_data': callback_generator(self.scene.__scene_name__, 'session_create')},
            {'text': '🗑 Удалить', 'callback_data': callback_generator(self.scene.__scene_name__, 'session_delete')},
            {'text': '🔄 Сменить этап', 'callback_data': callback_generator(self.scene.__scene_name__, 'session_change_stage')},
            {'text': '⬅️ В главное меню', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'main')},
        ]
        self.row_width = 2
        return buttons
    
    async def _sessions_menu_content(self):
        """Контент меню сессий"""
        scene_data = self.scene.get_data('scene')
        last_message = scene_data.get('admin_temp_data', {}).get('last_message', '')
        
        text = "🎮 *Управление сессиями*\n\n"
        
        if last_message:
            text += f"{last_message}\n\n"
            # Очищаем сообщение после показа
            scene_data['admin_temp_data']['last_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        text += "Выберите действие:"
        return text
    
    async def _session_input_create(self):
        return """🎮 *Создание сессии*

Отправьте ID для новой сессии или нажмите кнопку "Сгенерировать", чтобы создать автоматически."""
    
    async def _session_create_input_buttons(self):
        """Кнопки для ввода ID сессии при создании"""
        buttons = [
            {'text': '🎲 Сгенерировать автоматически', 'callback_data': callback_generator(self.scene.__scene_name__, 'session_create_auto')},
            {'text': '⬅️ Назад', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'sessions')},
        ]
        self.row_width = 1
        return buttons
    
    async def _session_list_delete(self):
        sessions = await get_sessions()
        if not sessions or len(sessions) == 0:
            return "📋 *Нет доступных сессий для удаления*"
        
        text = "🗑 *Удаление сессии*\n\n"
        text += "Выберите сессию для удаления:\n\n"
        
        for session in sessions:
            sid = session.get('id', 'N/A')
            stage = session.get('stage', 'N/A')
            step = session.get('step', 0)
            text += f"• `{sid}` | Этап: {stage} | Ход: {step}\n"
        
        return text
    
    async def _session_confirm_delete(self):
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('admin_temp_data', {}).get('delete_session_id')
        return f"""⚠️ *Подтверждение удаления*

Вы уверены, что хотите удалить сессию `{session_id}`?

Это действие необратимо!"""
    
    async def _session_list_change_stage(self):
        sessions = await get_sessions()
        if not sessions or len(sessions) == 0:
            return "📋 *Нет доступных сессий*"
        
        text = "🔄 *Смена этапа сессии*\n\n"
        text += "Выберите сессию:\n\n"
        
        for session in sessions:
            sid = session.get('id', 'N/A')
            stage = session.get('stage', 'N/A')
            step = session.get('step', 0)
            text += f"• `{sid}`\n  Этап: *{stage}* | Ход: {step}\n\n"
        
        return text
    
    async def _session_select_stage(self):
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('admin_temp_data', {}).get('change_stage_session_id')
        add_schedule = scene_data.get('admin_temp_data', {}).get('add_schedule', True)
        
        schedule_icon = "✅" if add_schedule else "❌"
        
        return f"""🔄 *Смена этапа сессии*

Сессия: `{session_id}`
Автоматический таймер: {schedule_icon}

Выберите новый этап:"""
    
    async def _session_delete_buttons(self):
        """Кнопки списка сессий для удаления"""
        sessions = await get_sessions()
        buttons = []
        
        if sessions and len(sessions) > 0:
            for session in sessions:
                sid = session.get('id', 'N/A')
                stage = session.get('stage', 'N/A')
                buttons.append({
                    'text': f"{sid[:8]}... | {stage}",
                    'callback_data': callback_generator(self.scene.__scene_name__, 'session_delete_confirm', sid)
                })
        
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'sessions')
        })
        
        self.row_width = 1
        return buttons
    
    async def _session_confirm_buttons(self):
        """Кнопки подтверждения удаления"""
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('admin_temp_data', {}).get('delete_session_id')
        
        buttons = [
            {'text': '✅ Да, удалить', 'callback_data': callback_generator(self.scene.__scene_name__, 'session_delete_yes', session_id)},
            {'text': '❌ Отмена', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'sessions')},
        ]
        self.row_width = 2
        return buttons
    
    async def _session_change_stage_list_buttons(self):
        """Кнопки списка сессий для смены этапа"""
        sessions = await get_sessions()
        buttons = []
        
        if sessions and len(sessions) > 0:
            for session in sessions:
                sid = session.get('id', 'N/A')
                stage = session.get('stage', 'N/A')
                buttons.append({
                    'text': f"{sid[:8]}... | {stage}",
                    'callback_data': callback_generator(self.scene.__scene_name__, 'session_select_for_stage', sid)
                })
        
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'sessions')
        })
        
        self.row_width = 1
        return buttons
    
    async def _session_select_stage_buttons(self):
        """Кнопки выбора этапа"""
        scene_data = self.scene.get_data('scene')
        add_schedule = scene_data.get('admin_temp_data', {}).get('add_schedule', True)
        schedule_icon = "✅" if add_schedule else "❌"
        
        stages = [
            ('FreeUserConnect', 'Подключение'),
            ('CellSelect', 'Выбор клеток'),
            ('Game', 'Игра'),
            ('End', 'Конец игры')
        ]
        
        buttons = []
        for stage_key, stage_name in stages:
            buttons.append({
                'text': stage_name,
                'callback_data': callback_generator(self.scene.__scene_name__, 'session_set_stage', stage_key)
            })
        
        buttons.append({
            'text': f'{schedule_icon} Менять этап по времени',
            'callback_data': callback_generator(self.scene.__scene_name__, 'session_toggle_schedule')
        })
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(self.scene.__scene_name__, 'session_change_stage')
        })
        
        self.row_width = 2
        return buttons
    
    # ============================================
    # КОМПАНИИ - КОНТЕНТ И КНОПКИ
    # ============================================
    
    async def _companies_menu_buttons(self):
        """Кнопки меню компаний с пагинацией"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        
        companies = await get_companies()
        if not companies:
            companies = []
        
        per_page = 30
        total_pages = math.ceil(len(companies) / per_page) if companies else 1
        
        buttons = []
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append({
                'text': '⬅️ Пред.',
                'callback_data': callback_generator(self.scene.__scene_name__, 'companies_page', page - 1)
            })
        
        if page < total_pages - 1:
            nav_buttons.append({
                'text': '➡️ След.',
                'callback_data': callback_generator(self.scene.__scene_name__, 'companies_page', page + 1)
            })
        
        if nav_buttons:
            buttons.extend(nav_buttons)
        
        # Кнопки действий
        buttons.extend([
            {'text': 'ℹ️ Информация о компании', 'callback_data': callback_generator(self.scene.__scene_name__, 'company_info')},
            {'text': '✏️ Изменить имя', 'callback_data': callback_generator(self.scene.__scene_name__, 'company_rename')},
            {'text': '⬅️ В главное меню', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'main')},
        ])
        
        self.row_width = 2
        return buttons
    
    async def _companies_menu_content(self):
        """Контент меню компаний со списком"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        last_message = scene_data.get('admin_temp_data', {}).get('last_message', '')
        
        text = "🏢 *Управление компаниями*\n\n"
        
        if last_message:
            text += f"{last_message}\n\n"
            # Очищаем сообщение после показа
            scene_data['admin_temp_data']['last_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        # Получаем и показываем список компаний
        companies = await get_companies()
        if not companies or len(companies) == 0:
            text += "📋 Нет зарегистрированных компаний\n\n"
        else:
            # Пагинация (30 компаний на страницу)
            per_page = 30
            total_pages = math.ceil(len(companies) / per_page)
            start_idx = page * per_page
            end_idx = start_idx + per_page
            page_companies = companies[start_idx:end_idx]
            
            text += f"📋 *Список компаний* (стр. {page + 1}/{total_pages})\n\n"
            
            for company in page_companies:
                cid = company.get('id', 'N/A')
                name = company.get('name', 'Без имени')
                session = company.get('session_id', 'N/A')
                text += f"• ID: `{cid}` | {name}\n  Сессия: `{session}`\n\n"
        
        text += "Выберите действие:"
        return text
    
    async def _companies_list(self):
        """Список всех компаний с пагинацией"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        
        companies = await get_companies()
        if not companies or len(companies) == 0:
            return "📋 *Нет зарегистрированных компаний*"
        
        # Пагинация (30 компаний на страницу)
        per_page = 30
        total_pages = math.ceil(len(companies) / per_page)
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_companies = companies[start_idx:end_idx]
        
        text = f"🏢 *Список компаний* (страница {page + 1}/{total_pages})\n\n"
        
        for company in page_companies:
            cid = company.get('id', 'N/A')
            name = company.get('name', 'Без имени')
            session = company.get('session_id', 'N/A')
            text += f"• ID: `{cid}` | {name} | Сессия: `{session}`\n"
        
        return text
    
    async def _companies_list_buttons(self):
        """Кнопки пагинации для списка компаний"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        
        companies = await get_companies()
        if not companies:
            companies = []
        
        per_page = 30
        total_pages = math.ceil(len(companies) / per_page) if companies else 1
        
        buttons = []
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append({
                'text': '⬅️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'companies_page', page - 1)
            })
        
        nav_buttons.append({
            'text': 'ℹ️ Инфо',
            'callback_data': callback_generator(self.scene.__scene_name__, 'company_info')
        })
        
        if page < total_pages - 1:
            nav_buttons.append({
                'text': '➡️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'companies_page', page + 1)
            })
        
        buttons.extend(nav_buttons)
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'companies')
        })
        
        self.row_width = 3
        return buttons
    
    async def _company_input_info(self):
        return """ℹ️ *Информация о компании*

Отправьте ID компании для получения подробной информации."""
    
    async def _company_show_info(self):
        """Показать подробную информацию о компании"""
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('admin_temp_data', {}).get('info_company_id')
        
        company = await get_company(id=company_id)
        if not company or 'error' in company:
            return f"❌ Компания с ID `{company_id}` не найдена"
        
        # Основная информация
        cid = company.get('id')
        name = company.get('name', 'Без имени')
        balance = company.get('balance', 0)
        reputation = company.get('reputation', 0)
        session_id = company.get('session_id', 'N/A')
        
        # Кредиты и вклады
        credits = company.get('credits', [])
        deposits = company.get('deposits', [])
        
        # Владелец и участники
        owner_id = company.get('owner', 0)
        users = await get_users(company_id=cid)
        
        # Склад
        warehouses = company.get('warehouses', {})
        total_items = sum(warehouses.values())
        
        # Позиция
        cell_position = company.get('cell_position', 'Не выбрана')
        
        # Налоги
        tax_debt = company.get('tax_debt', 0)
        overdue_steps = company.get('overdue_steps', 0)
        
        # Формируем текст
        text = f"🏢 *Информация о компании*\n\n"
        text += f"*Основное:*\n"
        text += f"• ID: `{cid}`\n"
        text += f"• Название: {name}\n"
        text += f"• Баланс: {balance:,} 💰\n".replace(",", " ")
        text += f"• Репутация: {reputation} ⭐\n"
        text += f"• Сессия: `{session_id}`\n\n"
        
        text += f"*Финансы:*\n"
        text += f"• Кредитов: {len(credits)}\n"
        text += f"• Вкладов: {len(deposits)}\n"
        text += f"• Налоговый долг: {tax_debt:,} 💰\n".replace(",", " ")
        text += f"• Просроченных ходов: {overdue_steps}\n\n"
        
        text += f"*Участники:*\n"
        if users and len(users) > 0:
            for user in users:
                uid = user.get('id')
                username = user.get('username', 'Без имени')
                is_owner = " 👑" if uid == owner_id else ""
                text += f"• {username} (`{uid}`){is_owner}\n"
        else:
            text += "• Нет участников\n"
        text += "\n"
        
        text += f"*Склад:*\n"
        text += f"• Всего предметов: {total_items}\n\n"
        
        text += f"*Расположение:*\n"
        text += f"• Клетка: {cell_position}\n"
        
        return text
    
    async def _company_info_back_button(self):
        """Кнопка возврата из информации о компании"""
        buttons = [
            {'text': '⬅️ Назад', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'companies')}
        ]
        self.row_width = 1
        return buttons
    
    async def _company_input_rename_id(self):
        return """✏️ *Изменение имени компании*

Отправьте ID компании, имя которой нужно изменить."""
    
    async def _company_input_rename_name(self):
        scene_data = self.scene.get_data('scene')
        company_id = scene_data.get('admin_temp_data', {}).get('rename_company_id')
        return f"""✏️ *Изменение имени компании*

Компания ID: `{company_id}`

Отправьте новое имя для компании."""
    
    # ============================================
    # ПОЛЬЗОВАТЕЛИ - КОНТЕНТ И КНОПКИ
    # ============================================
    
    async def _users_menu_buttons(self):
        """Кнопки меню пользователей с пагинацией"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        
        users = await get_users()
        if not users:
            users = []
        
        per_page = 30
        total_pages = math.ceil(len(users) / per_page) if users else 1
        
        buttons = []
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append({
                'text': '⬅️ Пред.',
                'callback_data': callback_generator(self.scene.__scene_name__, 'users_page', page - 1)
            })
        
        if page < total_pages - 1:
            nav_buttons.append({
                'text': '➡️ След.',
                'callback_data': callback_generator(self.scene.__scene_name__, 'users_page', page + 1)
            })
        
        if nav_buttons:
            buttons.extend(nav_buttons)
        
        # Кнопки действий
        buttons.extend([
            {'text': '✏️ Изменить имя', 'callback_data': callback_generator(self.scene.__scene_name__, 'user_rename')},
            {'text': '🗑 Удалить пользователя', 'callback_data': callback_generator(self.scene.__scene_name__, 'user_delete')},
            {'text': '⬅️ В главное меню', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'main')},
        ])
        
        self.row_width = 2
        return buttons
    
    async def _users_menu_content(self):
        """Контент меню пользователей со списком"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        last_message = scene_data.get('admin_temp_data', {}).get('last_message', '')
        
        text = "👥 *Управление пользователями*\n\n"
        
        if last_message:
            text += f"{last_message}\n\n"
            # Очищаем сообщение после показа
            scene_data['admin_temp_data']['last_message'] = ''
            await self.scene.set_data('scene', scene_data)
        
        # Получаем и показываем список пользователей
        users = await get_users()
        if not users or len(users) == 0:
            text += "📋 Нет зарегистрированных пользователей\n\n"
        else:
            # Пагинация (30 пользователей на страницу)
            per_page = 30
            total_pages = math.ceil(len(users) / per_page)
            start_idx = page * per_page
            end_idx = start_idx + per_page
            page_users = users[start_idx:end_idx]
            
            text += f"📋 *Список пользователей* (стр. {page + 1}/{total_pages})\n\n"
            
            for user in page_users:
                uid = user.get('id', 'N/A')
                username = user.get('username', 'Без имени')
                company_id = user.get('company_id', 'Нет')
                session = user.get('session_id', 'N/A')
                text += f"• ID: `{uid}` | {username}\n  Компания: {company_id} | Сессия: `{session}`\n\n"
        
        text += "Выберите действие:"
        return text
    
    async def _users_list(self):
        """Список всех пользователей с пагинацией"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        
        users = await get_users()
        if not users or len(users) == 0:
            return "📋 *Нет зарегистрированных пользователей*"
        
        # Пагинация (30 пользователей на страницу)
        per_page = 30
        total_pages = math.ceil(len(users) / per_page)
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_users = users[start_idx:end_idx]
        
        text = f"👥 *Список пользователей* (страница {page + 1}/{total_pages})\n\n"
        
        for user in page_users:
            uid = user.get('id', 'N/A')
            username = user.get('username', 'Без имени')
            company_id = user.get('company_id', 'Нет')
            session = user.get('session_id', 'N/A')
            text += f"• ID: `{uid}` | {username}\n  Компания: {company_id} | Сессия: `{session}`\n\n"
        
        return text
    
    async def _users_list_buttons(self):
        """Кнопки пагинации для списка пользователей"""
        scene_data = self.scene.get_data('scene')
        page = scene_data.get('admin_page', 0)
        
        users = await get_users()
        if not users:
            users = []
        
        per_page = 30
        total_pages = math.ceil(len(users) / per_page) if users else 1
        
        buttons = []
        
        # Кнопки навигации
        if page > 0:
            buttons.append({
                'text': '⬅️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'users_page', page - 1)
            })
        
        if page < total_pages - 1:
            buttons.append({
                'text': '➡️',
                'callback_data': callback_generator(self.scene.__scene_name__, 'users_page', page + 1)
            })
        
        buttons.append({
            'text': '⬅️ Назад',
            'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'users')
        })
        
        self.row_width = 2
        return buttons
    
    async def _user_input_rename_id(self):
        return """✏️ *Изменение имени пользователя*

Отправьте ID пользователя, имя которого нужно изменить."""
    
    async def _user_input_rename_name(self):
        scene_data = self.scene.get_data('scene')
        user_id = scene_data.get('admin_temp_data', {}).get('rename_user_id')
        return f"""✏️ *Изменение имени пользователя*

Пользователь ID: `{user_id}`

Отправьте новое имя для пользователя."""
    
    async def _user_input_delete_id(self):
        return """🗑 *Удаление пользователя*

Отправьте ID пользователя для удаления."""
    
    async def _user_confirm_delete(self):
        scene_data = self.scene.get_data('scene')
        user_id = scene_data.get('admin_temp_data', {}).get('delete_user_id')
        user = await get_user(id=user_id)
        
        if not user or 'error' in user:
            return f"❌ Пользователь с ID `{user_id}` не найден"
        
        username = user.get('username', 'Без имени')
        company_id = user.get('company_id', 'Нет')
        
        return f"""⚠️ *Подтверждение удаления*

Вы уверены, что хотите удалить пользователя?

• ID: `{user_id}`
• Имя: {username}
• Компания: {company_id}

Это действие необратимо!"""
    
    async def _user_confirm_delete_buttons(self):
        """Кнопки подтверждения удаления пользователя"""
        scene_data = self.scene.get_data('scene')
        user_id = scene_data.get('admin_temp_data', {}).get('delete_user_id')
        
        buttons = [
            {'text': '✅ Да, удалить', 'callback_data': callback_generator(self.scene.__scene_name__, 'user_delete_yes', user_id)},
            {'text': '❌ Отмена', 'callback_data': callback_generator(self.scene.__scene_name__, 'goto', 'users')},
        ]
        self.row_width = 2
        return buttons
    
    # ============================================
    # ОБРАБОТЧИКИ CALLBACKS
    # ============================================
    
    @Page.on_callback('goto')
    async def goto_handler(self, callback: CallbackQuery, args: list):
        """Переход между разделами"""
        scene_data = self.scene.get_data('scene')
        target = args[1] if len(args) > 1 else 'main'
        
        scene_data['admin_state'] = target
        scene_data['admin_substate'] = None
        scene_data['admin_page'] = 0
        scene_data['admin_temp_data'] = {}
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('admin_back')
    async def admin_back_handler(self, callback: CallbackQuery, args: list):
        """Возврат на предыдущую страницу"""
        scene_data = self.scene.get_data('scene')
        previous_page = scene_data.get('previous_page', 'main-page')
        
        await self.scene.update_page(previous_page)
        await callback.answer()
    
    # === СЕССИИ CALLBACKS ===
    
    @Page.on_callback('session_create')
    async def session_create_handler(self, callback: CallbackQuery, args: list):
        """Начать создание сессии"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'input_create'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('session_create_auto')
    async def session_create_auto_handler(self, callback: CallbackQuery, args: list):
        """Автоматическое создание сессии"""
        result = await create_session()
        
        if result and 'session' in result:
            session_id = result['session']['id']
            await callback.answer(f"✅ Сессия создана: {session_id}", show_alert=True)
        else:
            await callback.answer("❌ Ошибка создания сессии", show_alert=True)
        
        # Вернуться в меню сессий
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = None
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    @Page.on_callback('session_delete')
    async def session_delete_handler(self, callback: CallbackQuery, args: list):
        """Показать список сессий для удаления"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'list_delete'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('session_delete_confirm')
    async def session_delete_confirm_handler(self, callback: CallbackQuery, args: list):
        """Подтверждение удаления сессии"""
        session_id = args[1] if len(args) > 1 else None
        if not session_id:
            await callback.answer("❌ Ошибка: ID сессии не указан")
            return
        
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'confirm_delete'
        scene_data['admin_temp_data']['delete_session_id'] = session_id
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('session_delete_yes')
    async def session_delete_yes_handler(self, callback: CallbackQuery, args: list):
        """Выполнить удаление сессии"""
        session_id = args[1] if len(args) > 1 else None
        if not session_id:
            await callback.answer("❌ Ошибка: ID сессии не указан")
            return
        
        result = await delete_session(session_id=session_id, really=True)
        
        if result is None:
            await callback.answer(f"✅ Сессия {session_id} удалена", show_alert=True)
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Нет ответа'
            await callback.answer(f"❌ Ошибка: {error_msg}", show_alert=True)
        
        # Вернуться в меню сессий
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = None
        scene_data['admin_temp_data'] = {}
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    @Page.on_callback('session_change_stage')
    async def session_change_stage_handler(self, callback: CallbackQuery, args: list):
        """Показать список сессий для смены этапа"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'list_change_stage'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('session_select_for_stage')
    async def session_select_for_stage_handler(self, callback: CallbackQuery, args: list):
        """Выбрана сессия для смены этапа"""
        session_id = args[1] if len(args) > 1 else None
        if not session_id:
            await callback.answer("❌ Ошибка: ID сессии не указан")
            return
        
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'select_stage'
        scene_data['admin_temp_data']['change_stage_session_id'] = session_id
        scene_data['admin_temp_data']['add_schedule'] = True
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('session_toggle_schedule')
    async def session_toggle_schedule_handler(self, callback: CallbackQuery, args: list):
        """Переключить автоматический таймер"""
        scene_data = self.scene.get_data('scene')
        current = scene_data.get('admin_temp_data', {}).get('add_schedule', True)
        scene_data['admin_temp_data']['add_schedule'] = not current
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('session_set_stage')
    async def session_set_stage_handler(self, callback: CallbackQuery, args: list):
        """Установить новый этап сессии"""
        stage = args[1] if len(args) > 1 else None
        if not stage:
            await callback.answer("❌ Ошибка: этап не указан")
            return
        
        scene_data = self.scene.get_data('scene')
        session_id = scene_data.get('admin_temp_data', {}).get('change_stage_session_id')
        add_schedule = scene_data.get('admin_temp_data', {}).get('add_schedule', True)
        
        result = await update_session_stage(
            session_id=session_id,
            stage=stage,
            add_shedule=add_schedule
        )
        
        if result is None or (isinstance(result, dict) and 'error' not in result):
            await callback.answer(f"✅ Этап изменён на {stage}", show_alert=True)
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if isinstance(result, dict) else 'Ошибка'
            await callback.answer(f"❌ Ошибка: {error_msg}", show_alert=True)
        
        # Вернуться в меню сессий
        scene_data['admin_substate'] = None
        scene_data['admin_temp_data'] = {}
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    # === КОМПАНИИ CALLBACKS ===
    
    @Page.on_callback('companies_list')
    async def companies_list_handler(self, callback: CallbackQuery, args: list):
        """Показать список компаний"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'list'
        scene_data['admin_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('companies_page')
    async def companies_page_handler(self, callback: CallbackQuery, args: list):
        """Переключить страницу списка компаний"""
        page = int(args[1]) if len(args) > 1 else 0
        
        scene_data = self.scene.get_data('scene')
        scene_data['admin_page'] = page
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('company_info')
    async def company_info_handler(self, callback: CallbackQuery, args: list):
        """Запросить ID компании для информации"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'input_info'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('company_rename')
    async def company_rename_handler(self, callback: CallbackQuery, args: list):
        """Запросить ID компании для переименования"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'input_rename_id'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    # === ПОЛЬЗОВАТЕЛИ CALLBACKS ===
    
    @Page.on_callback('users_list')
    async def users_list_handler(self, callback: CallbackQuery, args: list):
        """Показать список пользователей"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'list'
        scene_data['admin_page'] = 0
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('users_page')
    async def users_page_handler(self, callback: CallbackQuery, args: list):
        """Переключить страницу списка пользователей"""
        page = int(args[1]) if len(args) > 1 else 0
        
        scene_data = self.scene.get_data('scene')
        scene_data['admin_page'] = page
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('user_rename')
    async def user_rename_handler(self, callback: CallbackQuery, args: list):
        """Запросить ID пользователя для переименования"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'input_rename_id'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('user_delete')
    async def user_delete_handler(self, callback: CallbackQuery, args: list):
        """Запросить ID пользователя для удаления"""
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'input_delete_id'
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('user_delete_confirm')
    async def user_delete_confirm_handler(self, callback: CallbackQuery, args: list):
        """Подтверждение удаления пользователя"""
        user_id = int(args[1]) if len(args) > 1 else None
        if not user_id:
            await callback.answer("❌ Ошибка: ID пользователя не указан")
            return
        
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = 'confirm_delete'
        scene_data['admin_temp_data']['confirm_delete_user_id'] = user_id
        await self.scene.set_data('scene', scene_data)
        
        await self.scene.update_message()
        await callback.answer()
    
    @Page.on_callback('user_delete_yes')
    async def user_delete_yes_handler(self, callback: CallbackQuery, args: list):
        """Выполнить удаление пользователя"""
        user_id = int(args[1]) if len(args) > 1 else None
        if not user_id:
            await callback.answer("❌ Ошибка: ID пользователя не указан")
            return
        
        result = await delete_user(user_id=user_id)
        
        if result and 'error' not in result:
            await callback.answer(f"✅ Пользователь {user_id} удалён", show_alert=True)
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Нет ответа'
            await callback.answer(f"❌ Ошибка: {error_msg}", show_alert=True)
        
        # Вернуться в меню пользователей
        scene_data = self.scene.get_data('scene')
        scene_data['admin_substate'] = None
        scene_data['admin_temp_data'] = {}
        await self.scene.set_data('scene', scene_data)
        await self.scene.update_message()
    
    # ============================================
    # ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ
    # ============================================
    
    @Page.on_text('str')
    async def handle_text_input(self, message: Message, value: str):
        """Обработка текстового ввода"""
        scene_data = self.scene.get_data('scene')
        admin_state = scene_data.get('admin_state')
        admin_substate = scene_data.get('admin_substate')
        text = value  # Используем value вместо message.text
        
        # === СЕССИИ ===
        if admin_state == 'sessions' and admin_substate == 'input_create':
            # Создание сессии с указанным ID
            result = await create_session(session_id=text)
            
            # Вернуться в меню сессий
            scene_data['admin_substate'] = None
            
            # if result and 'session' in result:
            session_id = result['id']
            scene_data['admin_temp_data']['last_message'] = f"✅ Сессия создана: {session_id}"
            
            await self.scene.set_data('scene', scene_data)
            await self.scene.update_message()
        
        # === КОМПАНИИ ===
        elif admin_state == 'companies':
            if admin_substate == 'input_info':
                # Запрос информации о компании
                try:
                    company_id = int(text)
                    scene_data['admin_temp_data']['info_company_id'] = company_id
                    scene_data['admin_substate'] = 'show_info'
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
                except ValueError:
                    scene_data['admin_temp_data']['last_message'] = "❌ Ошибка: введите числовой ID компании"
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
            
            elif admin_substate == 'input_rename_id':
                # Запрос ID для переименования
                try:
                    company_id = int(text)
                    # Проверяем существование компании
                    company = await get_company(id=company_id)
                    if not company or 'error' in company:
                        scene_data['admin_temp_data']['last_message'] = f"❌ Компания с ID {company_id} не найдена"
                        await self.scene.set_data('scene', scene_data)
                        await self.scene.update_message()
                        return
                    
                    scene_data['admin_temp_data']['rename_company_id'] = company_id
                    scene_data['admin_substate'] = 'input_rename_name'
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
                except ValueError:
                    scene_data['admin_temp_data']['last_message'] = "❌ Ошибка: введите числовой ID компании"
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
            
            elif admin_substate == 'input_rename_name':
                # Применить новое имя
                company_id = scene_data.get('admin_temp_data', {}).get('rename_company_id')
                result = await notforgame_update_company_name(company_id=company_id, new_name=text)
                
                # Вернуться в меню компаний
                scene_data['admin_substate'] = None
                
                if result and 'error' not in result:
                    scene_data['admin_temp_data'] = {'last_message': f"✅ Имя компании {company_id} изменено на '{text}'"}
                else:
                    error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Нет ответа'
                    scene_data['admin_temp_data'] = {'last_message': f"❌ Ошибка: {error_msg}"}
                
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
        
        # === ПОЛЬЗОВАТЕЛИ ===
        elif admin_state == 'users':
            if admin_substate == 'input_rename_id':
                # Запрос ID для переименования
                try:
                    user_id = int(text)
                    # Проверяем существование пользователя
                    user = await get_user(id=user_id)
                    if not user or 'error' in user:
                        scene_data['admin_temp_data']['last_message'] = f"❌ Пользователь с ID {user_id} не найден"
                        await self.scene.set_data('scene', scene_data)
                        await self.scene.update_message()
                        return
                    
                    scene_data['admin_temp_data']['rename_user_id'] = user_id
                    scene_data['admin_substate'] = 'input_rename_name'
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
                except ValueError:
                    scene_data['admin_temp_data']['last_message'] = "❌ Ошибка: введите числовой ID пользователя"
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
            
            elif admin_substate == 'input_rename_name':
                # Применить новое имя
                user_id = scene_data.get('admin_temp_data', {}).get('rename_user_id')
                result = await update_user(user_id=user_id, username=text)
                
                # Вернуться в меню пользователей
                scene_data['admin_substate'] = None
                
                if result and 'error' not in result:
                    scene_data['admin_temp_data'] = {'last_message': f"✅ Имя пользователя {user_id} изменено на '{text}'"}
                else:
                    error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Нет ответа'
                    scene_data['admin_temp_data'] = {'last_message': f"❌ Ошибка: {error_msg}"}
                
                await self.scene.set_data('scene', scene_data)
                await self.scene.update_message()
            
            elif admin_substate == 'input_delete_id':
                # Запрос ID для удаления
                try:
                    user_id = int(text)
                    # Проверяем существование пользователя
                    user = await get_user(id=user_id)
                    if not user or 'error' in user:
                        scene_data['admin_temp_data']['last_message'] = f"❌ Пользователь с ID {user_id} не найден"
                        await self.scene.set_data('scene', scene_data)
                        await self.scene.update_message()
                        return
                    
                    scene_data['admin_temp_data']['delete_user_id'] = user_id
                    scene_data['admin_substate'] = 'confirm_delete'
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
                except ValueError:
                    scene_data['admin_temp_data']['last_message'] = "❌ Ошибка: введите числовой ID пользователя"
                    await self.scene.set_data('scene', scene_data)
                    await self.scene.update_message()
    