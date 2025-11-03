from pprint import pprint
from aiogram import F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import os
import asyncio

from modules.ws_client import *
from modules.utils import go_to_page, update_page
from modules.db import db
from modules.load_scenes import load_scenes_from_db
from filters.admins import *
from modules.states import *

from oms import scene_manager

from bot_instance import dp, bot


# Список ID администраторов
UPDATE_PASSWORD = os.getenv("UPDATE_PASSWORD", "default_password")


@dp.message(AdminFilter(), Command("sg"))
async def start_game(message: Message, state: FSMContext):
    msg = await message.answer("Введите ID сессии для её старта:")
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(StartGameStates.waiting_for_session_id)

@dp.message(StartGameStates.waiting_for_session_id)
async def process_start_session_id(message: Message, state: FSMContext):
    session_id = message.text
    data = await state.get_data()
    msg_id = data['msg_id']
    response = await update_session_stage(
        session_id=session_id,
        stage='CellSelect',
    )
    
    await message.delete()
    if response is not None and "error" in response.keys():
        await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text=f"❌ Ошибка при запуске сессии: {response['error']}"
        )
        await state.clear()
        return
    
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text=f"✅ Сессия с ID `{session_id}` успешно запущена!",
        parse_mode="Markdown"
    )
    db.drop_all()
    await state.clear()
    

@dp.message(AdminFilter(), Command("cg"))
async def create_game(message: Message, state: FSMContext):
    msg = await message.answer("Введите ID сессии для новой игры или '-' для генерации ID:")
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(CreateGameStates.waiting_for_session_id)


@dp.message(CreateGameStates.waiting_for_session_id)
async def process_session_id(message: Message, state: FSMContext):
    session_id = message.text
    data = await state.get_data()
    msg_id = data['msg_id']
    session_id_i = None if session_id == "-" else session_id
    response = await create_session(
        session_id=session_id_i
    )
    await message.delete()
    if response is None:
        await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text=f"❌ Ошибка при создании сессии. Ответа нет."
        )
        await state.clear()
        return
    
    elif "error" in response.keys():
        await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text=f"❌ Ошибка при создании сессии: {response['error']}"
        )
        await state.clear()
        return
    
    await update_session_stage(
        session_id=response["session"]['id'],
        stage='FreeUserConnect',
    )
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text=f"✅ Успешно создана игровая сессия!\n🆔 Код сессии: `{response['session']['id']}`",
        parse_mode="Markdown"
    )
    await state.clear()

@dp.message(AdminFilter(), Command("ds"))
async def delete_session_command(message: Message, state: FSMContext):
    msg = await message.answer("Введите ID сессии для её удаления:")
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(DeleteSessionStates.waiting_for_session_id)


@dp.message(DeleteSessionStates.waiting_for_session_id)
async def process_delete_session_id(message: Message, state: FSMContext):
    session_id = message.text
    data = await state.get_data()
    msg_id = data['msg_id']
    
    users = await get_users(session_id=session_id)
    reposnse2 = await get_session(session_id=session_id)
    response = await delete_session(
        session_id=session_id,
        really=True
    )
    print("==========================")
    print(users)
    print(reposnse2)
    print(response)
    print(message.text)
    print("==========================")
    for user in users:
        scene = scene_manager.get_scene(user['id'])
        if scene:
            await scene.end()
    
    await message.delete()
    if response is not None and "error" in response.keys():
        await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text=f"❌ Ошибка при удалении сессии: {response['error']}"
        )
        await state.clear()
        return
    
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text=f"✅ Сессия с ID `{session_id}` успешно удалена!",
        parse_mode="Markdown"
    )
    await state.clear()


@dp.message(AdminFilter(), Command("step"))
async def change_session_stage(message: Message):
    """
    Команда для изменения этапа сессии
    Формат: /step <код_сессии> <этап>
    Этапы: FreeUserConnect, CellSelect, Game, End
    """
    # Парсим аргументы команды
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        await message.answer(
            "❌ Неверный формат команды!\n\n"
            "Используйте: `/step <код_сессии> <этап>`\n\n"
            "Доступные этапы:\n"
            "• `FreeUserConnect` - свободное подключение\n"
            "• `CellSelect` - выбор клетки\n"
            "• `Game` - игра\n"
            "• `End` - конец игры",
            parse_mode="Markdown"
        )
        return
    
    session_id = args[1].strip()
    stage = args[2].strip()
    
    # Проверяем валидность этапа
    valid_stages = ['FreeUserConnect', 'CellSelect', 'Game', 'End']
    if stage not in valid_stages:
        await message.answer(
            f"❌ Неверный этап: `{stage}`\n\n"
            f"Доступные этапы: {', '.join([f'`{s}`' for s in valid_stages])}",
            parse_mode="Markdown"
        )
        return
    
    # Выполняем запрос к API
    try:
        response = await update_session_stage(
            session_id=session_id,
            stage=stage
        )
        
        if response is None:
            await message.answer(
                f"⚠️ Запрос отправлен: сессия `{session_id}` → этап `{stage}`",
                parse_mode="Markdown"
            )
        elif isinstance(response, dict) and "error" in response:
            await message.answer(
                f"❌ Ошибка: {response['error']}",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"✅ Этап сессии `{session_id}` изменён на `{stage}`",
                parse_mode="Markdown"
            )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при выполнении команды: {str(e)}",
            parse_mode="Markdown"
        )


@dp.message(Command("leave"))
async def leave_session(message: Message, state: FSMContext):
    msg = await message.answer("Отправьте 'Да' для подтверждения выхода из сессии или что угодно для отмены.")
    await state.update_data(msg_id=msg.message_id)
    await state.set_state(ConfirmLeaveStates.waiting_for_confirmation)


@dp.message(ConfirmLeaveStates.waiting_for_confirmation)
async def confirm_leave(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    msg_id = data['msg_id']
    if message.text.lower() != "да":
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg_id,
            text="Выход из сессии отменен."
        )
        await state.clear()
        return
    user_id = message.from_user.id
    await delete_user(user_id=user_id)
    scene = scene_manager.get_scene(user_id)
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=msg_id,
        text="Ваше существование в сессии приравнено к 0, спасибо за игру."
    )
    await scene.end()
    await state.clear()

    
@dp.message(Command("prevpage"))
async def go_previous_page(message: Message):
    """Возвращает пользователя на предыдущую страницу сцены."""
    user_id = message.from_user.id

    scene = scene_manager.get_scene(user_id)
    scene_data = scene.get_data('scene') or {}
    try:
        await scene.update_page("main-page")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Не удалось переключиться: {exc}")


# http://localhost:81/ws/status - тут можно посмотреть статус вебсокета и доступные типы для отправки сообщений через send_message
@dp.message(Command("ping"))
async def ping_command(message: Message):
    """Обработчик команды /ping"""
    try:
        # Отправляем ping через клиент
        response = await ws_client.send_message(
            "ping", {'from': message.from_user.id})
        print(f"Ответ от сервера: {response}")
    except Exception as e:
        await message.answer(f"Ошибка при выполнении ping: {str(e)}")

@ws_client.on_message('pong')
async def on_pong(message: dict):
    """Обработчик ответа pong от сервера"""
    print(f"Получен pong от сервера: {message}")

    from_id = message.get('content', {}).get('from')

    await bot.send_message(from_id, "Pong! 🏓")

@ws_client.on_event("connect")
async def on_connect():
    await load_scenes_from_db(scene_manager)
    print("🔗 Подключено к WebSocket серверу")

@ws_client.on_message('api-update_session_stage')
async def on_update_session_stage(message: dict):
    """Обработчик обновления стадии сессии"""
    print(message)
    data = message.get('data', {})
    session_id = data.get('session_id')
    new_stage = data.get('new_stage')
    print("=====================", session_id, new_stage)
    
    if new_stage == "CellSelect":
        # Получаем все компании в сессии
        companies = await get_companies(session_id=session_id)
        
        for company in companies:
            company_id = company.get('id')
            owner_id = company.get('owner')
            
            # Получаем всех пользователей компании
            users = await get_users(session_id=session_id, company_id=company_id)
            
            for user in users:
                user_id = user.get('id')
                
                if user_id and scene_manager.has_scene(user_id):
                    scene = scene_manager.get_scene(user_id)
                    if scene:
                        # Владелец идёт на страницу выбора клетки
                        if user_id == owner_id:
                            await scene.update_page("select-cell-page")
                        else:
                            # Остальные ждут выбора владельца
                            await scene.update_page("wait-select-cell-page")
    
    elif new_stage == "Game":
        # Проверяем каждую компанию на нахождение в тюрьме
        companies = await get_companies(session_id=session_id)
        
        for company in companies:
            company_id = company.get('id')
            in_prison = company.get('in_prison', False)
            
            # Получаем всех пользователей компании
            users = await get_users(session_id=session_id, company_id=company_id)
            
            for user in users:
                user_id = user.get('id')
                
                if user_id and scene_manager.has_scene(user_id):
                    scene = scene_manager.get_scene(user_id)
                    if scene:
                        current_page = scene.page
                        
                        # Если компания в тюрьме - переводим на страницу тюрьмы
                        if in_prison:
                            await scene.update_page("prison-page")
                        else:
                            # Переводим с wait-game-stage-page или change-turn-page на main-page
                            if current_page not in ["start", "name-enter", "company-create", "company-join", "wait-start-page"]:
                                await scene.update_page("main-page")
    
    elif new_stage == "ChangeTurn":
        await go_to_page(session_id, None, "change-turn-page")
        await asyncio.sleep(5)
        await go_to_page(session_id, None, "change-turn-page")
        
    
    elif new_stage == "End":
        await go_to_page(session_id, None, "end-game-page")


@ws_client.on_event("disconnect")
async def on_disconnect():
    print("❌ Отключено от WebSocket сервера")

    for _ in range(15, 0, -1):
        print(f"🔄 Попытка подключения...")
        await ws_client.connect(max_attempts=10)
        if ws_client.is_connected():
            print("✅ Повторное подключение успешно!")
            return

        print(f"❌ Не удалось подключиться, повтор через 1 секунду...")
        await asyncio.sleep(1)

    print("❌ Не удалось подключиться после 15 попыток, выход.")


@ws_client.on_message("api-company_to_prison")
async def on_company_to_prison(message: dict):
    data = message.get('data', {})
    company_id = data.get('company_id')
    await go_to_page(company_id, None, "prison-page")


@ws_client.on_message("api-company_set_position")
async def on_company_set_position(message: dict):
    """Обработчик установки позиции компании"""
    data = message.get('data', {})
    company_id = data.get('company_id')
    new_position = data.get('new_position')
    
    print(f"[api-company_set_position] Company {company_id} set position to {new_position}")
    
    if not company_id:
        return
    
    # Переводим всех пользователей компании на страницу ожидания начала игры
    users = await get_users(company_id=company_id)
    
    print(f"[api-company_set_position] Found {len(users) if users else 0} users in company {company_id}")
    
    for user in users:
        user_id = user.get('id')
        
        if user_id and scene_manager.has_scene(user_id):
            scene = scene_manager.get_scene(user_id)
            if scene:
                current_page = scene.page
                
                print(f"[api-company_set_position] User {user_id} current page: {current_page}")
                
                # Переводим только если пользователь был на странице выбора или ожидания
                if current_page in ["select-cell-page", "wait-select-cell-page"]:
                    print(f"[api-company_set_position] Moving user {user_id} to wait-game-stage-page")
                    await scene.update_page("wait-game-stage-page")
    
    
@dp.message(Command("docs"), AdminFilter())
async def docs(message: Message):
    
    result = await get_sessions()
    pprint(result)
    
    result = await get_users()
    pprint(result)
    
    result = await get_companies()
    pprint(result)
    
    result = await get_factories()
    pprint(result)