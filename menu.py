from functools import partial
from os.path import join

from blit_text import blit_text
from entites import Player
from buttons import Button
from constants import DIRECTION_RIGHT, DIRECTION_LEFT, GUIDE_PAGES_COORDS, \
    UPGRADE_PAGES_COORDS, DEFAULT_CURSOR, ACTIVE_CURSOR, LEVELS_AMOUNT
from pygame import Surface, Rect
from pygame.draw import rect
from typing import Callable, Literal

from sqlite3 import connect


class Menu:
    """ Менюшка, где есть задний фон и кнопочки """

    def __init__(self, button_settings: list[tuple[
        int, int, int, int, Surface, Surface, str, Callable
    ]], background_image: Surface) -> None:
        """

        :param button_settings: Настройки для кнопок (ширина; высота; x; y;
        изображение активной кнопки; изображение неактивной кнопки;
        текст кнопки; функция, которая будет вызвана)
        :param background_image: Фоновое изображение для текущей менюшки

        """
        self.buttons = [Button(*cur_button_settings) for
                        cur_button_settings in button_settings]
        self.background_image = background_image

    def draw(self, screen, *args, **kwargs):
        """ Отрисовываем менюшку """
        arrow_idx = DEFAULT_CURSOR
        result = (None,)
        # Лепим изображение на экран
        screen.blit(self.background_image, (0, 0))
        # Отрисовываем кнопки
        for button in self.buttons:
            button_answer = button.draw(screen)
            if arrow_idx != ACTIVE_CURSOR and \
                    button_answer[0] == ACTIVE_CURSOR:
                arrow_idx = button_answer[0]
                result = button_answer[1:]
        return arrow_idx, result


class SelectLevelMenu(Menu):
    """ Меню выбора уровня (тут есть прикол с отображением информауии о
    врагах и отображение номера уровня, а также награды за уровень)

    """

    def __init__(
            self, button_settings: list[tuple[
                int, int, int, int, Surface, Surface, str, Callable
            ]], background_image: Surface, active_select_level_button_image,
            inactive_select_level_button_image
    ) -> None:
        super().__init__(button_settings, background_image)
        self.current_level = 1
        cur_level_amount = LEVELS_AMOUNT
        for x in range(LEVELS_AMOUNT // 3 + 1):
            for y in range(min(cur_level_amount, 3)):
                button_number = x * 3 + y + 1
                self.buttons.append(
                    Button(
                        47, 45, 440 + 63 * y, 125 + 61 * x,
                        active_select_level_button_image,
                        inactive_select_level_button_image,
                        str(button_number),
                        partial(self.update_level_info, button_number),
                        font_size=30
                    )
                )

    def show_level_info(
            self, screen: Surface, current_level_mark_coords: tuple[int, int],
            levels_reward: dict[int, int],
            current_level_reward_coords: tuple[int, int],
            enemies_info_coords: list[tuple[int, int]],
            *args, **kwargs
    ) -> None:
        """ Отображаем инфу об выбранном уровне

        :param screen: Экран, на котором, будет отображаться вся инфа
        :param current_level: Номер текущего уровня
        :param current_level_mark_coords: Координаты цифры, отображающей
        номаер выбранного уровня
        :param levels_reward: Словарь, который содержит номер уровня (ключ)
        и его награду (значение)
        :param current_level_reward_coords: Координаты цифры, отображающей
        награду за текущий уровень
        :param enemies_amount: Здесь содержится информация о количестве
        врагов каждого типа
        :param enemies_info_coords: Координаты цифры, отображающей
        количество врага определенного типа, хранятся в виде списка для
        каждого типа врага

        """
        # Отображаем номер текущего уровня
        blit_text(screen, str(self.current_level), *current_level_mark_coords,
                  center=True)

        # Отображаем нагарду за текщий уровень
        blit_text(screen, str(levels_reward[self.current_level]),
                  *current_level_reward_coords, font_size=25)

        enemies_amount = self.get_enemies_amount(
            f'level_{self.current_level}.txt'
        )

        # Отображаем для каждого типа врага его количество на карте уровня
        for index, current_coords in enumerate(enemies_info_coords):
            blit_text(screen, str(enemies_amount[index]), *current_coords,
                      font_size=16, center=True)

    def get_enemies_amount(self, filename: str) -> tuple:
        """Получение количества врагов на уровне

        :param filename: имя файла уровня
        """
        # Путь к файлу
        fullname = join('data', 'levels', filename)
        # Читаем уровень, убирая символы перевода строки
        with open(fullname, 'r', encoding='utf8') as mapFile:
            level_map = mapFile.read()

        return (level_map.count('o') + level_map.count('O'),
                level_map.count('a') + level_map.count('A'),
                level_map.count('m') + level_map.count('M'),
                level_map.count('h') + level_map.count('H'))

    def update_level_info(self, button_number):
        """Обновление информации об уровне"""
        self.current_level = button_number

    def draw(self, screen: Surface, *args, **kwargs):
        """ Отрисовываем менюшку """
        arrow_idx, result = super().draw(screen)
        self.show_level_info(screen, *args, **kwargs)
        return arrow_idx, result


class GuideMenu(Menu):

    def __init__(self, button_settings, background_image, guide_list):
        super().__init__(button_settings, background_image)
        self.buttons[1].action = partial(self.shift_guide_index,
                                         DIRECTION_LEFT)
        self.buttons[2].action = partial(self.shift_guide_index,
                                         DIRECTION_RIGHT)
        self.guide_list = guide_list
        self.current_guide_index = 0

    def shift_guide_index(self, arrow_direction: Literal[0, 1]) -> None:
        """ Смена индекса окна руководства

        :param arrow_direction: направление стрелки 0 | 1

        """
        if arrow_direction == DIRECTION_LEFT:
            self.current_guide_index -= 1
            if self.current_guide_index < 0:
                self.current_guide_index = len(self.guide_list) - 1
        else:
            self.current_guide_index += 1
            if self.current_guide_index > len(self.guide_list) - 1:
                self.current_guide_index = 0

    def draw(self, screen, *args, **kwargs):
        """ Отрисовываем менюшку """
        arrow_idx, result = super().draw(screen)
        screen.blit(self.guide_list[self.current_guide_index],
                    GUIDE_PAGES_COORDS)
        return arrow_idx, result


class UpgradeMenu(Menu):
    def __init__(self, button_settings, background_image,
                 improvement_scales) -> None:
        super().__init__(button_settings, background_image)
        self.improvement_scales = improvement_scales
        self.current_improvement_scale_index = 0
        self.buttons[1].action = partial(self.shift_improvement_scale_index,
                                         DIRECTION_LEFT)
        self.buttons[2].action = partial(self.shift_improvement_scale_index,
                                         DIRECTION_RIGHT)

    def shift_improvement_scale_index(
            self, arrow_direction: Literal[0, 1]
    ) -> None:
        """ Смена индекса окна руководства

        :param arrow_direction: направление стрелки 0 | 1

        """
        if arrow_direction == DIRECTION_LEFT:
            self.current_improvement_scale_index -= 1
            if self.current_improvement_scale_index < 0:
                self.current_improvement_scale_index = \
                    len(self.improvement_scales) - 1
        else:
            self.current_improvement_scale_index += 1
            if self.current_improvement_scale_index > \
                    len(self.improvement_scales) - 1:
                self.current_improvement_scale_index = 0

    def draw(self, screen, *args, **kwargs):
        """ Отрисовываем менюшку """
        arrow_idx, result = super().draw(screen)
        self.improvement_scales[self.current_improvement_scale_index].draw(
            screen, UPGRADE_PAGES_COORDS
        )
        return arrow_idx, result


class ImprovementScales:

    def __init__(
            self, image, scale_objects, active_upgrade_button_image,
            inactive_upgrade_button_image, player, upgrade_sound
    ):
        self.image = image
        self.scale_objects = scale_objects
        self.upgrade_buttons = []

        for index in range(len(self.scale_objects)):
            self.upgrade_buttons.append(Button(
                21, 21, 472, 215 + index * 48,
                active_upgrade_button_image,
                inactive_upgrade_button_image,
                '', partial(
                    self.upgrade, index, player, upgrade_sound
                )
            ))
            if scale_objects[index].current_cost == 'max':
                self.upgrade_buttons[index].is_visible = False

    def upgrade(self, index, player, upgrade_sound):
        con = connect('DataBase.sqlite')
        cur = con.cursor()
        sign = 1
        # проверка наличия нужной суммы монет для пользователя
        if player.coins - int(self.scale_objects[index].current_cost) >= 0:
            # вычитание цены из общей суммы монет пользователя и обновление
            # баланса в БД
            player.coins -= int(self.scale_objects[index].current_cost)
            cur.execute(f'UPDATE Player_data SET Coins = {player.coins}')
            con.commit()
            # проверка на заполнение полоски до конца (всего 5 делений по 0.2)
            if self.scale_objects[index].current_cost != 'max':
                upgrade_sound.play()
                self.scale_objects[index].stage += 1
                cur.execute(
                    f'UPDATE Scales '
                    f'SET {self.scale_objects[index].scale_name} = '
                    f'{self.scale_objects[index].stage}'
                )
                # изменение характеристики
                if self.scale_objects[index].scale_name == 'Shot_delay':
                    sign = -1

                # Берем старое значение
                old_value = cur.execute(
                    f'SELECT {self.scale_objects[index].scale_name} '
                    f'FROM Player_data'
                ).fetchone()[0]
                # Присваиваем новое
                cur.execute(
                    f"""
                    UPDATE Player_data SET 
                    {self.scale_objects[index].scale_name} = 
                    {old_value + self.scale_objects[index].delta_value * sign}
                    """
                )
                con.commit()
                # обновляем измененную величину
                self.update_player_scales(
                    self.scale_objects[index].scale_name, cur, player
                )
                # изменение цены для покупки
                self.scale_objects[index].current_cost = cur.execute(
                    f"""
                    SELECT {self.scale_objects[index].scale_name} 
                    FROM Scales_costs WHERE Id = 
                    {self.scale_objects[index].stage + 1}
                    """
                ).fetchone()[0]
                # увеличение длинны темного прямоугольника (за светлым)
                self.scale_objects[index].internal_rect.width += \
                    self.scale_objects[index].max_width * 0.2
                # увеличение светлой полоски
                self.scale_objects[index].external_rect.width += \
                    self.scale_objects[index].max_width * 0.2
                # если полоска дошла до конца, то обозначается полная прокачка
                # характеристики и кнопка становится невидима
                if self.scale_objects[index].current_cost == 'max':
                    self.upgrade_buttons[index].is_visible = False
        con.close()

    def update_player_scales(self, scale: str, cur, player: Player) -> None:
        """
        Функция для обновления переменных после изменения характеристик в БД
        :param scale: характеристика из категории
        :param cur: курсор базы данных
        :param player: объект класса Player
        """
        if scale == 'Ammo':
            player.clip_size = cur.execute(
                'SELECT Ammo FROM Player_data'
            ).fetchone()[0]
            player.ammo = player.clip_size
        elif scale == 'Shot_delay':
            player.shot_delay = cur.execute(
                'SELECT Shot_delay FROM Player_data'
            ).fetchone()[0]
        elif scale == 'Damage':
            player.damage = cur.execute(
                "SELECT Damage FROM Player_data"
            ).fetchone()[0]
        elif scale == 'HP':
            player.max_hp = cur.execute(
                "SELECT HP FROM Player_data"
            ).fetchone()[0]
            player.hp = player.max_hp
        elif scale == 'Shields':
            player.max_shield = cur.execute(
                'SELECT Shields FROM Player_data'
            ).fetchone()[0]
            player.shield = player.max_shield

    def draw(self, screen, upgrade_page_coords):
        screen.blit(self.image, upgrade_page_coords)
        for index, improvement_scale in enumerate(self.scale_objects):
            rect(screen, '#d19900', improvement_scale.external_rect)
            rect(screen, '#fff200', improvement_scale.internal_rect)
            blit_text(screen, improvement_scale.current_cost,
                      313, 220 + index * 48, font_size=9
                      )
        for button in self.upgrade_buttons:
            button.draw(screen)


class ImprovementScale:
    """Класс изображения шкалы прокачки"""

    def __init__(self, pos_x: int, pos_y: int, width: int, height: int,
                 border_width: int, scale_name: str):
        """
        :param pos_x: координата по оси x
        :param pos_y: координата по оси y
        :param width: ширина
        :param height: высота
        :param border_width: ширина границы
        :param scale_name: название шкалы прокачки

        """
        con = connect('DataBase.sqlite')
        cur = con.cursor()
        # Имя шкалы
        self.scale_name = scale_name
        # Стадия прокачки
        self.stage = cur.execute(
            f'SELECT {scale_name} FROM Scales'
        ).fetchone()[0]
        # Темная полоска (фигура)
        self.external_rect = Rect(
            pos_x, pos_y, width * 0.2 * self.stage, height
        )
        # Светлая полоска (фигура)
        self.internal_rect = Rect(
            pos_x + border_width, pos_y + border_width,
            width * 0.2 * self.stage - (border_width * 2),
            height - (border_width * 2)
        )
        # Текущая цена
        self.current_cost = cur.execute(
            f'SELECT {scale_name} FROM Scales_costs WHERE Id = '
            f'{self.stage + 1}'
        ).fetchone()[0]
        # Значение изменения характеристики
        self.delta_value = cur.execute(
            f'SELECT {scale_name} FROM Scales_delta'
        ).fetchone()[0]
        # Максимальная ширина
        self.max_width = width
        con.close()
