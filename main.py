import os
import sys
from typing import Union, Optional

import numpy as np
import pygame
import sqlite3

from pygame import RESIZABLE, transform, VIDEORESIZE
from dashboard import *

from constants import *

from chunk import Chunk
from entities import Player
from camera import Camera
from bullets import Bullet

from menu import *

# Задаём параметры приложения
pygame.init()
pygame.key.set_repeat(200, 70)
# Экран
screen = pygame.display.set_mode((WIDTH, HEIGHT), RESIZABLE)
# Виртуальная поверхность
virtual_surface = pygame.Surface((WIDTH, HEIGHT))
# Размеры экрана
current_size = screen.get_size()
# Экземпляр часов
clock = pygame.time.Clock()

# Прячем родной курсор
pygame.mouse.set_visible(False)

# Грузим фоновую музыку и запускаем её проигрываться
pygame.mixer.music.load("data/sounds/pause_saundtrack.mp3")
pygame.mixer.music.play(loops=-1)

# Игрок
player: Optional[Player] = None

# Группа спрайтов пуль
bullet_group: pygame.sprite.Group = pygame.sprite.Group()


def load_image(filename: str) -> pygame.Surface:
    """ Загрузчик изображений
    :param filename: название изображения, которое загружаем
    :return: возвращает загружаемое изображение
    """

    # Путь к файлу
    fullname = os.path.join('data', 'images', filename)
    try:
        # Подгружаем картинку
        image = pygame.image.load(fullname)
    except pygame.error as message:
        # Если что-то поломалось
        print('Cannot load image:', filename)
        raise SystemExit(message)
    return image


def load_sound(filename: str):
    """Загрузка звукового файла
    :param filename: имя звукового файла
    """
    # Путь к файлу
    fullname = os.path.join('data', 'sounds', filename)
    try:
        # Подгружаем звуковой эффект
        sound = pygame.mixer.Sound(fullname)
    except pygame.error as message:
        # Если что-то поломалось
        print('Cannot load sound:', filename)
        raise SystemExit(message)
    return sound


def grouper(iterable, n):
    args = [iter(iterable)] * n
    return zip(*args)


def load_level(filename: str):
    """ Загрузчик уровня из -txt файла

    :param filename: название файла, в котором лежит уровень
    :return: возвращаем уровень в виде списка, где каждый элемент - один
    ряд уровня, где символами обозначены тайлы и противники с игроком
    """
    # Путь к файлу
    fullname = os.path.join('data', 'levels', filename)
    # Читаем уровень, убирая символы перевода строки
    with open(fullname, 'r', encoding='utf8') as mapFile:
        level_map = [line.strip() for line in mapFile]
        for player_y, row in enumerate(level_map):
            player_x = row.find('@')
            if player_x != -1:
                break

    # И подсчитываем максимальную длину
    max_width = max(map(len, level_map))

    # Дополняем каждую строку пустыми клетками ('.')
    level_map = list(map(lambda x: x.ljust(max_width, '.'), level_map))
    return np.array(list(map(lambda x: [''.join(i) for i in grouper(x, 8)],
                             level_map))), player_x, player_y


def generate_level(level_map, player_x, player_y) -> tuple:
    """ Генерация уровня

    :return: (Player, int, int, list[Chunk])
    """
    player_group = pygame.sprite.Group()
    chunks = []
    player = Player((player_group,), PLAYER_IMAGES, player_x, player_y)
    level_x, level_y = len(level_map[0]), int(len(level_map) // 8)
    for y1 in range(level_y):
        for x1 in range(level_x):
            chunks.append(Chunk(
                TILE_IMAGES, ENEMY_IMAGES, x1, y1,
                level_map[y1 * 8:(y1 + 1) * 8, x1:x1 + 1], level_x
            ))
    return player, player_group, level_x, level_y, chunks


def terminate() -> None:
    """ Закрытие окна игры """
    pygame.quit()
    sys.exit()


# Все функции из серии set_<окно> сделаны так, а не через lambda чисто,
# чтобы было легче ориентироваться в коде и не путаться лишний раз

def set_endgame_menu():
    """Открытие меню смерти"""
    pause, start, running = False, False, True
    return (ENDGAME_MENU, pause, start, running)


def set_victory_menu():
    """Открытие меню победы"""
    pause, start, running = False, False, True
    return (VICTORY_MENU, pause, start, running)


def set_guide_menu():
    """Открытие раздела 'Руководство'"""
    pause, start, running = False, False, True
    return (GUIDE_MENU, pause, start, running)


def set_pause_menu():
    """Открытие меню паузы"""
    pygame.mixer.music.load("data/sounds/pause_saundtrack.mp3")
    pygame.mixer.music.play(loops=-1)
    pause, start, running = True, True, True
    return (PAUSE_MENU, pause, start, running)


def set_main_menu():
    """Открытие главного меню"""
    pause, start, running = False, False, True
    return (MAIN_MENU, pause, start, running)


def set_upgrade_menu():
    """Открытие меню улучшения характеристик"""
    pause, start, running = True, True, True
    return (UPGRADE_MENU, pause, start, running)


def continue_game():
    """Выход из паузы"""
    PAUSE_STOP_SOUND.play()
    pygame.mixer.music.load("data/sounds/main_saundtrack.mp3")
    pygame.mixer.music.play(loops=-1)
    pause, start, running = False, True, True
    return (LEVEL_MAP, pause, start, running)


def draw_arrow(game_screen: pygame.Surface, image,
               pos_x: int, pos_y: int) -> None:
    """Отрисовка стрелки
    :param game_screen: виртуальная поверхность(окно) игры
    :param image: изображение курсора
    :param pos_x: позиция по оси x
    :param pos_y: позиция по оси y
    """
    game_screen.blit(image, (pos_x, pos_y))


def quit_app():
    """Выход из приложения по кнопке 'Выход'"""
    global running
    pause, start, running = False, False, False
    return (MAIN_MENU, pause, start, running)


def chunks_on_screen(camera, player, level_x, level_y) -> list:
    """Координаты чанков отрисованных на экране"""
    x1 = int((camera.x - (7 - player.grid_x) * 50) // (8 * 50))
    y1 = int((camera.y - (7 - player.grid_y) * 50) // (8 * 50))

    x2 = int(((camera.x - (7 - player.grid_x) * 50) + WIDTH) // (8 * 50))
    y2 = int(((camera.y - (7 - player.grid_y) * 50) + WIDTH) // (8 * 50))

    x1 = min(max(x1, 0), level_x - 1)
    x2 = min(max(x2, 0), level_x - 1)

    y1 = min(max(y1, 0), level_y - 1)
    y2 = min(max(y2, 0), level_y - 1)

    result = []

    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            result.append(x + y * level_x)

    return result


def start_game():
    """Запуск уровня"""
    pygame.mixer.music.load("data/sounds/main_saundtrack.mp3")
    pygame.mixer.music.play(loops=-1)
    # Игрок, размер уровня в ширину и в высоту, список чанков
    player, player_group, level_x, level_y, chunks = generate_level(
        *load_level(f'level_{select_level_menu.current_level}.txt')
    )
    # Экземпляр класса камеры
    camera = Camera(player)
    player.rect.x += camera.dx
    player.rect.y += camera.dy
    pause, start, running = False, True, True
    dashboard = Dashboard(
        [
            DashboardScale(110, 32, RECHARGE_SCALE_WIDTH,
                           RECHARGE_SCALE_HEIGTH,
                           RECHARGE_SCALE_BORDER, player.ammo,
                           player.clip_size,
                           ('#2b2b2b', '#048c73', '#aff7f5')),
            DashboardScale(52, 75, PLAYER_HEALTH_SCALE_WIDTH,
                           PLAYER_HEALTH_SCALE_HEIGTH,
                           PLAYER_HEALTH_SCALE_BORDER, player.hp,
                           player.max_hp,
                           ('#2b2b2b', '#88001b', '#cd3030')),
            DashboardScale(52, 118, PLAYER_SHIELD_SCALE_WIDTH,
                           PLAYER_SHIELD_SCALE_HEIGTH,
                           PLAYER_SHIELD_SCALE_BORDER, player.shield,
                           player.max_shield,
                           ('#2b2b2b', '#00a8f3', '#8cfffb'))
        ],
        [
            (COIN_COUNTER_IMAGE, (WIDTH * 0.75, HEIGHT * 0.025)),
            (AMMO_COUNTER_IMAGE, (10, 10)),
            (HP_COUNTER_IMAGE, (15, 70)),
            (SHIELD_COUNTER_IMAGE, (18, 111))
        ], player
    )

    weapon_upgrade_page = ImprovementScales(
        load_image('ak47_characteristics_image.png'),
        [
            ImprovementScale(337, 220, IMPROVEMENT_SCALE_WIDTH,
                             12, BORDER_WIDTH, 'Shot_delay'),
            ImprovementScale(337, 269, IMPROVEMENT_SCALE_WIDTH,
                             12, BORDER_WIDTH, 'Damage'),
            ImprovementScale(337, 316, IMPROVEMENT_SCALE_WIDTH,
                             12, BORDER_WIDTH, 'Ammo')
        ],
        ACTIVE_UPGRADE_BUTTON_IMAGE, INACTIVE_UPGRADE_BUTTON_IMAGE,
        player, UPGRADE_SOUND
    )

    player_upgrade_image = ImprovementScales(
        load_image('player_characteristics_image.png'),
        [
            ImprovementScale(337, 220, IMPROVEMENT_SCALE_WIDTH,
                             12, BORDER_WIDTH, 'HP'),
            ImprovementScale(337, 269, IMPROVEMENT_SCALE_WIDTH,
                             12, BORDER_WIDTH, 'Shields')
        ], ACTIVE_UPGRADE_BUTTON_IMAGE, INACTIVE_UPGRADE_BUTTON_IMAGE,
        player, UPGRADE_SOUND
    )

    upgrade_menu = UpgradeMenu(
        [
            RETURN_TO_PAUSE_MENU_BUTTON,
            LEFT_UPGRADE_SHIFT_BUTTON_SETTINGS,
            RIGHT_UPGRADE_SHIFT_BUTTON_SETTINGS
        ], CHARACTERISTICS_BACKGROUND,
        [
            weapon_upgrade_page, player_upgrade_image
        ]
    )
    MENUS[UPGRADE_MENU] = upgrade_menu
    current_menu = LEVEL_MAP
    return (
        current_menu, pause, start, running, player, player_group, level_x,
        level_y, chunks, camera, dashboard, upgrade_menu
    )


def set_select_level_manu():
    pause, start, running = False, False, True
    return (SELECT_LEVEL_MENU, pause, start, running)


def blur_surface(surface, amt):
    """ Блюрим задний фон """
    if amt < 1.0:
        raise ValueError('Аргумент amt должен быть больше 1.0!!!')
    scale = 1.0 / float(amt)
    surface_size = surface.get_size()
    scale_size = (int(surface_size[0] * scale), int(surface_size[1] * scale))
    surface = pygame.transform.smoothscale(surface, scale_size)
    surface = pygame.transform.smoothscale(surface, surface_size)
    return surface


# Файл и установка иконки программы
icon = load_image('icon.png')
pygame.display.set_icon(icon)

# Изображение активной кнопки выбора уровня
ACTIVE_SELECT_LEVEL_BUTTON_IMAGE = load_image(
    'active_select_level_button.png'
)
# Изображение активной кнопки выбора уровня
INACTIVE_SELECT_LEVEL_BUTTON_IMAGE = load_image(
    'inactive_select_level_button.png'
)
# Изображение неактивной кнопки возврата на выбор уровня
# Изображение неактивной кнопки возврата на выбор уровня
INACTIVE_SMALL_RETURN_BUTTON_IMAGE = load_image(
    'inactive_small_return_button_image.png'
)
# Изображение активной кнопки возврата на выбор уровня
ACTIVE_SMALL_RETURN_BUTTON_IMAGE = load_image(
    'active_small_return_button_image.png'
)
# Изображение активной кнопки сдвига меню характеристики вправо
ACTIVE_RIGHT_SHIFT_BUTTON_IMAGE = load_image(
    'active_right_shift_button_button_image.png'
)
# Изображение неактивной кнопки сдвига меню характеристики вправо
INACTIVE_RIGHT_SHIFT_BUTTON_IMAGE = load_image(
    'inactive_right_shift_button_button_image.png'
)
# Изображение активной кнопки сдвига меню характеристики вправо
ACTIVE_LEFT_SHIFT_BUTTON_IMAGE = load_image(
    'active_left_shift_button_button_image.png'
)
# Изображение неактивной кнопки сдвига меню характеристики вправо
INACTIVE_LEFT_SHIFT_BUTTON_IMAGE = load_image(
    'inactive_left_shift_button_button_image.png'
)
# Изображение активной кнопки улучшения характеристики
ACTIVE_UPGRADE_BUTTON_IMAGE = load_image('active_upgrade_button_image.png')
# Изображение неактивной кнопки улучшения характеристики
INACTIVE_UPGRADE_BUTTON_IMAGE = load_image(
    'inactive_upgrade_button_image.png'
)
# Изображение активной кнопки магазина скинов
ACTIVE_BUTTON_IMAGE = load_image('active_button_image.png')
# Изображение неактивной кнопки магазина скинов
INACTIVE_BUTTON_IMAGE = load_image('inactive_button_image.png')

# Изображения тайлов
TILE_IMAGES = {
    'l': load_image('land.png'),
    '^': load_image('light_land.png'),
    'd': load_image('dirt.png'),
    'm': load_image('mixed_dirt.png'),
    'L': load_image('light_dirt.png'),
    'b': load_image('box.png'),
    'B': load_image('shelter_box.png'),
    's': load_image('shelter_floor.png'),
    'w': load_image('shelter_wall.png'),
    'D': load_image('down_shelter_floor.png'),
    '!': load_image('reactor_image.png'),
    '*': load_image('shelter_light.png'),
    '#': load_image('shelter_small_door.png'),
    '_': load_image('shelter_background_wall_1.png'),
    '-': load_image('shelter_background_wall_2.png'),
    '/': load_image('elevator_background_image.png'),
    '0': load_image('infirmary_background_image_1.png'),
    '1': load_image('infirmary_background_image_2.png'),
    '2': load_image('infirmary_background_image_3.png'),
    '3': load_image('infirmary_background_image_4.png'),
    '4': load_image('infirmary_background_image_5.png'),
    '5': load_image('elevator_background_image_1.png'),
    '6': load_image('elevator_background_image_2.png'),
    '7': load_image('elevator_background_image_3.png'),
    '8': load_image('elevator_background_image_4.png'),
    '9': load_image('elevator_background_image_5.png'),
    'r': load_image('reactor_background_image_1.png'),
    'а': load_image('corridor_background_image_1.png'),
    'б': load_image('corridor_background_image_2.png'),
    'в': load_image('corridor_background_image_3.png'),
    'г': load_image('corridor_background_image_4.png'),
    'д': load_image('corridor_background_image_5.png'),
    'е': load_image('corridor_background_image_6.png'),
    'ё': load_image('corridor_background_image_7.png'),
    'ж': load_image('corridor_background_image_8.png'),
    'з': load_image('corridor_background_image_9.png'),
    'и': load_image('corridor_background_image_10.png'),
    'й': load_image('storage_background_image_1.png'),
    'к': load_image('storage_background_image_2.png'),
    'л': load_image('storage_background_image_3.png'),
    'м': load_image('storage_background_image_4.png'),
    'н': load_image('storage_background_image_5.png'),
    'о': load_image('storage_background_image_6.png'),
    'п': load_image('storage_background_image_7.png'),
    'р': load_image('storage_background_image_8.png'),
    'с': load_image('storage_background_image_9.png'),
    'т': load_image('storage_background_image_10.png'),
    'у': load_image('water_treatment_plant_background_image_1.png'),
    'ф': load_image('water_treatment_plant_background_image_2.png'),
    'х': load_image('water_treatment_plant_background_image_3.png'),
    'ц': load_image('water_treatment_plant_background_image_4.png'),
    'ч': load_image('water_treatment_plant_background_image_5.png'),
    'ш': load_image('water_treatment_plant_background_image_6.png'),
    'щ': load_image('water_treatment_plant_background_image_7.png'),
}

# Изображение главного меню игры
MAIN_MENU_IMAGE = load_image('main_menu_image.png')
# Задний фон для экрана с выбором уровня
SELECT_LEVEL_MENU_IMAGE = load_image('select_level_menu_image.png')
# Фон экрана смерти игрока
ENDGAME_MENU_IMAGE = load_image('player_dead_image.png')
# Фон экрана для прохождения уровня
VICTORY_MENU_IMAGE = load_image('player_victory_image.png')
# Изображение игрока
PLAYER_IMAGES = [load_image('artur_1.png'), load_image('artur_2.png'),
                 load_image('artur_3.png')]
# Изображение пули
BULLET_IMAGE = load_image('bullet.png')
# Изображения врагов
ENEMY_IMAGES = [
    [load_image('ordinary_enemy_image_1.png'),
     load_image('ordinary_enemy_image_2.png'),
     load_image('ordinary_enemy_image_3.png')],
    [load_image('heavy_enemy_1.png'),
     load_image('heavy_enemy_2.png'),
     load_image('heavy_enemy_3.png')],
    [load_image('armored_enemy_1.png'),
     load_image('armored_enemy_2.png'),
     load_image('armored_enemy_3.png')],
    [load_image('marksman_enemy_1.png'),
     load_image('marksman_enemy_2.png'),
     load_image('marksman_enemy_3.png')]
]
# Изображение пули врага
ENEMY_BULLET_IMAGE = load_image('enemy_bullet.png')
# Звук подборам монет
COIN_SELECTION_SOUND = load_sound('coin_selection.wav')
# Звук выстрела
SHOT_SOUND = load_sound('shot_sound.wav')
# Звук выстрела тяжика (звуки выстрела минигана)
HEAVY_ENEMY_SHOT_SOUND = load_sound('heavy_enemy_shot_sound.wav')
ARMORED_ENEMY_SHOT_SOUND = load_sound('armored_enemy_shot_sound.wav')
MARKSMAN_ENEMY_SHOT_SOUND = load_sound('marksman_enemy_shot_sound.wav')
# Звук перезарядки
RECHARGE_SOUND = load_sound('recharge_sound.wav')
# Звук разрушения коробки
BOX_DESTROY_SOUND = load_sound('box_destroy_sound.wav')
ENEMY_DESTROY_SOUND = load_sound('enemy_destroy_sound.wav')
# Звук попадания в препятствие
HIT_SOUND = load_sound('hit_sound.wav')
SHIELD_HIT_SOUND = load_sound('shield_hit_sound.wav')
# Задний фон
BACKGROUND_IMAGE = load_image('background_image.jpg')
# Задний фон в меню паузы
PAUSE_BACKGROUND = load_image('pause_background_image.png')
# Заданий фон для панельки с выбором характеристик
CHARACTERISTICS_BACKGROUND = load_image(
    'characteristics_background_image.png'
)
GUIDE_MENU_IMAGE = load_image(
    'guide_menu_image.png'
)
# Листы со спрайтами медной монетки
COINS_SHEETS = [load_image('copper_coins_sheet8x1.png'),
                load_image('silver_coins_sheet8x1.png'),
                load_image('golden_coins_sheet8x1.png'), ]
# Счетчик снарядов в обойме
AMMO_COUNTER_IMAGE = load_image('ammo_counter.png')
# Счетчик монеток
COIN_COUNTER_IMAGE = load_image('coin_counter.png')
# Счетчик HP
HP_COUNTER_IMAGE = load_image('hp_counter.png')
# Счетчик щита
SHIELD_COUNTER_IMAGE = load_image('shield_counter.png')
# Изображение курсора
MAIN_ARROW_IMAGE = load_image('main_cursor_image.png')
# Изображение курсора, наведенного на кликабельный предмет
CLICK_ARROW_IMAGE = load_image('click_cursor_image.png')

# Звук улучшения оружия / персонажа
UPGRADE_SOUND = load_sound('upgrade_sound.wav')
# Звук открытия меню паузы
PAUSE_START_SOUND = load_sound('pause_start_sound.wav')
# Звук закрытия меню паузы
PAUSE_STOP_SOUND = load_sound('pause_stop_sound.wav')

# Изображения курсора
ARROW_IMAGES = [MAIN_ARROW_IMAGE, CLICK_ARROW_IMAGE]

CHARACTERISTICS_IMAGES = [
    load_image('ak47_characteristics_image.png'),
    load_image('player_characteristics_image.png')
]

# Изображения руководства
GUIDE_PAGES_LIST = [
    load_image('guide_image_1.png'), load_image('guide_image_2.png'),
    load_image('guide_image_3.png'), load_image('guide_image_4.png'),
    load_image('guide_image_5.png'), load_image('guide_image_6.png'),
    load_image('guide_image_7.png'), load_image('guide_image_8.png')
]

CHARACTERISTICS_BUTTONS_SETTINGS = (
    HEIGHT // 2 + 15, HEIGHT // 2 + 64, HEIGHT // 2 + 111
)

START_BUTTON_SETTINGS = (
    151, 31, 70, 120,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Начать', set_select_level_manu
)

GUIDE_BUTTON_SETTINGS = (
    151, 31, 70, 180,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Руководство', set_guide_menu
)

QUIT_BUTTON_SETTINGS = (
    151, 31, 70, 240,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Выход', quit_app
)

START_LEVEL_BUTTON_SETTINGS = (
    151, 31, 70, 322,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Играть', start_game
)

RETURN_TO_MAIN_MENU_BUTTON_SETTINGS = (
    28, 28, 41, 327,
    ACTIVE_SMALL_RETURN_BUTTON_IMAGE,
    INACTIVE_SMALL_RETURN_BUTTON_IMAGE,
    '', set_main_menu
)

RETURN_TO_SELECT_LEVEL_BUTTON_SETTINGS = (
    151, 31, 324, 240,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Выбор уровня', set_select_level_manu
)

GUIDE_RETURN_BUTTON_SETTINGS = (
    28, 28, 187, 6,
    ACTIVE_SMALL_RETURN_BUTTON_IMAGE,
    INACTIVE_SMALL_RETURN_BUTTON_IMAGE,
    '', set_main_menu
)

RIGHT_GUIDE_SHIFT_BUTTON_SETTINGS = (
    21, 21, 585, 200,
    ACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
    INACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
    ''
)
LEFT_GUIDE_SHIFT_BUTTON_SETTINGS = (
    21, 21, 185, 200,
    ACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
    INACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
    ''
)

CONTINUE_BUTTON_SETTINGS = (
    151, 31, 322, 168,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Продолжить', continue_game
)

OPEN_CHARACTERISTICS_MENU_BUTTON = (
    151, 31, 322, 216,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Улучшение', set_upgrade_menu
)

RETURN_TO_SELECT_LEVEL_PAUSE_MENU_BUTTON_SETTINGS = (
    151, 31, 322, 266,
    ACTIVE_BUTTON_IMAGE,
    INACTIVE_BUTTON_IMAGE,
    'Выбор уровня', set_select_level_manu
)

RETURN_TO_PAUSE_MENU_BUTTON = (
    21, 21, 267, 97,
    ACTIVE_SMALL_RETURN_BUTTON_IMAGE,
    INACTIVE_SMALL_RETURN_BUTTON_IMAGE,
    '', set_pause_menu
)

RIGHT_UPGRADE_SHIFT_BUTTON_SETTINGS = (
    21, 21, 503, 222,
    ACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
    INACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
    ''
)
LEFT_UPGRADE_SHIFT_BUTTON_SETTINGS = (
    21, 21, 265, 222,
    ACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
    INACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
    ''
)

# Запущен ли основной цикл игры
running = True
# С какой стороны столкнулись спрайты
collide_side = ''
# счетчик прыжка
jump_counter = 0

# Нажата ли кнопка стрельбы
button_pushed = False

# Индекс текущего изображения курсора
arrow_idx = 0

# Стоит ли игра на паузе
pause = False

# Текущий экран
current_menu = MAIN_MENU

# Блюр изображение игры
blured_background_image = None
# Текущая категория улучшающих шкал
current_characteristics_target = 'ak-47'
# Текущая характеристика улучшений
current_characteristics_target_idx = 0

# Флаг работы уровня
start = False
# Переменная камеры
camera = None
# Переменная подключения к БД
con = None

# Индекс текущей страницы руководства
current_guide_index = 0

main_menu: Menu = Menu(
    [
        START_BUTTON_SETTINGS,
        GUIDE_BUTTON_SETTINGS,
        QUIT_BUTTON_SETTINGS
    ], MAIN_MENU_IMAGE
)

select_level_menu: SelectLevelMenu = SelectLevelMenu(
    [
        START_LEVEL_BUTTON_SETTINGS,
        RETURN_TO_MAIN_MENU_BUTTON_SETTINGS
    ], SELECT_LEVEL_MENU_IMAGE, ACTIVE_SELECT_LEVEL_BUTTON_IMAGE,
    INACTIVE_SELECT_LEVEL_BUTTON_IMAGE
)

# Меню смерти игрока :(
endgame_menu: Menu = Menu(
    [
        RETURN_TO_SELECT_LEVEL_BUTTON_SETTINGS,
    ], ENDGAME_MENU_IMAGE
)

# Экран завершения уровня
victory_menu: Menu = Menu(
    [
        RETURN_TO_SELECT_LEVEL_BUTTON_SETTINGS,
    ], VICTORY_MENU_IMAGE
)

# Меню руководства
guide_menu: GuideMenu = GuideMenu(
    [
        GUIDE_RETURN_BUTTON_SETTINGS,
        LEFT_GUIDE_SHIFT_BUTTON_SETTINGS,
        RIGHT_GUIDE_SHIFT_BUTTON_SETTINGS
    ], GUIDE_MENU_IMAGE, GUIDE_PAGES_LIST
)

# Меню паузы
pause_menu: Menu = Menu(
    [
        CONTINUE_BUTTON_SETTINGS,
        OPEN_CHARACTERISTICS_MENU_BUTTON,
        RETURN_TO_SELECT_LEVEL_PAUSE_MENU_BUTTON_SETTINGS
    ], PAUSE_BACKGROUND
)

# Список со всеми менюшками
MENUS: dict[int, Union[Menu, GuideMenu, SelectLevelMenu]] = {
    MAIN_MENU: main_menu,
    SELECT_LEVEL_MENU: select_level_menu,
    ENDGAME_MENU: endgame_menu,
    VICTORY_MENU: victory_menu,
    GUIDE_MENU: guide_menu,
    PAUSE_MENU: pause_menu
}

# Массив чанков
chunks = []
dashboard = None

# Открываем главное меню
set_main_menu()

# Кадры
frame = 0
# Направление игрока
direction = 0
# Флаг проверки стоит ли игрок на земле
on_ground = True

player_group = None
level_x, level_y = None, None

# Игровой цикл
while running:

    for event in pygame.event.get():
        # Выход из приложения
        if event.type == pygame.QUIT:
            running = False
        # Изменение размеров окна
        if event.type == VIDEORESIZE:
            current_size = event.size
        # Проверки для кнопок движения при условии старта уровня
        if start and event.type == pygame.KEYDOWN:
            # Кнопка прыжка
            if event.key == pygame.K_SPACE:
                if on_ground:
                    jump_counter = 20
                    on_ground = False
            # Движение влево
            if event.key == pygame.K_a:
                direction = 1
                player.direction = DIRECTION_LEFT
            # Движение вправо
            if event.key == pygame.K_d:
                direction = 2
                player.direction = DIRECTION_RIGHT
            # Кнопка паузы
            if event.key == pygame.K_ESCAPE:
                pause = not pause
                # Проверка находится ли пользователь в меню паузы или в игре
                if pause:
                    blured_background_image = blur_surface(virtual_surface, 15)
                    current_menu, pause = set_pause_menu()[:2]
                else:
                    PAUSE_STOP_SOUND.play()

                    if current_menu == UPGRADE_MENU:
                        current_menu, pause = set_pause_menu()[:2]
                    elif current_menu == PAUSE_MENU:
                        current_menu, pause = continue_game()[:2]
        # Отжата кнопка движения влево или вправо
        if start and event.type == pygame.KEYUP:
            if event.key == pygame.K_a or event.key == pygame.K_d:
                direction = 0
        # Нажата кнопка мыши
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Кнопка выстрела на ЛКМ
            if event.button == 1:
                button_pushed = True
            # Кнопка перезарядки на ПКМ
            elif event.button == 3 and start and not pause:
                # Проверка на полноту обоймы
                if player.ammo != player.clip_size:
                    player.ammo = 0
                    RECHARGE_SOUND.play()
                    player.recharge_timer = 120
        # Кнопка мыши отжата и если это ЛКМ, стрельба прекращается
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                button_pushed = False
    # Запущен уровень
    if start:
        # Уровень не стоит на паузе
        if not pause:
            # Выстрел если нет задержки стрельбы и есть патроны
            if not player.timer:
                if button_pushed and player.ammo:
                    player.ammo -= 1
                    # Определение направления и координаты пули
                    if player.direction == DIRECTION_LEFT:
                        x = player.x - BULLET_WIDTH
                    else:
                        x = player.x + player.rect.w + BULLET_WIDTH
                    SHOT_SOUND.play()
                    # Выпустить снаряд
                    new_bul = Bullet(
                        bullet_group, BULLET_IMAGE, player.direction,
                        x,
                        player.y + player.rect.h // 2 + 2,
                        damage=player.damage
                    )
                    player.timer = player.shot_delay
            # Уменьшаем таймер
            else:
                player.timer -= 1
            # Проверка таймера перезарядки
            if player.recharge_timer:
                # отнимаем значение таймера
                player.recharge_timer -= 1
                # Если таймер вышел
                if player.recharge_timer == 0:
                    # восполняем обойму
                    player.ammo = player.clip_size
            # Перезарядка, если кончились патроны
            elif not player.ammo:
                RECHARGE_SOUND.play()
                player.recharge_timer = 120

            # Группа разрушаемых спрайтов
            destructible_groups = pygame.sprite.Group()
            # Группа не разрушаемых спрайтов
            indestructible_groups = pygame.sprite.Group()
            # Группа для определенно взятых спрайтов
            target_group = pygame.sprite.Group()

            # Пробегаемся по чанкам, которые отрисованы и формируем группы
            # спрайтов
            for chunk_idx in chunks_on_screen(
                    camera, player, level_x, level_y
            ):
                destructible_groups.add(chunks[chunk_idx].boxes_group)
                destructible_groups.add(chunks[chunk_idx].enemies_group)
                indestructible_groups.add(chunks[chunk_idx].bricks_group)
                target_group.add(chunks[chunk_idx].bricks_group)
                target_group.add(chunks[chunk_idx].boxes_group)

            virtual_surface.blit(BACKGROUND_IMAGE, (0, 0))
            # Обновляем камеру
            for chunk_idx in chunks_on_screen(
                    camera, player, level_x, level_y
            ):
                # Перемещаем все спрайты
                chunks[chunk_idx].render(
                    virtual_surface, camera, frame, player_group,
                    [SHOT_SOUND, HEAVY_ENEMY_SHOT_SOUND,
                     ARMORED_ENEMY_SHOT_SOUND, MARKSMAN_ENEMY_SHOT_SOUND],
                    bullet_group, target_group, ENEMY_BULLET_IMAGE
                )
            # Обновляем пули
            for bullet in bullet_group:
                # Если вернет True, в случае для уровней с реактором,
                # то работает условие победы на уровне
                if bullet.update(
                        player, destructible_groups,
                        indestructible_groups,
                        [ENEMY_DESTROY_SOUND, BOX_DESTROY_SOUND],
                        [HIT_SOUND, SHIELD_HIT_SOUND],
                        player_group, camera,
                        virtual_surface, COINS_SHEETS, COIN_SELECTION_SOUND,
                        chunks
                ):
                    # Пополняем баланс монет за победу
                    player.coins += LEVELS_REWARD[
                        select_level_menu.current_level
                    ]
                    # Обновляем данные в БД
                    con = sqlite3.connect('DataBase.sqlite')
                    cur = con.cursor()
                    cur.execute(
                        f'UPDATE Player_data SET Coins = {player.coins}'
                    )
                    con.commit()
                    con.close()
                    # Открываем меню победы
                    current_menu, pause, start, running = set_victory_menu()
            # Обновляем таймер щита игрока
            if player.shield_recharge:
                player.shield_recharge -= 1
                # Таймер вышел
                if player.shield_recharge <= 0:
                    # Увеличиваем значение щита на 1
                    player.shield += 1
                    # Запускаем таймер восстановления щита, если их значение
                    # неполное
                    if player.shield != player.max_shield:
                        player.shield_recharge = 150

            # Проверяем хп игрока
            for player in player_group:
                # Хп все потрачено
                if player.hp <= 0:
                    current_menu, pause, start, running = set_endgame_menu()

            # Отрисовка игрока
            player_group.draw(virtual_surface)

            # Проверка коллизии с группой спрайтов в чанке
            player.check_collision_sides(target_group)
            # Проверка направления движения
            if direction == 1:
                # Проверка на коллизию с объектами слева
                if not any(
                        (
                                player.collide_list[4],
                                (
                                        not player.collide_list[7] and
                                        player.collide_list[2]
                                ),
                                (
                                        not player.collide_list[6] and
                                        player.collide_list[0]
                                )
                        )
                ):
                    # Передвижение игрока и анимация движения
                    camera.update(dx=-STEP)
                    if jump_counter:
                        player.current_image_idx = 2
                    elif frame % 5 == 0:
                        player.current_image_idx += 1
                        if player.current_image_idx == len(PLAYER_IMAGES):
                            player.current_image_idx = 0
            elif direction == 2:
                # Проверка на коллизию с объектами справа
                if not any(
                        (
                                player.collide_list[5],
                                (
                                        not player.collide_list[7] and
                                        player.collide_list[3]
                                ),
                                (
                                        not player.collide_list[6] and
                                        player.collide_list[1]
                                )
                        )
                ):
                    # Движение и анимация движения игрока
                    camera.update(dx=STEP)
                    if jump_counter:
                        player.current_image_idx = 2
                    elif frame % 5 == 0:
                        player.current_image_idx += 1
                        if player.current_image_idx == len(PLAYER_IMAGES):
                            player.current_image_idx = 0
            # Индекс изображения игрока сменяется на стоячего
            else:
                player.current_image_idx = 0
            # Прыжок игрока
            if jump_counter:
                jump_counter -= 1
                if not player.collide_list[6]:
                    camera.update(dy=-10)
            elif not player.collide_list[7]:
                if player.collide_list[2]:
                    dx = 1
                elif player.collide_list[3]:
                    dx = -1
                else:
                    dx = 0
                camera.update(dx, 5)
            else:
                on_ground = True
            # Обновить интерфейс
            dashboard.update(player)
            # Отобразить интерфейс
            dashboard.draw(virtual_surface)
            # Смена изображения игрока исходя из направления
            if player.direction == DIRECTION_RIGHT:
                player.image = PLAYER_IMAGES[player.current_image_idx]
            else:
                player.image = pygame.transform.flip(
                    PLAYER_IMAGES[player.current_image_idx], True, False
                )
        # Игра на паузе
        else:
            # Блюр фонового изображения
            virtual_surface.blit(blured_background_image, (0, 0))

    # Надо ли отображать какую-либо менюшку
    if current_menu != LEVEL_MAP:
        # Отображаем текущую менюшку (Вот эти все приколы с *args и
        # **kwargs в файлике menu.py нужны были, чтобы избежать в этой
        # части кода миллиона if-ов, где проверяется, какая именно менюшка
        # сейчас должна быть отображена, поэтому при расширении игры (и то
        # что есть на данный момент), все что касается интерфейса будет тут
        # обрабатываться по аналогичному принципу и ничего в if-ы
        # дописывать уже не нужно будет)
        arrow_idx, result = MENUS[current_menu].draw(
            virtual_surface, CURRENT_LEVEL_MARK_COORDS,
            LEVELS_REWARD, CURRENT_LEVEL_REWARD_COORDS,
            ENEMIES_INFO_COORDS
        )

        # Эта хитрая штука нужна для передачи значений переменных через
        # функции (ликвидация global переменных, в которых происходит
        # изменение из локальной области видимости)
        if result[0] is not None:
            current_menu = result[0]
            pause = result[1]
            start = result[2]
            running = result[3]
            if len(result) > 4:
                player = result[4]
                player_group = result[5]
                level_x = result[6]
                level_y = result[7]
                chunks = result[8]
                camera = result[9]
                dashboard = result[10]
                MENUS[UPGRADE_MENU] = result[11]

    # Координаты курсора мыши
    x, y = pygame.mouse.get_pos()
    # Отрисовка курсора
    if 0 < x < WIDTH and \
            0 < y < HEIGHT:
        draw_arrow(virtual_surface, ARROW_IMAGES[arrow_idx], x, y)
        arrow_idx = 0
    # Изображение приложения в соответствии с заданным размером окна
    scaled_surface = transform.scale(virtual_surface, current_size)
    screen.blit(scaled_surface, (0, 0))
    # Отображение изображения на экран
    pygame.display.flip()
    # Обновление таймера по FPS
    clock.tick(FPS)

    # Обновление кадров
    frame += 1
    if frame % 5 == 0:
        pygame.display.set_caption(f'"Wasteland BETA" FPS: '
                                   f'{round(clock.get_fps())}')
        frame = 0

terminate()
