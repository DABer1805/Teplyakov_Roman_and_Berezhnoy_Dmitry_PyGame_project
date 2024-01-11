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
from pygame import Rect

from constants import WIDTH, HEIGHT, FPS, STEP, DIRECTION_LEFT, \
    DIRECTION_RIGHT, BORDER_WIDTH, IMPROVEMENT_SCALE_WIDTH, BULLET_WIDTH

from classes import Player, Enemy, Wall, Box, Camera, Bullet, Button, Ray, \
    PhantomTile, Chunk

# Подключаемся к базе данных
con = sqlite3.connect('DataBase.sqlite')
cur = con.cursor()

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
pygame.mixer.music.play()

# Игрок
player: Optional[Player] = None

player_group = pygame.sprite.Group()
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

    # Путь к файлу
    fullname = os.path.join('data', filename)
    # Читаем уровень, убирая символы перевода строки
    with open(fullname, 'r') as mapFile:
        level_map = [line.strip() for line in mapFile]

    # И подсчитываем максимальную длину
    max_width = max(map(len, level_map))

    # Дополняем каждую строку пустыми клетками ('.')
    level_map = list(map(lambda x: x.ljust(max_width, '.'), level_map))
    return np.array(list(map(lambda x: [''.join(i) for i in grouper(x, 8)],
                             level_map)))


def generate_level(level_map):
    """ Генерация уровня """
    global level_x, level_y
    chunks = []
    player = Player((player_group,), PLAYER_IMAGE, 9, 12)
    level_x, level_y = 7, 3
    for y1 in range(level_y):
        for x1 in range(level_x):
            chunks.append(Chunk(
                TILE_IMAGES, ENEMY_IMAGES, x1, y1,
                level_map[y1 * 8:(y1 + 1) * 8, x1:x1 + 1]
            ))
    return player, level_x, level_y, chunks


def terminate() -> None:
    """ Закрытие окна игры """
    pygame.quit()
    sys.exit()


def print_text(text: str, pos_x: int, pos_y: int,
               font_color: Union[tuple[int, int, int], str] = (255, 255, 255),
               font_name: str = 'bahnschrift',
               font_size: int = 30) -> None:
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
    # Отрисовываем на экране выбранный текст
    virtual_surface.blit(font.render(text, True, font_color), (pos_x, pos_y),)


def show_dashboard(ammo: int, coins: int) -> None:
    """ Отрисовка всех полосочек с характеристиками персонажа (hp, щиты и
    кол-во оставшихся пуль в магазине), а также счётчика монет

    :param ammo: Сколько пуль у игрока в данный момент
    :param coins: Количество монет у игрока в данный момент
    """
    # Отрисовываем картинку для счётчика пуль
    virtual_surface.blit(AMMO_COUNTER_IMAGE, (10, 10))
    # Отрисовываем картинку для счётчика монет
    virtual_surface.blit(COIN_COUNTER_IMAGE, (650, 10))
    # Отрисовываем количество пуль у игрока
    print_text(str(ammo) if ammo else '-', 112 if ammo > 9 else 115, 30,
               "white", font_size=18)
    # Отрисовываем количество монет у игрока
    print_text(str(coins), 700, 5, "gray30", font_size=40)


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


# Изображение активной кнопки продолжения игры
ACTIVE_CONTINUE_BUTTON_IMAGE = load_image('active_continue_button_image.png')
# Изображение неактивной кнопки продолжения игры
INACTIVE_CONTINUE_BUTTON_IMAGE = load_image(
    'inactive_continue_button_image.png'
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
}

# ===== Изображения =====
# Изображение главного меню игры
MAIN_MENU_IMAGE = load_image('main_menu_image.png')
# Задний фон для экрана с выбором уровня
SELECT_LEVEL_MENU_IMAGE = load_image('select_level_menu_image.png')
# Изображение игрока
PLAYER_IMAGE = load_image('artur.png')
# Изображение пули
BULLET_IMAGE = load_image('bullet.png')
# Изображения врагов
ENEMY_IMAGES = [
    load_image('ordinary_enemy_image.png'),
    load_image('heavy_enemy.png'),
    load_image('armored_enemy.png'),
    load_image('marksman_enemy.png')
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
ENEMY_DESTROY_SOUND = pygame.mixer.Sound("data/sounds/enemy_destroy_sound.wav")
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
COINS_SHEET = load_image('copper_coins_sheet8x1.png')
# Счетчик снарядов в обойме
AMMO_COUNTER_IMAGE = load_image('ammo_counter.png')
# Счетчик монеток
COIN_COUNTER_IMAGE = load_image('coin_counter.png')
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

# COINS_DATA = {
#     'sheet': COINS_SHEET, 'columns': 8, 'rows': 1, 'percent': 50,
#     'coins_group': coins_group, 'all_sprites': all_sprites
# }

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

# Монетки игрока
coins = cur.execute("SELECT Coins FROM Player_data").fetchone()[0]

# Урон игрока
player_damage = cur.execute("SELECT Damage FROM Player_data").fetchone()[0]

# Нажата ли кнопка стрельбы
button_pushed = False

# Индекс текущего изображения курсора
arrow_idx = 0

# Задержка между выстрелами
shot_delay = 0

# Стоит ли игра на паузе
pause = False

# Текущий экран
current_menu = 0

improvement_scales = {
    'ak-47': [
        [
            [
                pygame.Rect(settings[0], settings[1], settings[2],
                            settings[3]),
                pygame.Rect(settings[4], settings[5], settings[6],
                            settings[7]),
                0, 0
            ] for settings in (
                (337, 220, 0, 12, 337 + BORDER_WIDTH, 220 + BORDER_WIDTH, 0,
                 12 - BORDER_WIDTH * 2, 0),
                (337, 269, 0, 12, 337 + BORDER_WIDTH, 269 + BORDER_WIDTH, 0,
                 12 - BORDER_WIDTH * 2, 0),
                (337, 316, 0, 12, 337 + BORDER_WIDTH, 269 + BORDER_WIDTH, 0,
                 12 - BORDER_WIDTH * 2, 0)
            )
        ], [False, False, False], [
            [10, 45, 100, 250, 500, 'max'],
            [10, 60, 150, 300, 600, 'max'],
            [10, 45, 100, 250, 500, 'max']
        ],
        [
            lambda: print('Увеличение скорости стрельбы'),
            lambda: print('Увеличение урона'),
            lambda: print('Увеличение объёма магазина')
        ]
    ],
    'player': [
        [
            [
                pygame.Rect(settings[0], settings[1], settings[2],
                            settings[3]),
                pygame.Rect(settings[4], settings[5], settings[6],
                            settings[7]),
                0, 0
            ] for settings in (
                (337, 220, 0, 12, 337 + BORDER_WIDTH, 220 + BORDER_WIDTH, 0,
                 12 - BORDER_WIDTH * 2, 0),
                (337, 269, 0, 12, 337 + BORDER_WIDTH, 269 + 69 + BORDER_WIDTH,
                 0, 12 - BORDER_WIDTH * 2, 0)
            )
        ], [False, False, True], [
            [10, 45, 100, 250, 500, 'max'],
            [10, 45, 100, 250, 500, 'max']
        ],
        [
            lambda: print('Увеличение запаса здоровья'),
            lambda: print('Улучшение щита')
        ]
    ]
}

# Значения для увеличения характеристик и имена колонок в БД
improvement_values = {
    'ak-47': (('Shot_delay', 3), ('Damage', 0.5), ('Ammo', 2)),
    'player': (('HP', 1), ('Shields', 1))
}

blured_background_image = None

current_characteristics_target = 'ak-47'

current_characteristics_target_idx = 0

start = False
camera = False

chunks = []


def start_game():
    global player, start, chunks, camera
    # Игрок, размер уровня в ширину и в высоту
    player, level_x, level_y, chunks = generate_level(
        load_level('level_1.txt')
    )
    camera = Camera(player)
    player.rect.x += camera.dx
    player.rect.y += camera.dy
    start = True
    buttons.clear()


def return_to_pause_menu():
    global current_menu, pause
    del buttons[-6:]
    buttons.append(Button(
        152, 38, WIDTH // 2 - 78, HEIGHT // 2 - 32,
        ACTIVE_CONTINUE_BUTTON_IMAGE,
        INACTIVE_CONTINUE_BUTTON_IMAGE,
        'continue_button', continue_game
    ))
    buttons.append(Button(
        152, 38, WIDTH // 2 - 78, HEIGHT // 2 + 16,
        ACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
        INACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
        'characteristics_button', open_characteristics_menu
    ))
    buttons.append(Button(
        152, 38, WIDTH // 2 - 78, 266,
        ACTIVE_RETURN_BUTTON_IMAGE,
        INACTIVE_RETURN_BUTTON_IMAGE,
        'return_button', select_level
    ))
    current_menu = 2
    pause = True


def return_to_main_menu():
    global buttons, current_menu, pause, current_menu
    del buttons[-2:]
    buttons = [
        Button(
            151, 31, 70, 60,
            ACTIVE_START_BUTTON_IMAGE,
            INACTIVE_START_BUTTON_IMAGE,
            'start_button', select_level
        ),
        Button(
            151, 31, 70, 120,
            ACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
            INACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
            'chracteristics_button', lambda: print('Улучшение')
        ),
        Button(
            151, 31, 70, 180,
            ACTIVE_SKINS_BUTTON_IMAGE,
            INACTIVE_SKINS_BUTTON_IMAGE,
            'skins_button', lambda: print('Скины')
        ),
        Button(
            151, 31, 70, 240,
            ACTIVE_GUIDE_BUTTON_IMAGE,
            INACTIVE_GUIDE_BUTTON_IMAGE,
            'chracteristics_button', lambda: print('Руководство')
        ),
        Button(
            151, 31, 70, 300,
            ACTIVE_EXIT_BUTTON_IMAGE,
            INACTIVE_EXIT_BUTTON_IMAGE,
            'chracteristics_button', quit
        )
    ]
    current_menu = 0


def open_characteristics_menu():
    global current_background_image, buttons, current_menu
    del buttons[-3:]
    current_menu = 1
    buttons.append(Button(
        21, 21, 267, 97,
        ACTIVE_SMALL_RETURN_BUTTON_IMAGE,
        INACTIVE_SMALL_RETURN_BUTTON_IMAGE,
        f'return_to_pause_menu_button', return_to_pause_menu
    ))
    buttons.append(Button(
        21, 21, WIDTH // 2 + 103, 222,
        ACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
        INACTIVE_RIGHT_SHIFT_BUTTON_IMAGE,
        f'right_shift_button', partial(shift_characteristics_idx, 1)
    ))
    buttons.append(Button(
        21, 21, WIDTH // 2 - 135, 222,
        ACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
        INACTIVE_LEFT_SHIFT_BUTTON_IMAGE,
        f'left_shift_button', partial(shift_characteristics_idx, 0)
    ))
    for idx in range(len(
            improvement_scales[current_characteristics_target][0])
    ):
        buttons.append(Button(
            21, 21, WIDTH // 2 + 72, CHARACTERISTICS_BUTTONS_SETTINGS[idx],
            ACTIVE_UPGRADE_BUTTON_IMAGE,
            INACTIVE_UPGRADE_BUTTON_IMAGE,
            f'upgrade_button_{idx + 1}', partial(upgrade, idx)
        ))
    current_background_image = CHARACTERISTICS_BACKGROUND


def shift_characteristics_idx(direction):
    global current_characteristics_target_idx, current_characteristics_target
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
    for idx in range(1, 4):
        if improvement_scales[current_characteristics_target][1][-idx]:
            buttons[-idx].is_visible = False
        else:
            buttons[-idx].is_visible = True
    for idx in range(1, 4 - len(
            improvement_scales[current_characteristics_target][0]
    )):
        buttons[-idx].is_visible = False


def upgrade(idx):
    global improvement_scales, coins, buttons
    # проверка наличия нужной суммы монет для пользователя
    if coins - improvement_scales[current_characteristics_target][2][idx][
        improvement_scales[current_characteristics_target][0][idx][3]
    ] >= 0:
        # вычитание цены из общей суммы монет пользователя и обновление
        # баланса в БД
        coins -= improvement_scales[current_characteristics_target][2][idx][
            improvement_scales[current_characteristics_target][0][idx][3]
        ]
        cur.execute(f'UPDATE Player_data SET Coins = {coins}')
        con.commit()
        # проверка на заполнение полоски до конца (всего 5 делений по 0.2)
        if improvement_scales[current_characteristics_target][0][idx][2] != 1:
            UPGRADE_SOUND.play()
            # запуск lambda функций
            improvement_scales[current_characteristics_target][3][idx]()
            col = improvement_values[current_characteristics_target][idx][0]
            value = improvement_values[current_characteristics_target][idx][1]
            # Проверяем, что изменяемая характеристика не скорость стрельбы
            if col != 'Shot_delay':
                # Берем старое значение
                old_value = cur.execute(
                    f'SELECT {col} FROM Player_data'
                ).fetchone()[0]
                # Присваиваем новое
                cur.execute(
                    f"UPDATE Player_data SET {col} = {old_value + value}"
                )
                con.commit()
            else:
                # Для скорости стрельбы логика та же, но значение мы отнимаем
                old_value = cur.execute(
                    f'SELECT {col} FROM Player_data'
                ).fetchone()[0]
                cur.execute(
                    f"UPDATE Player_data SET {col} = {old_value - value}"
                )
                con.commit()
            # обновляем измененную величину
            update_player_scales(current_characteristics_target, col)
            # увеличение полоски
            improvement_scales[current_characteristics_target][0][idx][2] += \
                0.2
            # изменение цены для покупки
            improvement_scales[current_characteristics_target][0][idx][3] += 1
            # увеличение длинны темного прямоугольника (за светлым)
            improvement_scales[current_characteristics_target][0][idx][
                0].width = \
                IMPROVEMENT_SCALE_WIDTH * improvement_scales[
                    current_characteristics_target
                ][0][idx][2]
            # увеличение светлой полоски
            improvement_scales[current_characteristics_target][0][idx][
                1].width = \
                IMPROVEMENT_SCALE_WIDTH * \
                improvement_scales[
                    current_characteristics_target
                ][0][idx][2] - BORDER_WIDTH * 2
            # если полоска дошла до конца, то обозначается полная прокачка
            # характеристики и кнопка становится невидима
            if improvement_scales[current_characteristics_target][0][idx][2] \
                    == 1:
                improvement_scales[current_characteristics_target][1][
                    idx] = True
                buttons[-(3 - idx)].is_visible = False


def update_player_scales(characteristic: str, scale: str) -> None:
    """
    Функция для обновления переменных после изменения характеристик в БД
    :param characteristic: категория характеристики (ak-47 | player)
    :param scale: характеристика из категории
    """

    global player, shot_delay, player_damage
    if characteristic == 'ak-47':
        if scale == 'Ammo':
            player.ammo = cur.execute(
                'SELECT Ammo FROM Player_data'
            ).fetchone()[0]
        elif scale == 'Shot_delay':
            shot_delay = cur.execute(
                'SELECT Shot_delay FROM Player_data'
            ).fetchone()[0]
        elif scale == 'Damage':
            player_damage = cur.execute(
                "SELECT Damage FROM Player_data"
            ).fetchone()[0]
    elif characteristic == 'player':
        if scale == 'HP':
            player.hp = cur.execute(
                "SELECT HP FROM Player_data"
            ).fetchone()[0]
        elif scale == 'Shields':
            player.shield = cur.execute(
                'SELECT Shields FROM Player_data'
            ).fetchone()[0]


def continue_game():
    global pause
    PAUSE_STOP_SOUND.play()
    del buttons[-3:]
    pygame.mixer.music.pause()
    pygame.mixer.music.load(
        "data/sounds/main_saundtrack.mp3"
    )
    pygame.mixer.music.play()
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


def select_level():
    global current_menu, buttons, pause, start
    pause, start = False, False
    buttons.clear()
    buttons.append(
        Button(
            151, 31, 70, 322,
            ACTIVE_START_BUTTON_IMAGE,
            INACTIVE_START_BUTTON_IMAGE,
            'start_button', start_game
        )
    )
    buttons.append(
        Button(
            28, 28, 41, 327,
            ACTIVE_SMALL_RETURN_BUTTON_IMAGE,
            INACTIVE_SMALL_RETURN_BUTTON_IMAGE,
            'return_to_main_menu_button', return_to_main_menu
        )
    )
    current_menu = 3


buttons = [
    Button(
        151, 31, 70, 60,
        ACTIVE_START_BUTTON_IMAGE,
        INACTIVE_START_BUTTON_IMAGE,
        'start_button', select_level
    ),
    Button(
        151, 31, 70, 120,
        ACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
        INACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
        'chracteristics_button', lambda: print('Улучшение')
    ),
    Button(
        151, 31, 70, 180,
        ACTIVE_SKINS_BUTTON_IMAGE,
        INACTIVE_SKINS_BUTTON_IMAGE,
        'skins_button', lambda: print('Скины')
    ),
    Button(
        151, 31, 70, 240,
        ACTIVE_GUIDE_BUTTON_IMAGE,
        INACTIVE_GUIDE_BUTTON_IMAGE,
        'chracteristics_button', lambda: print('Руководство')
    ),
    Button(
        151, 31, 70, 300,
        ACTIVE_EXIT_BUTTON_IMAGE,
        INACTIVE_EXIT_BUTTON_IMAGE,
        'chracteristics_button', quit
    )
]

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
                player.image = pygame.transform.flip(PLAYER_IMAGE,
                                                     True, False)
            if event.key == pygame.K_d:
                direction = 2
                player.direction = DIRECTION_RIGHT
                player.image = PLAYER_IMAGE
            if event.key == pygame.K_ESCAPE:
                pause = not pause
                if pause:
                    current_menu = 2
                    PAUSE_START_SOUND.play()
                    pygame.mixer.music.pause()
                    pygame.mixer.music.load(
                        "data/sounds/pause_saundtrack.mp3"
                    )
                    pygame.mixer.music.play()
                    blured_background_image = get_screenshot()
                    buttons.append(Button(
                        152, 38, WIDTH // 2 - 78, HEIGHT // 2 - 32,
                        ACTIVE_CONTINUE_BUTTON_IMAGE,
                        INACTIVE_CONTINUE_BUTTON_IMAGE,
                        'continue_button', continue_game
                    ))
                    buttons.append(Button(
                        152, 38, WIDTH // 2 - 78, HEIGHT // 2 + 16,
                        ACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
                        INACTIVE_CHARACTERISTICS_BUTTON_IMAGE,
                        'characteristics_button', open_characteristics_menu
                    ))
                    buttons.append(Button(
                        152, 38, WIDTH // 2 - 78, 266,
                        ACTIVE_RETURN_BUTTON_IMAGE,
                        INACTIVE_RETURN_BUTTON_IMAGE,
                        'return_button', select_level
                    ))
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
                if player.ammo != 5:
                    player.ammo = 0
                    RECHARGE_SOUND.play()
                    player.recharge_timer = 120
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                button_pushed = False
    if start:
        if not pause:
            if not shot_delay:
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
                        player.y + player.rect.h // 2 + 2
                    )
                    shot_delay = 25
            else:
                shot_delay -= 1

            if player.recharge_timer:
                player.recharge_timer -= 1
                if player.recharge_timer == 0:
                    player.ammo = cur.execute(
                        "SELECT Ammo FROM Player_data"
                    ).fetchone()[0]
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
                    virtual_surface, camera, player_group,
                    [SHOT_SOUND, HEAVY_ENEMY_SHOT_SOUND,
                     ARMORED_ENEMY_SHOT_SOUND, MARKSMAN_ENEMY_SHOT_SOUND],
                    bullet_group, target_group, ENEMY_BULLET_IMAGE
                )

            for bullet in bullet_group:
                bullet.update(
                    destructible_groups,
                    indestructible_groups,
                    [ENEMY_DESTROY_SOUND, BOX_DESTROY_SOUND],
                    [HIT_SOUND, SHIELD_HIT_SOUND],
                    player_group, camera,
                    virtual_surface
                )
            # Обновляем таймер щита игрока
            if player.shield_recharge:
                player.shield_recharge -= 1
                if player.shield_recharge == 0:
                    player.shield += 1
                    if player.shield != 3:
                        player.shield_recharge = 300
            # Проверяем хп игрока
            for player in player_group:
                if player.hp == 0:
                    print("ПОМЕР")

            player_group.draw(virtual_surface)

            player.check_collision_sides(target_group)
            if frame % 10:
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
            show_dashboard(player.ammo, coins)
        else:
            virtual_surface.blit(blured_background_image, (0, 0))
            if current_menu == 1:
                virtual_surface.blit(CHARACTERISTICS_BACKGROUND, (0, 0))
                virtual_surface.blit(CHARACTERISTICS_IMAGES[
                                current_characteristics_target_idx
                            ], (300, 91))
                for idx, improvement_scale in enumerate(
                        improvement_scales[
                            current_characteristics_target
                        ][0]
                ):
                    pygame.draw.rect(virtual_surface, '#d19900', improvement_scale[0])
                    pygame.draw.rect(virtual_surface, '#fff200', improvement_scale[1])
                    print_text(
                        str(improvement_scales[
                                current_characteristics_target
                            ][2][idx][improvement_scale[3]]), 313,
                        220 + idx * 48,
                        font_size=9
                    )
            elif current_menu == 2:
                virtual_surface.blit(PAUSE_BACKGROUND, (0, 0))
    else:
        if current_menu == 0:
            virtual_surface.blit(MAIN_MENU_IMAGE, (0, 0))
        elif current_menu == 3:
            virtual_surface.blit(SELECT_LEVEL_MENU_IMAGE, (0, 0))

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
con.close()
