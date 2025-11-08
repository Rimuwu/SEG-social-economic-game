from asyncio import sleep
import asyncio
import os
from pprint import pprint
import random
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from game.statistic import Statistic
from game.logistics import Logistics
from game.stages import stage_game_updater
from global_modules.api_configurate import get_fastapi_app
from modules.logs import *
from modules.db import just_db
from modules.sheduler import scheduler
from game.session import session_manager
from game.exchange import Exchange
from game.citie import Citie
from os import getenv
from global_modules.logs import main_logger
from routers.ws_company import *

# Импортируем роуты
from routers import connect_ws

debug = getenv("DEBUG", "False").lower() == "true"

@asynccontextmanager
async def lifespan(app: FastAPI):

    game_logger.info("====================== GAME is starting up...")
    websocket_logger.info("====================== GAME is starting up...")
    main_logger.info("====================== GAME is starting up...")
    routers_logger.info("====================== GAME is starting up...")

    # Startup
    websocket_logger.info("Creating missing tables on startup...")
    # await just_db.drop_all() # Тестово

    await just_db.create_table('sessions') # Таблица сессий
    await just_db.create_table('users') # Таблица пользователей
    await just_db.create_table('companies') # Таблица компаний
    await just_db.create_table('time_schedule') # Таблица с задачами по времени
    await just_db.create_table('step_schedule') # Таблица с задачами по шагам
    await just_db.create_table('contracts') # Таблица с контрактами
    await just_db.create_table('cities') # Таблица с городами
    await just_db.create_table('exchanges') # Таблица с биржей
    await just_db.create_table('factories') # Таблица с заводами
    await just_db.create_table('item_price') # Таблица с ценами на товары
    await just_db.create_table('logistics') # Таблица с логистикой
    await just_db.create_table('statistics') # Таблица со статистикой

    websocket_logger.info("Loading sessions from database...")
    await session_manager.load_from_base()

    await sleep(5)
    websocket_logger.info("Starting task scheduler...")

    asyncio.create_task(scheduler.start())
    if debug:
        asyncio.create_task(test3())

    yield

    websocket_logger.info("API is shutting down...")

    websocket_logger.info("Stopping task scheduler...")
    scheduler.stop()
    await scheduler.cleanup_shutdown_tasks()

app = get_fastapi_app(
    title="API",
    version="6.6.6",
    description="SEG API",
    debug=os.getenv("DEBUG", "False").lower() == "true",
    lifespan=lifespan,
    routers=[
        connect_ws.router
    ],
    api_logger=websocket_logger
)

@app.get("/")
async def root(request: Request):
    return {"message": f"{app.description} is running! v{app.version}"}

@app.get("/ping")
async def ping(request: Request):
    return {"message": "pong"}

async def test1():
    
    from game.user import User
    from game.session import Session, session_manager, SessionStages
    from game.company import Company
    from game.contract import Contract

    await asyncio.sleep(2)

    # Очистка и создание сессии
    if await session_manager.get_session('AFRIKA'):
        session = await session_manager.get_session('AFRIKA')
        if session: await session.delete()

    session = await session_manager.create_session('AFRIKA')
    
    print("Session created")
    
    user1 = await User().create(
        1,
        session_id=session.session_id,
        username="User 1"
    )

    user2 = await User().create(
        2,
        session_id=session.session_id,
        username="User 2"
    )
    
    comp1 = await user1.create_company("Company 1")
    comp2 = await user2.create_company("Company 2")


    await session.update_stage(SessionStages.CellSelect)
    await session.reupdate()


    print(f'=== STAGE: {session.stage} === STEP4545 {session.step} ===')

    for _ in range(29):
        await stage_game_updater(session.session_id)
        for i in [session, comp1, comp2]:
            await i.reupdate()

        print(f"=== STEP {session.step} ({session.stage}) ===")
        if session.stage == SessionStages.Game.value:
            for comp in [comp1, comp2]:
                coins = random.randint(
                    -comp.balance, comp.balance * 2)
                comp.balance += coins

                rep = random.randint(-comp.reputation, 10)
                comp.reputation += rep

                await comp.save_to_base()

    await session.update_stage(SessionStages.End)
    await session.reupdate()
    print(session.stage)

    comp_id = comp1.id
    st = await Statistic.get_all_by_company(
        session_id=session.session_id, company_id=comp_id)

    # Простая CLI визуализация
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ИГРЫ - ГРАФИК БАЛАНСА")
    print("="*60)
    
    # Получаем статистику для обеих компаний
    stats_comp1 = await Statistic.get_all_by_company(session.session_id, comp1.id)
    stats_comp2 = await Statistic.get_all_by_company(session.session_id, comp2.id)
    
    if stats_comp1 and stats_comp2:
        print(f"\n🏢 Company 1 (ID: {comp1.id}) vs Company 2 (ID: {comp2.id})")
        print("-" * 60)
        
        # Создаем простой текстовый график
        max_steps = max(len(stats_comp1), len(stats_comp2))
        
        for i in range(min(len(stats_comp1), len(stats_comp2))):
            stat1 = stats_comp1[i]
            stat2 = stats_comp2[i]
            
            # Нормализация для отображения
            balance1 = stat1.balance
            balance2 = stat2.balance
            
            # Создаем бары для визуализации
            max_bar_length = 30
            max_balance = max(abs(balance1), abs(balance2), 1)
            
            bar1_length = int((abs(balance1) / max_balance) * max_bar_length)
            bar2_length = int((abs(balance2) / max_balance) * max_bar_length)
            
            bar1 = "█" * bar1_length if balance1 >= 0 else "▓" * bar1_length
            bar2 = "█" * bar2_length if balance2 >= 0 else "▓" * bar2_length
            
            print(f"Шаг {stat1.step:2d} | Comp1: {balance1:6d} {bar1:<30} | Comp2: {balance2:6d} {bar2:<30}")
    
    # Итоговая статистика
    print("\n" + "="*60)
    print("📈 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("="*60)
    
    final_comp1 = stats_comp1[-1] if stats_comp1 else None
    final_comp2 = stats_comp2[-1] if stats_comp2 else None
    
    if final_comp1 and final_comp2:
        print(f"🏢 Company 1:")
        print(f"   💰 Баланс: {final_comp1.balance}")
        print(f"   ⭐ Репутация: {final_comp1.reputation}")
        print(f"   🏭 Заводы: {final_comp1.factories}")
        print(f"   📈 Экон. мощь: {final_comp1.economic_power}")
        
        print(f"\n🏢 Company 2:")
        print(f"   💰 Баланс: {final_comp2.balance}")
        print(f"   ⭐ Репутация: {final_comp2.reputation}")
        print(f"   🏭 Заводы: {final_comp2.factories}")
        print(f"   📈 Экон. мощь: {final_comp2.economic_power}")
        
        # Определяем победителя
        winner = "Company 1" if final_comp1.balance > final_comp2.balance else "Company 2"
        print(f"\n🏆 ПОБЕДИТЕЛЬ ПО БАЛАНСУ: {winner}")
        
    print("\n" + "="*60)
    


async def test2():
    
    from game.user import User
    from game.session import Session, session_manager, SessionStages
    from game.company import Company
    from game.contract import Contract

    # Очистка и создание сессии
    if await session_manager.get_session('test'):
        session = await session_manager.get_session('test')
        if session: await session.delete()

    session = await session_manager.create_session('test')

    await sleep(2)

    print("Session created")

    # user1 = await User().create(
    #     1,
    #     session_id=session.session_id,
    #     username="User 1"
    # )

    # user2 = await User().create(
    #     2,
    #     session_id=session.session_id,
    #     username="User 2"
    # )

    for i in range(44):
        # await asyncio.sleep(0.5)
        user1 = await User().create(
            i,
            session_id=session.session_id,
            username=f"User {i}"
        )
        comp = await user1.create_company(f"Company {i}")
        for j in range(4):
            user = await User().create(
                i*100 + j + 1,
                session_id=session.session_id,
                username=f"User {i*10 + j + 1}n"
            )
            await user.add_to_company(comp.secret_code)

    await sleep(10)
    await session.update_stage(SessionStages.CellSelect)
    # for i in [session, comp1, comp2]:
    #     await i.reupdate()
    
    await sleep(10)
    await session.update_stage(SessionStages.Game)
    
    # await comp1.set_position(0, 0)
    # await comp2.set_position(0, 1)

    # await session.update_stage(SessionStages.Game)
    # for i in [session, comp1, comp2]:
    #     await i.reupdate()

    # await comp1.take_credit(1000, 3)
    # print('Taking credit...')
    # res = await handle_company_take_credit(
    #     'test',
    #     {
    #         "company_id": str(comp1.id),
    #         "amount": 1000,
    #         "period": 3,
    #         "password": getenv('UPDATE_PASSWORD')
    #     }
    # )
    
    # print("Credit taken:", res)
    # # 666 коммит моооооой by AS1
    

async def test3():
    
    from game.user import User
    from game.session import Session, session_manager, SessionStages
    from game.company import Company
    from game.contract import Contract

    # Очистка и создание сессии
    if await session_manager.get_session('test3'):
        session = await session_manager.get_session('test3')
        if session: await session.delete()

    session = await session_manager.create_session('test3')

    await sleep(2)

    print("Session created")

    user1 = await User().create(
        1,
        session_id=session.session_id,
        username="User 1"
    )

    user2 = await User().create(
        2,
        session_id=session.session_id,
        username="User 2"
    )

    comp1 = await user1.create_company("Company 1")
    comp2 = await user2.create_company("Company 2")
    
    await comp1.add_resource("wood", 20, True)
    # await comp2.add_balance(20000)
    
    await session.update_stage(SessionStages.CellSelect)
    
    await session.update_stage(SessionStages.Game)
    for i in [session, comp1, comp2]:
        await i.reupdate()

    cr = await Contract().create(
        supplier_company_id=comp1.id,
        customer_company_id=comp2.id,
        session_id=session.session_id,
        who_creator=comp1.id,
        resource="wood",
        amount_per_turn=10,
        duration_turns=2,
        payment_amount=10000
    )
    
    await cr.accept_contract(comp2.id)
    
    await session.update_stage(SessionStages.ChangeTurn)
    
    await session.update_stage(SessionStages.Game)
    for i in [session, comp1, comp2]:
        await i.reupdate()