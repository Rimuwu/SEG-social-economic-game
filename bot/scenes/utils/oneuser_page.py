from oms import Page
from oms import scene_manager

class OneUserPage(Page):

    __for_blocked_pages__: list[str] = []
    __blocked_text__: str = "🔒 Доступ к этой странице заблокирован, так как на ней уже находится другой пользователь."

    def page_blocked(self):
        """ Отвечает сцене, можно ли перейти на эту страницу
            Возвращает кортеж (bool, str) - можно ли перейти, и сообщение если нельзя
        """
        company_id = self.scene.get_key('scene', 'company_id')

        for se in self.__for_blocked_pages__ + [
            self.__page_name__
            ]:

            scenes = scene_manager.get_for_params(
                self.__scene__.name, se
            )
            for s in scenes:
                if s == self.scene: continue # На всякий

                if s.get_key('scene', 'company_id') == company_id:
                    return False, self.__blocked_text__

        return True, 'all_ok'