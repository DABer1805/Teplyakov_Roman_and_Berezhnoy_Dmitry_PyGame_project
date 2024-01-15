import os
import sys
from ctypes import windll
from functools import partial
from typing import Union, Optional

import numpy as np
import pygame
import sqlite3
import win32gui
import win32ui
from PIL import Image, ImageFilter
from pygame import RESIZABLE, transform, VIDEORESIZE

from constants import WIDTH, HEIGHT, FPS, STEP, DIRECTION_LEFT, \
    DIRECTION_RIGHT, BORDER_WIDTH, IMPROVEMENT_SCALE_WIDTH, BULLET_WIDTH, \
    RECHARGE_SCALE_WIDTH, RECHARGE_SCALE_HEIGTH, PLAYER_HEALTH_SCALE_WIDTH, \
    PLAYER_HEALTH_SCALE_HEIGTH, PLAYER_SHIELD_SCALE_WIDTH, \
    PLAYER_SHIELD_SCALE_HEIGTH, RECHARGE_SCALE_BORDER, \
    PLAYER_HEALTH_SCALE_BORDER, PLAYER_SHIELD_SCALE_BORDER, LEVELS_AMOUNT, \
    LEVELS_REWARD

from classes import Player, Camera, Bullet, Button, Chunk, ImprovementScales, \
    ImprovementScale

# Задаём параметры приложения
pygame.init()
pygame.key.set_repeat(200, 70)

screen = pygame.display.set_mode((WIDTH, HEIGHT), RESIZABLE)

virtual_surface = pygame.Surface((WIDTH, HEIGHT))

current_size = screen.get_size()

clock = pygame.time.Clock()

# Прячем родной курсор
pygame.mouse.set_visible(False)

# Грузим фоновую музыку и запускаем её проигрываться
pygame.mixer.music.load("data/sounds/main_saundtrack.mp3")
pygame.mixer.music.play(loops=-1)

# Игрок
player: Optional[Player] = None

bullet_group = pygame.sprite.Group()


def load_image(filename: str) -> pygame.Surface:
    """ Загрузчик изображений

    :param filename: Название изображения, которое загружаем
    :return: Возвращаем загружаемое изображение
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

    :param filename: Название файла, в котором лежит уровень
    :return: Возвращаем уровень в виде списка, где каждый элемент - один
    ряд уровня, где символами обозначены тайлы и противники с игроком
    """

    global player_x, player_y

    # Путь к файлу
    fullname = os.path.join('data', filename)
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
                             level_map)))


def generate_level(level_map):
    """ Генерация уровня """
    global level_x, level_y, player_group
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
    return player, level_x, level_y, chunks


def get_enemies_amount(filename: str):
    # Путь к файлу
    fullname = os.path.join('data', filename)
    # Читаем уровень, убирая символы перевода строки
    with open(fullname, 'r', encoding='utf8') as mapFile:
        level_map = mapFile.read()

    return (level_map.count('o') + level_map.count('O'),
            level_map.count('a') + level_map.count('A'),
            level_map.count('m') + level_map.count('M'),
            level_map.count('h') + level_map.count('H'))


def terminate() -> None:
    """ Закрытие окна игры """
    pygame.quit()
    sys.exit()


def print_text(text: str, pos_x: int, pos_y: int,
               font_color: Union[tuple[int, int, int], str] = (255, 255, 255),
               font_name: str = 'bahnschrift',
               font_size: int = 30, center=False) -> None:
    """ Отрисовка текста на экране

    :param text: Текст, который будет отображён на экране
    :param pos_x: x - координата текста
    :param pos_y: y - координата текста
    :param font_color: Цвет, в который будет окрашен текст
    :param font_name: Название шрифта, который будет использован
    :param font_size: Размер шрифта
    """
    # Выбранный шрифт
    font = pygame.font.SysFont(font_name, font_size)
    text_surface = font.render(text, True, font_color)
    if not center:
        # Отрисовываем на экране выбранный текст
        virtual_surface.blit(text_surface, (pos_x, pos_y))
    else:
        text_rect = text_surface.get_rect(center=(pos_x, pos_y))
        virtual_surface.blit(text_surface, text_rect)


def show_level_info():
    print_text(str(current_level), 58, 57, center=True)
    print_text(str(LEVELS_REWARD[current_level]), 180, 107, font_size=25)
    print_text(str(enemies_amount[0]), 115, 239, font_size=16, center=True)
    print_text(str(enemies_amount[1]), 215, 239, font_size=16, center=True)
    print_text(str(enemies_amount[2]), 115, 290, font_size=16, center=True)
    print_text(str(enemies_amount[3]), 215, 290, font_size=16, center=True)


def show_dashboard(ammo: int, coins: int) -> None:
    """ Отрисовка всех полосочек с характеристиками персонажа (hp, щиты и
    кол-во оставшихся пуль в магазине), а также счётчика монет

    :param ammo: Сколько пуль у игрока в данный момент
    :param coins: Количество монет у игрока в данный момент
    """
    # Отрисовываем картинку для счётчика пуль
    virtual_surface.blit(AMMO_COUNTER_IMAGE, (10, 10))
    # Отрисовываем картинку для счётчика монет
    virtual_surface.blit(COIN_COUNTER_IMAGE, (600, 10))
    # Отрисовываем картинку для счётчика HP
    virtual_surface.blit(HP_COUNTER_IMAGE, (15, 70))
    # Отрисовываем картинку для счётчика щита
    virtual_surface.blit(SHIELD_COUNTER_IMAGE, (18, 111))
    pygame.draw.rect(
        virtual_surface, '#2b2b2b', pygame.Rect(
            110, 32, RECHARGE_SCALE_WIDTH,
            RECHARGE_SCALE_HEIGTH
        )
    )
    pygame.draw.rect(
        virtual_surface, '#048c73', pygame.Rect(
            110 + RECHARGE_SCALE_BORDER, 32 + RECHARGE_SCALE_BORDER,
            RECHARGE_SCALE_WIDTH * (player.ammo / player.clip_size) -
            RECHARGE_SCALE_BORDER * 2,
            RECHARGE_SCALE_HEIGTH - RECHARGE_SCALE_BORDER * 2
        )
    )
    pygame.draw.rect(
        virtual_surface, '#aff7f5', pygame.Rect(
            110 + RECHARGE_SCALE_BORDER * 2, 32 + RECHARGE_SCALE_BORDER * 2,
            RECHARGE_SCALE_WIDTH * (player.ammo / player.clip_size) -
            RECHARGE_SCALE_BORDER * 4,
            RECHARGE_SCALE_HEIGTH - RECHARGE_SCALE_BORDER * 4
        )
    )
    pygame.draw.rect(
        virtual_surface, '#2b2b2b', pygame.Rect(
            52, 75, PLAYER_HEALTH_SCALE_WIDTH,
            PLAYER_HEALTH_SCALE_HEIGTH
        )
    )
    pygame.draw.rect(
        virtual_surface, '#88001b', pygame.Rect(
            52 + PLAYER_HEALTH_SCALE_BORDER, 75 + PLAYER_HEALTH_SCALE_BORDER,
            PLAYER_HEALTH_SCALE_WIDTH * (player.hp / player.max_hp)
            - PLAYER_HEALTH_SCALE_BORDER * 2,
            PLAYER_HEALTH_SCALE_HEIGTH - PLAYER_HEALTH_SCALE_BORDER * 2
        )
    )
    pygame.draw.rect(
        virtual_surface, '#cd3030', pygame.Rect(
            52 + PLAYER_HEALTH_SCALE_BORDER * 2,
            75 + PLAYER_HEALTH_SCALE_BORDER * 2,
            PLAYER_HEALTH_SCALE_WIDTH * (player.hp / player.max_hp)
            - PLAYER_HEALTH_SCALE_BORDER * 4,
            PLAYER_HEALTH_SCALE_HEIGTH - PLAYER_HEALTH_SCALE_BORDER * 4
        )
    )
    pygame.draw.rect(
        virtual_surface, '#2b2b2b', pygame.Rect(
            52, 118, PLAYER_SHIELD_SCALE_WIDTH,
            PLAYER_SHIELD_SCALE_HEIGTH
        )
    )
    pygame.draw.rect(
        virtual_surface, '#00a8f3', pygame.Rect(
            52 + PLAYER_SHIELD_SCALE_BORDER,
            118 + PLAYER_SHIELD_SCALE_BORDER,
            PLAYER_HEALTH_SCALE_WIDTH * (player.shield / player.max_shield) -
            PLAYER_SHIELD_SCALE_BORDER * 2,
            PLAYER_HEALTH_SCALE_HEIGTH - PLAYER_SHIELD_SCALE_BORDER * 2
        )
    )
    pygame.draw.rect(
        virtual_surface, '#8cfffb', pygame.Rect(
            52 + PLAYER_SHIELD_SCALE_BORDER * 2,
            118 + PLAYER_SHIELD_SCALE_BORDER * 2,
            PLAYER_HEALTH_SCALE_WIDTH * (player.shield / player.max_shield)
            - PLAYER_SHIELD_SCALE_BORDER * 4,
            PLAYER_HEALTH_SCALE_HEIGTH - PLAYER_SHIELD_SCALE_BORDER * 4
        )
    )
    # Отрисовываем количество монет у игрока
    print_text(str(coins), 650, 10, "white", font_size=30)


def pil_image_to_surface(pil_image: Image) -> pygame.Surface:
    """ Преобразователь PIL картинки в поверхность PyGame

    :param pil_image: PIL картинка, которую необходимо преобразовать
    :return: Возвращает поверхность (нужно, чтобы PyGame мог работать с
    данной картинкой)
    """

    return pygame.image.fromstring(
        pil_image.tobytes(), pil_image.size, pil_image.mode
    ).convert()


def get_screenshot() -> pygame.Surface:
    """ Функция для получения заблюренного скриншота экрана с игрой,
    чтобы потом использовать его для меню паузы

    :return: Возвращаем заблюренный скриншот экрана с игрой и
    подготавливаем его для размещения на экране
    """
    window = win32gui.FindWindow(None, pygame.display.get_caption()[0])

    left, top, right, bot = win32gui.GetWindowRect(window)
    width = right - left
    height = bot - top

    hwnd_DC = win32gui.GetWindowDC(window)
    mfc_DC = win32ui.CreateDCFromHandle(hwnd_DC)
    save_DC = mfc_DC.CreateCompatibleDC()

    save_bit_map = win32ui.CreateBitmap()
    save_bit_map.CreateCompatibleBitmap(mfc_DC, width, height)

    save_DC.SelectObject(save_bit_map)
    windll.user32.PrintWindow(window, save_DC.GetSafeHdc(), 1)

    bmp_info = save_bit_map.GetInfo()
    bmp_str = save_bit_map.GetBitmapBits(True)

    im = Image.frombuffer(
        'RGB',
        (bmp_info['bmWidth'], bmp_info['bmHeight']),
        bmp_str, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(save_bit_map.GetHandle())
    save_DC.DeleteDC()
    mfc_DC.DeleteDC()
    win32gui.ReleaseDC(window, hwnd_DC)

    return pil_image_to_surface(
        im.filter(ImageFilter.GaussianBlur(radius=5))
    )


icon = load_image('icon.png')
pygame.display.set_icon(icon)

# Изображение активной кнопки продолжения игры
ACTIVE_CONTINUE_BUTTON_IMAGE = load_image('active_continue_button_image.png')
# Изображение неактивной кнопки продолжения игры
INACTIVE_CONTINUE_BUTTON_IMAGE = load_image(
    'inactive_continue_button_image.png'
)
# Изображение активной кнопки выбора уровня
ACTIVE_SELECT_LEVEL_BUTTON_IMAGE = load_image(
    'active_select_level_button.png'
)
# Изображение активной кнопки выбора уровня
INACTIVE_SELECT_LEVEL_BUTTON_IMAGE = load_image(
    'inactive_select_level_button.png'
)
# Изображение активной кнопки продолжения игры
ACTIVE_CHARACTERISTICS_BUTTON_IMAGE = load_image(
    'active_characteristics_button_image.png'
)
# Изображение неактивной кнопки возврата на выбор уровня
INACTIVE_RETURN_BUTTON_IMAGE = load_image(
    'inactive_return_button_image.png'
)
# Изображение активной кнопки возврата на выбор уровня
ACTIVE_RETURN_BUTTON_IMAGE = load_image(
    'active_return_button_image.png'
)
# Изображение неактивной кнопки возврата на выбор уровня
INACTIVE_SMALL_RETURN_BUTTON_IMAGE = load_image(
    'inactive_small_return_button_image.png'
)
# Изображение активной кнопки возврата на выбор уровня
ACTIVE_SMALL_RETURN_BUTTON_IMAGE = load_image(
    'active_small_return_button_image.png'
)
# Изображение неактивной кнопки продолжения игры
INACTIVE_CHARACTERISTICS_BUTTON_IMAGE = load_image(
    'inactive_characteristics_button_image.png'
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
ACTIVE_EXIT_BUTTON_IMAGE = load_image(
    'active_exit_button_image.png'
)
# Изображение неактивной кнопки сдвига меню характеристики вправо
INACTIVE_EXIT_BUTTON_IMAGE = load_image(
    'inactive_exit_button_image.png'
)
# Изображение активной кнопки сдвига меню характеристики вправо
ACTIVE_LEFT_SHIFT_BUTTON_IMAGE = load_image(
    'active_left_shift_button_button_image.png'
)
# Изображение неактивной кнопки сдвига меню характеристики вправо
INACTIVE_LEFT_SHIFT_BUTTON_IMAGE = load_image(
    'inactive_left_shift_button_button_image.png'
)
# Изображение активной кнопки начала игры
ACTIVE_START_BUTTON_IMAGE = load_image(
    'active_start_button_image.png'
)
# Изображение неактивной кнопки начала игры
INACTIVE_START_BUTTON_IMAGE = load_image(
    'inactive_start_button_image.png'
)
# Изображение активной кнопки магазина скинов
ACTIVE_SKINS_BUTTON_IMAGE = load_image('active_skins_button_image.png')
# Изображение неактивной кнопки магазина скинов
INACTIVE_SKINS_BUTTON_IMAGE = load_image('inactive_skins_button_image.png')
# Изображение активной кнопки руководства
ACTIVE_GUIDE_BUTTON_IMAGE = load_image('active_guide_button_image.png')
# Изображение неактивной кнопки руководства
INACTIVE_GUIDE_BUTTON_IMAGE = load_image('inactive_guide_button_image.png')
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

# ===== Изображения =====
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
COIN_SELECTION_SOUND = pygame.mixer.Sound("data/sounds/coin_selection.wav")
# Звук выстрела
SHOT_SOUND = pygame.mixer.Sound("data/sounds/shot_sound.wav")
# Звук выстрела тяжика (звуки выстрела минигана)
HEAVY_ENEMY_SHOT_SOUND = pygame.mixer.Sound(
    "data/sounds/heavy_enemy_shot_sound.wav"
)
ARMORED_ENEMY_SHOT_SOUND = pygame.mixer.Sound(
    "data/sounds/armored_enemy_shot_sound.wav"
)
MARKSMAN_ENEMY_SHOT_SOUND = pygame.mixer.Sound(
    "data/sounds/marksman_enemy_shot_sound.wav"
)
# Звук перезарядки
RECHARGE_SOUND = pygame.mixer.Sound("data/sounds/recharge_sound.wav")
# Звук разрушения коробки
BOX_DESTROY_SOUND = pygame.mixer.Sound("data/sounds/box_destroy_sound.wav")
ENEMY_DESTROY_SOUND = pygame.mixer.Sound(
    "data/sounds/enemy_destroy_sound.wav")
# Звук попадания в препятствие
HIT_SOUND = pygame.mixer.Sound("data/sounds/hit_sound.wav")
SHIELD_HIT_SOUND = pygame.mixer.Sound("data/sounds/shield_hit_sound.wav")
# Задний фон
BACKGROUND_IMAGE = load_image('background_image.jpg')
# Задний фон в меню паузы
PAUSE_BACKGROUND = load_image('pause_background_image.png')
# Заданий фон для панельки с выбором характеристик
CHARACTERISTICS_BACKGROUND = load_image(
    'characteristics_background_image.png'
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

# ===== Звуки =====
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

CHARACTERISTICS_BUTTONS_SETTINGS = (
    HEIGHT // 2 + 15, HEIGHT // 2 + 64, HEIGHT // 2 + 111
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
current_menu = 0

blured_background_image = None

current_characteristics_target = 'ak-47'

current_characteristics_target_idx = 0

start = False
camera = False
con = None

hp_damage_timer = 0
shield_damage_timer = 0

chunks = []


def start_game():
    global player, start, chunks, camera
    # Игрок, размер уровня в ширину и в высоту
    player, level_x, level_y, chunks = generate_level(
        load_level(f'level_{current_level}.txt')
    )
    camera = Camera(player)
    player.rect.x += camera.dx
    player.rect.y += camera.dy
    start = True
    buttons.clear()


def open_endgame_menu():
    global start, current_menu
    buttons.append(Button(
        151, 31, 324, 270,
        ACTIVE_BUTTON_IMAGE,
        INACTIVE_BUTTON_IMAGE,
        'Выбор уровня', select_level
    ))
    current_menu = 4
    start = False


def open_victory_menu():
    global start, current_menu
    buttons.append(Button(
        151, 31, 324, 270,
        ACTIVE_BUTTON_IMAGE,
        INACTIVE_BUTTON_IMAGE,
        'Выбор уровня', select_level
    ))
    current_menu = 5
    start = False


def return_to_pause_menu():
    global current_menu, pause
    del buttons[-3:]
    if con is not None:
        con.close()
    buttons.append(Button(
        151, 31, WIDTH // 2 - 78, HEIGHT // 2 - 32,
        ACTIVE_BUTTON_IMAGE,
        INACTIVE_BUTTON_IMAGE,
        'Продолжить', continue_game
    ))
    buttons.append(Button(
        151, 31, WIDTH // 2 - 78, HEIGHT // 2 + 16,
        ACTIVE_BUTTON_IMAGE,
        INACTIVE_BUTTON_IMAGE,
        'Улучшение', open_characteristics_menu
    ))
    buttons.append(Button(
        151, 31, WIDTH // 2 - 78, 266,
        ACTIVE_BUTTON_IMAGE,
        INACTIVE_BUTTON_IMAGE,
        'Выбор уровня', select_level
    ))
    current_menu = 2
    pause = True


def return_to_main_menu():
    global buttons, current_menu, pause, current_menu
    del buttons[-2:]
    buttons = [
        Button(
            151, 31, 70, 120,
            ACTIVE_BUTTON_IMAGE,
            INACTIVE_BUTTON_IMAGE,
            'Начать', select_level
        ),
        Button(
            151, 31, 70, 180,
            ACTIVE_BUTTON_IMAGE,
            INACTIVE_BUTTON_IMAGE,
            'Руководство', lambda: print('Руководство')
        ),
        Button(
            151, 31, 70, 240,
            ACTIVE_BUTTON_IMAGE,
            INACTIVE_BUTTON_IMAGE,
            'Выход', quit
        )
    ]
    current_menu = 0


def open_characteristics_menu():
    global buttons, current_menu, improvement_scales, con
    del buttons[-3:]
    con = sqlite3.connect('DataBase.sqlite')
    cur = con.cursor()
    cur.execute(
        f'UPDATE Player_data '
        f'SET Coins = {player.coins}'
    )
    improvement_scales = {
        'ak-47': ImprovementScales(
            [
                ImprovementScale(337, 220, IMPROVEMENT_SCALE_WIDTH,
                                 12, BORDER_WIDTH, 'Shot_delay',
                                 cur),
                ImprovementScale(337, 269, IMPROVEMENT_SCALE_WIDTH,
                                 12, BORDER_WIDTH, 'Damage',
                                 cur),
                ImprovementScale(337, 316, IMPROVEMENT_SCALE_WIDTH,
                                 12, BORDER_WIDTH, 'Ammo', cur)
            ],
            ACTIVE_UPGRADE_BUTTON_IMAGE, INACTIVE_UPGRADE_BUTTON_IMAGE,
            player, cur, con, UPGRADE_SOUND
        ),
        'player': ImprovementScales(
            [
                ImprovementScale(337, 220, IMPROVEMENT_SCALE_WIDTH,
                                 12, BORDER_WIDTH, 'HP', cur),
                ImprovementScale(337, 269, IMPROVEMENT_SCALE_WIDTH,
                                 12, BORDER_WIDTH, 'Shields',
                                 cur)
            ], ACTIVE_UPGRADE_BUTTON_IMAGE, INACTIVE_UPGRADE_BUTTON_IMAGE,
            player, cur, con, UPGRADE_SOUND
        )
    }
    current_menu = 1
    buttons.append(Button(
        21, 21, 267, 97,
        ACTIVE_SMALL_RETURN_BUTTON_IMAGE,
        INACTIVE_SMALL_RETURN_BUTTON_IMAGE,
        '', return_to_pause_menu
    ))
    buttons.append(Button(
        21, 21, WIDTH // 2 + 103, 222,
        ACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
        INACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
        '', partial(shift_characteristics_idx, 1)
    ))
    buttons.append(Button(
        21, 21, WIDTH // 2 - 135, 222,
        ACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
        INACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
        '', partial(shift_characteristics_idx, 0)
    ))


def shift_characteristics_idx(direction):
    global current_characteristics_target_idx, current_characteristics_target
    for button in improvement_scales[
        current_characteristics_target
    ].upgrade_buttons:
        button.is_visible = False
    if direction == 0:
        current_characteristics_target_idx -= 1
        if current_characteristics_target_idx < 0:
            current_characteristics_target_idx = len(improvement_scales) - 1
    else:
        current_characteristics_target_idx += 1
        if current_characteristics_target_idx > len(improvement_scales) - 1:
            current_characteristics_target_idx = 0
    current_characteristics_target = list(improvement_scales.keys())[
        current_characteristics_target_idx
    ]
    for index, button in enumerate(improvement_scales[
                                       current_characteristics_target
                                   ].upgrade_buttons):
        if improvement_scales[
            current_characteristics_target
        ].scale_objects[index].current_cost != 'max':
            button.is_visible = True


def continue_game():
    global pause
    PAUSE_STOP_SOUND.play(loops=-1)
    del buttons[-3:]
    pygame.mixer.music.pause()
    pygame.mixer.music.load(
        "data/sounds/main_saundtrack.mp3"
    )
    pygame.mixer.music.play(loops=-1)
    if pause:
        pause = False


def draw_arrow(screen, image, x, y):
    screen.blit(image, (x, y))


def quit():
    global running
    running = False


def chunks_on_screen():
    global camera, player
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


current_level = 1
enemies_amount = get_enemies_amount(f'level_{current_level}.txt')


def update_level_info(button_number):
    global current_level, enemies_amount
    current_level = button_number
    enemies_amount = get_enemies_amount(f'level_{current_level}.txt')


def select_level():
    global current_menu, buttons, pause, start, player
    pause, start = False, False
    if player is not None:
        # Подключаемся к базе данных
        con = sqlite3.connect('DataBase.sqlite')
        cur = con.cursor()
        cur.execute(
            f'UPDATE Player_data '
            f'SET Coins = {player.coins}'
        )
        con.commit()
        con.close()
    buttons.clear()
    buttons.append(
        Button(
            151, 31, 70, 322,
            ACTIVE_BUTTON_IMAGE,
            INACTIVE_BUTTON_IMAGE,
            'Играть', start_game
        )
    )
    buttons.append(
        Button(
            28, 28, 41, 327,
            ACTIVE_SMALL_RETURN_BUTTON_IMAGE,
            INACTIVE_SMALL_RETURN_BUTTON_IMAGE,
            '', return_to_main_menu
        )
    )
    cur_level_amount = LEVELS_AMOUNT
    for x in range(LEVELS_AMOUNT // 3 + 1):
        for y in range(min(cur_level_amount, 3)):
            button_number = x * 3 + y + 1
            buttons.append(
                Button(
                    47, 45, 440 + 63 * y, 125 + 61 * x,
                    ACTIVE_SELECT_LEVEL_BUTTON_IMAGE,
                    INACTIVE_SELECT_LEVEL_BUTTON_IMAGE,
                    str(button_number), partial(update_level_info,
                                                button_number), font_size=30
                )
            )
        cur_level_amount -= 3
    current_menu = 3


buttons = []
return_to_main_menu()

frame = 0
direction = 0
on_ground = True

# Игровой цикл
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == VIDEORESIZE:
            current_size = event.size
        if start and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if on_ground:
                    jump_counter = 20
                    on_ground = False
            if event.key == pygame.K_a:
                direction = 1
                player.direction = DIRECTION_LEFT
            if event.key == pygame.K_d:
                direction = 2
                player.direction = DIRECTION_RIGHT
            if event.key == pygame.K_ESCAPE:
                pause = not pause
                if pause:
                    blured_background_image = get_screenshot()
                    return_to_pause_menu()
                else:
                    PAUSE_STOP_SOUND.play()

                    if current_menu == 1:
                        return_to_pause_menu()
                    elif current_menu == 2:
                        continue_game()
        if start and event.type == pygame.KEYUP:
            if event.key == pygame.K_a or event.key == pygame.K_d:
                direction = 0
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                button_pushed = True
            elif event.button == 3:
                if player.ammo != player.clip_size:
                    player.ammo = 0
                    RECHARGE_SOUND.play()
                    player.recharge_timer = 120
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                button_pushed = False
    if start:
        if not pause:
            if not player.timer:
                if button_pushed and player.ammo:
                    player.ammo -= 1
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
            else:
                player.timer -= 1

            if player.recharge_timer:
                player.recharge_timer -= 1
                if player.recharge_timer == 0:
                    player.ammo = player.clip_size
            elif not player.ammo:
                RECHARGE_SOUND.play()
                player.recharge_timer = 120

            destructible_groups = pygame.sprite.Group()
            indestructible_groups = pygame.sprite.Group()

            target_group = pygame.sprite.Group()

            for chunk_idx in chunks_on_screen():
                destructible_groups.add(chunks[chunk_idx].boxes_group)
                destructible_groups.add(chunks[chunk_idx].enemies_group)
                indestructible_groups.add(chunks[chunk_idx].bricks_group)
                target_group.add(chunks[chunk_idx].bricks_group)
                target_group.add(chunks[chunk_idx].boxes_group)

            virtual_surface.blit(BACKGROUND_IMAGE, (0, 0))
            # Обновляем камеру
            for chunk_idx in chunks_on_screen():
                # Перемещаем все спрайты
                chunks[chunk_idx].render(
                    virtual_surface, camera, frame, player_group,
                    [SHOT_SOUND, HEAVY_ENEMY_SHOT_SOUND,
                     ARMORED_ENEMY_SHOT_SOUND, MARKSMAN_ENEMY_SHOT_SOUND],
                    bullet_group, target_group, ENEMY_BULLET_IMAGE
                )

            for bullet in bullet_group:
                if bullet.update(
                        player,
                        destructible_groups,
                        indestructible_groups,
                        [ENEMY_DESTROY_SOUND, BOX_DESTROY_SOUND],
                        [HIT_SOUND, SHIELD_HIT_SOUND],
                        player_group, camera,
                        virtual_surface, COINS_SHEETS, COIN_SELECTION_SOUND,
                        chunks
                ):
                    player.coins += LEVELS_REWARD[current_level]
                    con = sqlite3.connect('DataBase.sqlite')
                    cur = con.cursor()
                    cur.execute(
                        f'UPDATE Player_data '
                        f'SET Coins = {player.coins}'
                    )
                    con.close()
                    open_victory_menu()
            # Обновляем таймер щита игрока
            if player.shield_recharge:
                player.shield_recharge -= 1
                if player.shield_recharge <= 0:
                    player.shield += 1
                    if player.shield != player.max_shield:
                        player.shield_recharge = 150

            # Проверяем хп игрока
            for player in player_group:
                if player.hp <= 0:
                    open_endgame_menu()

            player_group.draw(virtual_surface)

            player.check_collision_sides(target_group)
            if direction == 1:
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
                    camera.update(dx=-STEP)
                    if jump_counter:
                        player.current_image_idx = 2
                    elif frame % 5 == 0:
                        player.current_image_idx += 1
                        if player.current_image_idx == len(PLAYER_IMAGES):
                            player.current_image_idx = 0
            elif direction == 2:
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
                    camera.update(dx=STEP)
                    if jump_counter:
                        player.current_image_idx = 2
                    elif frame % 5 == 0:
                        player.current_image_idx += 1
                        if player.current_image_idx == len(PLAYER_IMAGES):
                            player.current_image_idx = 0
            else:
                player.current_image_idx = 0
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
            show_dashboard(player.ammo, player.coins)
            if player.direction == DIRECTION_RIGHT:
                player.image = PLAYER_IMAGES[player.current_image_idx]
            else:
                player.image = pygame.transform.flip(
                    PLAYER_IMAGES[player.current_image_idx], True, False
                )
        else:
            virtual_surface.blit(blured_background_image, (0, 0))
            if current_menu == 1:
                virtual_surface.blit(CHARACTERISTICS_BACKGROUND, (0, 0))
                virtual_surface.blit(CHARACTERISTICS_IMAGES[
                                         current_characteristics_target_idx
                                     ], (300, 91))
                for index, improvement_scale in enumerate(
                        improvement_scales[
                            current_characteristics_target
                        ].scale_objects
                ):
                    pygame.draw.rect(
                        virtual_surface, '#d19900',
                        improvement_scale.external_rect
                    )
                    pygame.draw.rect(
                        virtual_surface, '#fff200',
                        improvement_scale.internal_rect
                    )
                    print_text(
                        improvement_scale.current_cost,
                        313, 220 + index * 48, font_size=9
                    )
                for button in improvement_scales[
                    current_characteristics_target
                ].upgrade_buttons:
                    cur_idx = button.draw(virtual_surface)
                    if cur_idx:
                        arrow_idx = cur_idx
            elif current_menu == 2:
                virtual_surface.blit(PAUSE_BACKGROUND, (0, 0))
    else:
        if current_menu == 0:
            virtual_surface.blit(MAIN_MENU_IMAGE, (0, 0))
        elif current_menu == 3:
            virtual_surface.blit(SELECT_LEVEL_MENU_IMAGE, (0, 0))
            show_level_info()
        elif current_menu == 4:
            virtual_surface.blit(ENDGAME_MENU_IMAGE, (0, 0))
        elif current_menu == 5:
            virtual_surface.blit(VICTORY_MENU_IMAGE, (0, 0))

    for button in buttons:
        cur_idx = button.draw(virtual_surface)
        if cur_idx:
            arrow_idx = cur_idx

    x, y = pygame.mouse.get_pos()
    if 0 < x < WIDTH and \
            0 < y < HEIGHT:
        draw_arrow(virtual_surface, ARROW_IMAGES[arrow_idx], x, y)
        arrow_idx = 0

    scaled_surface = transform.scale(virtual_surface, current_size)
    screen.blit(scaled_surface, (0, 0))

    pygame.display.flip()
    clock.tick(FPS)

    frame += 1
    if frame % 5 == 0:
        pygame.display.set_caption(f'"Wasteland" FPS: '
                                   f'{round(clock.get_fps())}')
        frame = 0

terminate()
