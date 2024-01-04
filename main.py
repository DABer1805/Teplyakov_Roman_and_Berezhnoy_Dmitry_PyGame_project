import os
import sys
from ctypes import windll
from functools import partial
from typing import Union

import pygame
import win32gui
import win32ui
from PIL import Image, ImageFilter

from constants import WIDTH, HEIGHT, FPS, STEP, DIRECTION_LEFT, \
    DIRECTION_RIGHT, BORDER_WIDTH, IMPROVEMENT_SCALE_WIDTH

from classes import Player, Enemy, Wall, Box, Camera, Bullet, Button, Ray, \
    PhantomTile

# Задаём параметры приложения
pygame.init()
pygame.key.set_repeat(200, 70)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Прячем родной курсор
pygame.mouse.set_visible(False)

# Грузим фоновую музыку и запускаем её проигрываться
pygame.mixer.music.load("data/sounds/main_saundtrack.mp3")
pygame.mixer.music.play()

# Игрок
player = None

# Все спрайты
all_sprites = pygame.sprite.Group()
# Спрайты коробок
boxes_group = pygame.sprite.Group()
# Спрайты кирпичных блоков
bricks_group = pygame.sprite.Group()
# Спрайты, где есть игрок
player_group = pygame.sprite.Group()
# Спрайты пулей
bullet_group = pygame.sprite.Group()
# Спрайты монеток
coins_group = pygame.sprite.Group()
# Спрайты врагов
enemies_group = pygame.sprite.Group()
# Спрайты лучей
rays_group = pygame.sprite.Group()
# Группа всех статичных блоков
tile_group = pygame.sprite.Group()
tile_group.add(bricks_group)
tile_group.add(boxes_group)
# Группа фантомных блоков (задний фон и украшения)
phantom_group = pygame.sprite.Group()


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


def load_level(filename: str) -> list[str]:
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
    return list(map(lambda x: x.ljust(max_width, '.'), level_map))


def generate_level(level: list[str]) -> tuple[Player, int, int]:
    """ Генерация уровня """
    new_player, x, y = None, None, None
    for y in range(len(level)):
        for x in range(len(level[y])):
            # Тут те тайлы, котрые не рушатся, создаётся соответствующий
            # спрайт и добавляется в группу
            if level[y][x] in ('w', 's', 'l', 'd', 'm', 'L', '^', 'D'):
                Wall(bricks_group, all_sprites, TILE_IMAGES,
                     TILE_NAMES[level[y][x]], x, y)
            elif level[y][x] in ('#', '_', '-', '*', '/', '0', '1', '2',
                                 '3'):
                PhantomTile(phantom_group, all_sprites, TILE_IMAGES,
                            TILE_NAMES[level[y][x]], x, y)
            # Тут считывается местоположение игрока и создаётся его спрайт
            # (НЕ НАДО СОЗДАВАТЬ В
            # ФАЙЛЕ НЕСКОЛЬКИХ ИГРОКОВ!!!)
            elif level[y][x] == '@':
                new_player = Player(player_group, all_sprites, PLAYER_IMAGE,
                                    5, x, y)
            # Тут те тайлы, котрые имеют hp и их можно разрушить, создаётся
            # соответствующий спрайт и добавляется в группу
            elif level[y][x] == '<' or level[y][x] == '>':
                if level[y][x] == '>':
                    Enemy(enemies_group, all_sprites, ENEMY_IMAGE, x, y,
                          direction=DIRECTION_RIGHT)
                else:
                    Enemy(enemies_group, all_sprites, ENEMY_IMAGE, x, y)
            elif level[y][x] in ('b', 'B'):
                Box(boxes_group, all_sprites, TILE_IMAGES,
                    TILE_NAMES[level[y][x]], x, y)
    # Вернем игрока, а также размер поля в клетках
    return new_player, x, y


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
    screen.blit(font.render(text, True, font_color), (pos_x, pos_y))


def show_dashboard(ammo: int, coins: int) -> None:
    """ Отрисовка всех полосочек с характеристиками персонажа (hp, щиты и
    кол-во оставшихся пуль в магазине), а также счётчика монет

    :param ammo: Сколько пуль у игрока в данный момент
    :param coins: Количество монет у игрока в данный момент
    """
    # Отрисовываем картинку для счётчика пуль
    screen.blit(AMMO_COUNTER_IMAGE, (10, 10))
    # Отрисовываем картинку для счётчика монет
    screen.blit(COIN_COUNTER_IMAGE, (650, 10))
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
    window = win32gui.FindWindow(None, 'pygame window')

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
    'land': load_image('land.png'),
    'light_land': load_image('light_land.png'),
    'dirt': load_image('dirt.png'),
    'mixed_dirt': load_image('mixed_dirt.png'),
    'light_dirt': load_image('light_dirt.png'),
    'box': load_image('box.png'),
    'shelter_box': load_image('shelter_box.png'),
    'shelter_floor': load_image('shelter_floor.png'),
    'shelter_wall': load_image('shelter_wall.png'),
    'down_shelter_floor': load_image('down_shelter_floor.png'),
    'shelter_light': load_image('shelter_light.png'),
    'shelter_small_door': load_image('shelter_small_door.png'),
    'shelter_background_wall_1': load_image('shelter_background_wall_1.png'),
    'shelter_background_wall_2': load_image('shelter_background_wall_2.png'),
    'shelter_door': load_image('shelter_door.png'),
    'storage_background_1': load_image('storage_background_image_1.png'),
    'storage_background_2': load_image('storage_background_image_2.png'),
    'water_treatment_room_background_1': load_image(
        'water_treatment_room_background_image_1.png'
    ),
    'infirmary_background': load_image('infirmary_background_image.png')
}

# Названия тайлов
TILE_NAMES = {
    'l': 'land',
    '^': 'light_land',
    'd': 'dirt',
    'b': 'box',
    'B': 'shelter_box',
    'L': 'light_dirt',
    'm': 'mixed_dirt',
    's': 'shelter_floor',
    'w': 'shelter_wall',
    '*': 'shelter_light',
    '#': 'shelter_small_door',
    '_': 'shelter_background_wall_1',
    '-': 'shelter_background_wall_2',
    '/': 'shelter_door',
    'D': 'down_shelter_floor',
    '0': 'storage_background_1',
    '1': 'storage_background_2',
    '2': 'water_treatment_room_background_1',
    '3': 'infirmary_background'
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
# Изображение врага
ENEMY_IMAGE = load_image('ordinary_enemy_image.png')
# Изображение heavy врага
HEAVY_ENEMY_IMAGE = load_image('heavy_enemy.png')
# Изображение пули врага
ENEMY_BULLET_IMAGE = load_image('enemy_bullet.png')
# Звук подборам монет
COIN_SELECTION_SOUND = pygame.mixer.Sound("data/sounds/coin_selection.wav")
# Звук выстрела
SHOT_SOUND = pygame.mixer.Sound("data/sounds/shot_sound.wav")
# Звук перезарядки
RECHARGE_SOUND = pygame.mixer.Sound("data/sounds/recharge_sound.wav")
# Звук разрушения коробки
BOX_DESTROY_SOUND = pygame.mixer.Sound("data/sounds/box_destroy_sound.wav")
# Звук попадания в препятствие
HIT_SOUND = pygame.mixer.Sound("data/sounds/hit_sound.wav")
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

COINS_DATA = {
    'sheet': COINS_SHEET, 'columns': 8, 'rows': 1, 'percent': 50,
    'coins_group': coins_group, 'all_sprites': all_sprites
}

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

# Монетки игрока (надо с БД брать)
coins = 5000
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
            [10, 45, 100, 250, 500, 'max'],
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

blured_background_image = None

current_characteristics_target = 'ak-47'

current_characteristics_target_idx = 0

start = False


def start_game():
    global start, player, level_x, level_y, camera, all_sprites
    for sprite in all_sprites:
        sprite.kill()
    # Игрок, размер уровня в ширину и в высоту
    player, level_x, level_y = generate_level(load_level('level_1.txt'))
    # Камера
    camera = Camera((level_x, level_y))
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
    if coins - improvement_scales[current_characteristics_target][2][idx][
        improvement_scales[current_characteristics_target][0][idx][3]
    ] >= 0:
        coins -= improvement_scales[current_characteristics_target][2][idx][
            improvement_scales[current_characteristics_target][0][idx][3]
        ]
        if improvement_scales[current_characteristics_target][0][idx][2] != 1:
            UPGRADE_SOUND.play()
            improvement_scales[current_characteristics_target][3][idx]()
            improvement_scales[current_characteristics_target][0][idx][2] += \
                0.2
            improvement_scales[current_characteristics_target][0][idx][3] += 1
            improvement_scales[current_characteristics_target][0][idx][
                0].width = \
                IMPROVEMENT_SCALE_WIDTH * improvement_scales[
                    current_characteristics_target
                ][0][idx][2]
            improvement_scales[current_characteristics_target][0][idx][
                1].width = \
                IMPROVEMENT_SCALE_WIDTH * \
                improvement_scales[
                    current_characteristics_target
                ][0][idx][2] - BORDER_WIDTH * 2
            if improvement_scales[current_characteristics_target][0][idx][2] \
                    == 1:
                improvement_scales[current_characteristics_target][1][
                    idx] = True
                buttons[-(3 - idx)].is_visible = False


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

# Игровой цикл
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                button_pushed = True
            elif event.button == 3:
                if player.ammo:
                    player.ammo = 0
                    RECHARGE_SOUND.play()
                    player.recharge_timer = 120
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                button_pushed = False
        if start and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if not jump_counter:
                    jump_counter = 20
            if event.key == pygame.K_a:
                # Движение влево
                if not (pygame.sprite.spritecollideany(player, bricks_group)
                        or pygame.sprite.spritecollideany(
                            player, boxes_group)):
                    player.rect.x -= STEP
                    player.direction = DIRECTION_LEFT
                    player.image = pygame.transform.flip(PLAYER_IMAGE,
                                                         True, False)
                    collide_side = ''
                elif collide_side != 'left' and collide_side:
                    player.rect.x -= STEP
                    player.direction = DIRECTION_LEFT
                    player.image = pygame.transform.flip(PLAYER_IMAGE,
                                                         True, False)
                    collide_side = ''
                else:
                    collide_side = 'left'
            if event.key == pygame.K_d:
                # Движение вправо
                if not (pygame.sprite.spritecollideany(player, bricks_group)
                        or pygame.sprite.spritecollideany(
                            player, boxes_group)):
                    player.rect.x += STEP
                    player.direction = DIRECTION_RIGHT
                    player.image = PLAYER_IMAGE
                    collide_side = ''
                elif collide_side != 'right' and collide_side:
                    player.rect.x += STEP
                    player.direction = DIRECTION_RIGHT
                    player.image = PLAYER_IMAGE
                    collide_side = ''
                else:
                    collide_side = 'right'
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

    if start:
        if not pause:

            if not shot_delay:
                if button_pushed and player.ammo:
                    player.ammo -= 1
                    if player.direction == DIRECTION_LEFT:
                        bullet_image = pygame.transform.flip(BULLET_IMAGE,
                                                             True, False)
                        x = player.rect.x
                    else:
                        bullet_image = BULLET_IMAGE
                        x = player.rect.x + player.rect.w
                    SHOT_SOUND.play()
                    # Выпустить снаряд
                    new_bul = Bullet(bullet_group, all_sprites, bullet_image,
                                     player.direction,
                                     x,
                                     player.rect.y + player.rect.h // 2 + 2)
                    shot_delay = 25
            else:
                shot_delay -= 1

            if jump_counter > 0:
                jump_counter -= 1
                if not (pygame.sprite.spritecollideany(player, bricks_group)
                        or pygame.sprite.spritecollideany(
                            player, boxes_group)):
                    player.rect.y -= 8
                    collide_side = ''
                else:
                    jump_counter = 0
            else:
                collided = False

                for sprite in bricks_group:
                    if sprite.rect.collidepoint(player.rect.midbottom):
                        collided = True

                if not collided:
                    player.rect.y += 2

            if player.recharge_timer:
                player.recharge_timer -= 1
                if player.recharge_timer == 0:
                    player.ammo = 5
            elif not player.ammo:
                RECHARGE_SOUND.play()
                player.recharge_timer = 120

            # Обновляем камеру
            camera.update(player, collide_side)

            # Перемещаем все спрайты
            for sprite in all_sprites:
                camera.apply(sprite)

            # Перемещаем пули
            for bullet in bullet_group:
                bullet.update([boxes_group, enemies_group],
                              [bricks_group],
                              COINS_DATA, BOX_DESTROY_SOUND, HIT_SOUND,
                              player_group)

            # Проверяем наличие игрока в поле зрения врага и перемещаем врагов
            for enemy in enemies_group:
                # Луч для проверки попадания игрока в поле зрения врага
                if enemy.direction:
                    enemy.ray = Ray(rays_group, enemy.direction,
                                    enemy.rect.x + enemy.rect.w,
                                    enemy.rect.y + enemy.rect.h // 2)
                else:
                    enemy.ray = Ray(rays_group, enemy.direction,
                                    enemy.rect.x,
                                    enemy.rect.y + enemy.rect.h // 2)

                # Проверка пересечения с игроком лучами и переход в режим атаки
                # для врага, если игрок в поле зрения
                if enemy.ray.check_collide_with_player(player_group):
                    enemy.attack_player = True
                    enemy.speed = 0
                    enemy.attack_timer = 120
                else:
                    if enemy.attack_timer:
                        enemy.attack_timer -= 1
                        if enemy.attack_timer == 0:
                            enemy.attack_player = False
                            enemy.speed = 1
                    elif enemy.attack_timer == 0:
                        enemy.attack_player = False
                        enemy.speed = 1

                # Создание пуль в случае, если враг в режиме атаки
                if enemy.attack_player:
                    if enemy.is_shoot:
                        SHOT_SOUND.play()
                        new_bullet = Bullet(bullet_group, all_sprites,
                                            ENEMY_BULLET_IMAGE,
                                            enemy.direction,
                                            enemy.rect.x,
                                            enemy.rect.y + enemy.rect.h // 2,
                                            is_enemy_bullet=True)
                        enemy.timer = 90
                        enemy.is_shoot = False
                    else:
                        enemy.timer -= 1
                        if enemy.timer == 0:
                            enemy.is_shoot = True

                enemy.update(player.direction)

            for coin in coins_group:
                if coin.counter == 3:
                    coin.counter = 0
                    coin.update()
                else:
                    coin.counter += 1

            coins_collide_list = pygame.sprite.spritecollide(
                player, coins_group, False
            )
            if coins_collide_list:
                coins += 1
                COIN_SELECTION_SOUND.play()
                coins_collide_list[0].kill()

            # Красим фон
            screen.blit(BACKGROUND_IMAGE, (0, 0))
            # Рисуем спрайты
            phantom_group.draw(screen)
            boxes_group.draw(screen)
            bricks_group.draw(screen)
            player_group.draw(screen)
            bullet_group.draw(screen)
            coins_group.draw(screen)
            enemies_group.draw(screen)

            show_dashboard(player.ammo, coins)
        else:
            screen.blit(blured_background_image, (0, 0))
            if current_menu == 1:
                screen.blit(CHARACTERISTICS_BACKGROUND, (0, 0))
                screen.blit(CHARACTERISTICS_IMAGES[
                                current_characteristics_target_idx
                            ], (300, 91))
                for idx, improvement_scale in enumerate(
                        improvement_scales[
                            current_characteristics_target
                        ][0]
                ):
                    pygame.draw.rect(screen, '#d19900', improvement_scale[0])
                    pygame.draw.rect(screen, '#fff200', improvement_scale[1])
                    print_text(
                        str(improvement_scales[
                                current_characteristics_target
                            ][2][idx][improvement_scale[3]]), 313,
                        220 + idx * 48,
                        font_size=9
                    )
            elif current_menu == 2:
                screen.blit(PAUSE_BACKGROUND, (0, 0))

    else:
        if current_menu == 0:
            screen.blit(MAIN_MENU_IMAGE, (0, 0))
        elif current_menu == 3:
            screen.blit(SELECT_LEVEL_MENU_IMAGE, (0, 0))

    for button in buttons:
        cur_idx = button.draw(screen)
        if cur_idx:
            arrow_idx = cur_idx

    x, y = pygame.mouse.get_pos()
    if 0 < x < WIDTH and \
            0 < y < HEIGHT:
        draw_arrow(screen, ARROW_IMAGES[arrow_idx], x, y)
        arrow_idx = 0

    pygame.display.flip()
    clock.tick(FPS)

terminate()
