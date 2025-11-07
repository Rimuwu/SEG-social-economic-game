from oms import Page, scene_manager
from modules.ws_client import get_user, get_session, get_sessions, delete_session, create_session, update_session_stage, notforgame_update_session_max_steps, get_users
import json
from modules.utils import create_buttons
import asyncio

class SessionAdd(Page):
    __page_name__ = "admin-session-add-page"
    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "settings") is None:
            await self.scene.update_key(self.__page_name__, "settings", json.dumps({
                "session_id": None, #ID сессии
                "map_pattern": None, #Паттерн карты
                "size": None, #Размер карты
                "max_steps": None, #Максимальное количество ходов
                "session_group_url": None, #URL группы сессии
                "max_companies": None, #Максимальное количество компаний
                "max_player_in_company": None, #Максимальное количество игроков в компании
                "time_on_game_stage": None, #Время на игровую стадию
                "time_on_change_stage": None #Время на стадию смены
            }))
        if self.scene.get_key(self.__page_name__, "state") is None:
            await self.scene.update_key(self.__page_name__, "state", None)

    async def content_worker(self):
        try:
            data = json.loads(self.scene.get_key(self.__page_name__, "settings"))
        except:
            data = self.scene.get_key(self.__page_name__, "settings")
        
        return self.content.format(
            session_id = data.get("session_id") if data.get("session_id") is not None else "Не задано",
            map_pattern = data.get("map_pattern") if data.get("map_pattern") is not None else "Не задано",
            size = data.get("size") if data.get("size") is not None else "Не задано",
            max_steps = data.get("max_steps") if data.get("max_steps") is not None else "Не задано",
            session_group_url = data.get("session_group_url") if data.get("session_group_url") is not None else "Не задано",
            max_companies = data.get("max_companies") if data.get("max_companies") is not None else "Не задано",
            max_player_in_company = data.get("max_player_in_company") if data.get("max_player_in_company") is not None else "Не задано",
            time_on_game_stage = data.get("time_on_game_stage") if data.get("time_on_game_stage") is not None else "Не задано",
            time_on_change_stage = data.get("time_on_change_stage") if data.get("time_on_change_stage") is not None else "Не задано"
        )
    
    
    async def buttons_worker(self):
        self.row_width = 2
        buttons = [
            create_buttons(self.scene.__scene_name__, "Задать ID", "set_id", ignore_row=True),
            create_buttons(self.scene.__scene_name__, "Задать паттерн", "set_pattern"),
            create_buttons(self.scene.__scene_name__, "Размер карты", "set_size"),
            create_buttons(self.scene.__scene_name__, "Кол-во Этапов", "set_max_steps", ignore_row=True),
            create_buttons(self.scene.__scene_name__, "URL группы сессии", "set_url", ignore_row=True),
            create_buttons(self.scene.__scene_name__, "Кол-во компаний", "set_count_comp"),
            create_buttons(self.scene.__scene_name__, "Игроков в компании", "set_count_player_in_comp"),
            create_buttons(self.scene.__scene_name__, "Время Этапа", "set_time_game_stage"),
            create_buttons(self.scene.__scene_name__, "Время Межэтапа", "set_time_change_stage"),
            create_buttons(self.scene.__scene_name__, "Создать сессию", "create_session"),
        ]

        return buttons

    @Page.on_callback("set_id")
    async def set_id(self, callback, args):
        await callback.answer("Введите ID сессии в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_id")

    @Page.on_callback("set_pattern")
    async def set_pattern(self, callback, args):
        await callback.answer("Введите паттерн карты в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_pattern")

    @Page.on_callback("set_size")
    async def set_size(self, callback, args):
        await callback.answer("Введите размер карты в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_size")

    @Page.on_callback("set_max_steps")
    async def set_max_steps(self, callback, args):
        await callback.answer("Введите кол-во этапов в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_max_steps")

    @Page.on_callback("set_url")
    async def set_url(self, callback, args):
        await callback.answer("Введите URL группы сессии в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_url")

    @Page.on_callback("set_count_comp")
    async def set_count_comp(self, callback, args):
        await callback.answer("Введите кол-во компаний в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_count_comp")

    @Page.on_callback("set_count_player_in_comp")
    async def set_count_player_in_comp(self, callback, args):
        await callback.answer("Введите кол-во игроков в компании в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_count_player_in_comp")

    @Page.on_callback("set_time_game_stage")
    async def set_time_game_stage(self, callback, args):
        await callback.answer("Введите время этапа в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_time_game_stage")

    @Page.on_callback("set_time_change_stage")
    async def set_time_change_stage(self, callback, args):
        await callback.answer("Введите время межэтапа в чат или - чтобы оставить по умолчанию", show_alert=True)
        await self.scene.update_key(self.__page_name__, "state", "set_time_change_stage")
    
    @Page.on_callback("create_session")
    async def create_session(self, callback, args):
        try:
            data = json.loads(self.scene.get_key(self.__page_name__, "settings"))
        except:
            data = self.scene.get_key(self.__page_name__, "settings")
        result = await create_session(
            session_id=data.get("session_id"),
            map_pattern=data.get("map_pattern") if data.get("map_pattern") is not None else "random",
            size=data.get("size") if data.get("size") is not None else 7,
            max_steps=data.get("max_steps") if data.get("max_steps") is not None else 15,
            session_group_url=data.get("session_group_url") if data.get("session_group_url") is not None else "",
            max_companies=data.get("max_companies") if data.get("max_companies") is not None else 10,
            max_players_in_company=data.get("max_player_in_company") if data.get("max_player_in_company") is not None else 5,
            time_on_game_stage=data.get("time_on_game_stage") if data.get("time_on_game_stage") is not None else 3,
            time_on_change_stage=data.get("time_on_change_stage") if data.get("time_on_change_stage") is not None else 1
        )

        if "error" in result:
            await callback.answer(f"❌ Ошибка: {result.get('error')}", show_alert=True)
        else:
            await callback.answer("✅ Сессия создана!", show_alert=True)
            await self.scene.update_key(self.__page_name__, "settings", None)
            await self.scene.update_page("admin-session-main-page")
        
    @Page.on_text("int")
    async def handle_int(self, message, value: int):
        try:
            data = json.loads(self.scene.get_key(self.__page_name__, "settings"))
        except:
            data = self.scene.get_key(self.__page_name__, "settings")
        state = self.scene.get_key(self.__page_name__, "state")
        
        if state == "set_size":
            data["size"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        elif state == "set_max_steps":
            data["max_steps"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        elif state == "set_count_comp":
            data["max_companies"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        elif state == "set_count_player_in_comp":
            data["max_player_in_company"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        elif state == "set_time_game_stage":
            data["time_on_game_stage"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        elif state == "set_time_change_stage":
            data["time_on_change_stage"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        
    
    @Page.on_text("str")
    async def handle_str(self, message, value: str):
        try:
            data = json.loads(self.scene.get_key(self.__page_name__, "settings"))
        except:
            data = self.scene.get_key(self.__page_name__, "settings")
        state = self.scene.get_key(self.__page_name__, "state")
        
        if state == "set_id":
            data["session_id"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        elif state == "set_pattern":
            data["map_pattern"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        elif state == "set_url":
            data["session_group_url"] = value
            await self.scene.update_key(self.__page_name__, "settings", json.dumps(data))
            await self.scene.update_message()
        

class SessionDell(Page):
    __page_name__ = "admin-session-dell-page"
    
    async def buttons_worker(self):
        result = await get_sessions()
        buttons = []
        self.row_width = 2
        if len(result) != 0:
            for s in result:
                buttons.append(create_buttons(self.scene.__scene_name__, f"{s.get('id')}", "dell_session", s.get("id")))
        
        return buttons
    
    
    @Page.on_callback("dell_session")
    async def dell_session(self, callback, args):
        flag = True
        try:
            if await get_user(id=self.scene.user_id).get("session_id") == args[1]:
                flag = False
        except:
            pass
        users = await get_users(session_id=args[1])
        print(users)
        for user in users:
            scene = scene_manager.get_scene(user['id'])
            print(user["id"])
            if scene:
                await scene.end()
        await delete_session(args[1], really=True)
        if flag:
            await callback.answer("✅ Сессия удалена!", show_alert=True)
            await self.scene.update_message()
    
    @Page.on_text("str")
    async def handle_str(self, message, value: str):
        flag = True
        try:
            if await get_user(id=self.scene.user_id).get("session_id") == value:
                flag = False
        except:
            pass
        if "error" not in await get_session(value):
            users = await get_users(session_id=value)
            for user in users:
                scene = scene_manager.get_scene(user['id'])
                if scene:
                    await scene.end()
        await delete_session(value, really=True)
        if flag:
            await self.scene.update_message()
    
        
class SessionInfo(Page):
    __page_name__ = "admin-session-info-page"
    
    async def content_worker(self):
        session = self.scene.get_key(self.__page_name__, "session_id")
        
        if session is not None:
            data = await get_session(session)
            return self.content.format(
                session_id = data.get("id"),
                stage = data.get("stage"),
                map_pattern = data.get("map_pattern"),
                size = data.get("map_size").get("rows"),
                max_steps = f'{data.get("step")}/{data.get("max_steps")}',
                event_type = data.get("event").get("type"),
                max_companies = len(data.get("companies")),
                user = len(data.get("users")),
                time_to_next_stage = data.get("time_to_next_stage")
            )
        return "Выберите сессию для просмотра информации."
    
    async def buttons_worker(self):
        session = self.scene.get_key(self.__page_name__, "session_id")
        buttons = []
        if session is not None:
            self.row_width = 1
            buttons.append(create_buttons(self.scene.__scene_name__, "Сменить этап", "to_p", "admin-session-change-stage-page"))
            buttons.append(create_buttons(self.scene.__scene_name__, "Сменить кол-во ходов", "to_p", "admin-session-change-steps-page"))
            buttons.append(create_buttons(self.scene.__scene_name__, "↪ К выбору", "back_to_s", ignore_row=True))
        else:
            result = await get_sessions()
            self.row_width = 2
            if len(result) != 0:
                for s in result:
                    buttons.append(create_buttons(self.scene.__scene_name__, f"{s.get('id')}", "set_session", s.get("id")))
            
            buttons.append(create_buttons(self.scene.__scene_name__, "↪ Назад", "to_p", "admin-session-main-page", ignore_row=True))

        return buttons
    
    
    @Page.on_callback("set_session")
    async def set_session(self, callback, args: list):
        await self.scene.update_key(self.__page_name__, "session_id", args[1])
        await self.scene.update_message()
    
    
    @Page.on_callback("to_p")
    async def to_pages(self, callback, args: list):
        await self.scene.update_page(args[1])
    
    
    @Page.on_callback("back_to_s")
    async def back_to_s(self, callback, args: list):
        await self.scene.update_key(self.__page_name__, "session_id", None)
        await self.scene.update_message()


class SessonChangeStage(Page):
    __page_name__ = "admin-session-change-stage-page"

    async def data_preparate(self):
        if self.scene.get_key(self.__page_name__, "add_shedule") is None:
            await self.scene.update_key(self.__page_name__, "add_shedule", True)
    
    async def content_worker(self):
        data = await get_session(self.scene.get_key("admin-session-info-page", "session_id"))
        stage = data.get("stage")
        return self.content.format(
            current_stage = stage
            )
    async def buttons_worker(self):
        self.row_width = 2
        add_shedule = self.scene.get_key(self.__page_name__, "add_shedule")
        buttons = [
            create_buttons(self.scene.__scene_name__, "FreeUserConnect", "change_stage", "FreeUserConnect"),
            create_buttons(self.scene.__scene_name__, "CellSelect", "change_stage", "CellSelect"),
            create_buttons(self.scene.__scene_name__, "Game", "change_stage", "Game"),
            create_buttons(self.scene.__scene_name__, "End", "change_stage", "End")
        ]
        buttons.append(create_buttons(self.scene.__scene_name__, "✅ Таймер" if add_shedule else "❌ Таймер", "toggle_shedule"))
        return buttons

    @Page.on_callback("change_stage")
    async def change_stage(self, callback, args: list):
        session_id = self.scene.get_key("admin-session-info-page", "session_id")
        add_shedule = self.scene.get_key(self.__page_name__, "add_shedule")
        await update_session_stage(session_id, args[1], add_shedule=add_shedule)
        await callback.answer("✅ Этап сессии изменён!", show_alert=True)
        await self.scene.update_page("admin-session-info-page")
    
    @Page.on_callback("toggle_shedule")
    async def toggle_shedule(self, callback, args: list):
        add_shedule = self.scene.get_key(self.__page_name__, "add_shedule")
        await self.scene.update_key(self.__page_name__, "add_shedule", not add_shedule)
        await self.scene.update_message()
    
    
class SessionChangeSteps(Page):
    __page_name__ = "admin-session-change-steps-page"
    
    
    async def content_worker(self):
        session_id = self.scene.get_key("admin-session-info-page", "session_id")
        data = await get_session(session_id)
        steps = f'{data.get("step")}/{data.get("max_steps")}'
        return self.content.format(step=steps)
    
    @Page.on_text("int")
    async def handle_int(self, message, value: int):
        session_id = self.scene.get_key("admin-session-info-page", "session_id")
        await notforgame_update_session_max_steps(session_id, value)
        await self.scene.update_page("admin-session-info-page")