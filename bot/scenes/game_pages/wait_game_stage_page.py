from oms import Page
from modules.ws_client import get_company
from global_modules.logs import Logger
from global_modules.load_config import ALL_CONFIGS

bot_logger = Logger.get_logger("bot")


class WaitGameStagePage(Page):
    __page_name__ = "wait-game-stage-page"
    
    async def content_worker(self) -> str:
        try:
            scene_data = self.scene.get_data('scene')
            if not scene_data:
                return "⏳ Загрузка данных компании..."
            
            company_id = scene_data.get('company_id')
            session_id = scene_data.get('session')
            
            if not company_id or not session_id:
                return "⏳ Ожидание данных о компании..."

            # Получаем данные компании
            user_company = await get_company(id=company_id, session_id=session_id)
            if not user_company:
                return "❌ Ошибка загрузки данных компании"
                
            company_name = user_company.get('name', 'Неизвестная компания')
            cell_position = user_company.get('cell_position', '')
            
            content = f"🏢 **{company_name}**\n\n"
            
            if cell_position:
                # Получаем тип клетки и ресурс
                cells_config = ALL_CONFIGS.get('cells')
                if cells_config:
                    # Получаем информацию о клетке из API
                    cell_info_response = await get_company(id=company_id)
                    if cell_info_response:
                        # Пытаемся определить тип клетки по ресурсу или другим данным
                        # Для простоты выводим базовую информацию
                        content += f"📍 **Выбранная клетка**: {cell_position}\n\n"
                        
                        # Пытаемся получить информацию о типе клетки
                        from modules.ws_client import get_company_cell_info
                        cell_details = await get_company_cell_info(company_id=company_id)
                        
                        if cell_details and "error" not in cell_details:
                            cell_type = cell_details.get('type', 'Неизвестно')
                            resource = cell_details.get('resource', 'Нет')
                            
                            # Получаем метку типа клетки из конфига
                            if cells_config and hasattr(cells_config, 'types'):
                                cell_type_obj = cells_config.types.get(cell_type)
                                if cell_type_obj:
                                    cell_label = cell_type_obj.label
                                    cell_resource = cell_type_obj.resource if hasattr(cell_type_obj, 'resource') else None
                                    
                                    content += f"🗺️ **Тип клетки**: {cell_label}\n"
                                else:
                                    content += f"🗺️ **Тип клетки**: {cell_type}\n"
                            else:
                                content += f"🗺️ **Тип клетки**: {cell_type}\n"
                        else:
                            content += "🗺️ **Тип клетки**: Загрузка...\n"
                else:
                    content += f"📍 **Выбранная клетка**: {cell_position}\n\n"
                
                content += "\n⏳ **Ожидание начала игрового этапа...**"
            else:
                content += "⏳ **Ожидание выбора клетки владельцем компании...**"
            
            return content
            
        except Exception as e:
            bot_logger.error(f"Ошибка в WaitGameStagePage.content_worker: {e}")
            return f"❌ Ошибка при загрузке данных: {str(e)}"
