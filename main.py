import os
import sys
from ctypes import windll

import pygame
import win32gui
import win32ui
from PIL import Image, ImageFilter

from constants import WIDTH, HEIGHT, FPS, STEP, DIRECTION_LEFT, \
    DIRECTION_RIGHT

from classes import Player, Enemy, Wall, Box, Camera, Bullet, Button, Ray

# Задаём параметры приложения
pygame.init()
pygame.mouse.set_visible(False)
pygame.key.set_repeat(200, 70)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Фоновая музыка
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


def load_image(name: str, color_key=None) -> pygame.Surface:
    """ Загрузчик изображений """
    fullname = os.path.join('data', 'images', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)

    if color_key is not None:
        if color_key == -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key)
    else:
        image = image.convert_alpha()
    return image


def load_level(filename: str) -> list[str]:
    filename = "data/" + filename
    # читаем уровень, убирая символы перевода строки
    with open(filename, 'r') as mapFile:
        level_map = [line.strip() for line in mapFile]

    # и подсчитываем максимальную длину
    max_width = max(map(len, level_map))

    # дополняем каждую строку пустыми клетками ('.')
    return list(map(lambda x: x.ljust(max_width, '.'), level_map))


def generate_level(level):
    new_player, x, y = None, None, None
    for y in range(len(level)):
        for x in range(len(level[y])):
            if level[y][x] in ('l', 'd', 'm', 'L', '^'):
                Wall(bricks_group, all_sprites, TILE_IMAGES,
                     TILE_NAMES[level[y][x]], x, y)
            elif level[y][x] == '@':
                new_player = Player(player_group, all_sprites, PLAYER_IMAGE,
                                    5, x, y)
            elif level[y][x] == '<' or level[y][x] == '>':
                if level[y][x] == '>':
                    Enemy(enemies_group, all_sprites, ENEMY_IMAGE, x, y,
                          direction=DIRECTION_RIGHT)
                else:
                    Enemy(enemies_group, all_sprites, ENEMY_IMAGE, x, y)
            elif level[y][x] == ':':
                Box(boxes_group, all_sprites, TILE_IMAGES,
                    x, y)
    # вернем игрока, а также размер поля в клетках
    return new_player, x, y


def terminate():
    pygame.quit()
    sys.exit()


def print_text(message, px, py, font_color=(255, 255, 255),
               font_type="bahnschrift", font_size=30):
    """Отрисовка текста"""
    font = pygame.font.SysFont(font_type, font_size)
    text = font.render(message, True, font_color)
    screen.blit(text, (px, py))


def show_dashboard(ammo, coins):
    """Отрисовка счёта и количества врагов"""
    screen.blit(AMMO_COUNTER_IMAGE, (90, 10))
    screen.blit(COIN_COUNTER_IMAGE, (10, 10))
    print_text(str(ammo) if ammo else 'Перезарядка', 175, 36, "gray30",
               "stxingkai", 30)
    print_text(str(coins), 60, 17, "gray30", "stxingkai", 40)


def pilImageToSurface(pilImage):
    return pygame.image.fromstring(
        pilImage.tobytes(), pilImage.size, pilImage.mode).convert()


def get_screenshot():
    window = win32gui.FindWindow(None, 'pygame window')

    left, top, right, bot = win32gui.GetWindowRect(window)
    w = right - left  # wide
    h = bot - top  # hight

    hwndDC = win32gui.GetWindowDC(window)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

    saveDC.SelectObject(saveBitMap)
    result = windll.user32.PrintWindow(window, saveDC.GetSafeHdc(), 1)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    im = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(window, hwndDC)

    return pilImageToSurface(
        im.filter(ImageFilter.GaussianBlur(radius=5))
    )


# Изображениями тайлов
TILE_IMAGES = {'land': load_image('land.png'),
               'light_land': load_image('light_land.png'),
               'dirt': load_image('dirt.png'),
               'mixed_dirt': load_image('mixed_dirt.png'),
               'light_dirt': load_image('light_dirt.png'),
               'box': load_image('box.png')}
TILE_NAMES = {
    'l': 'land',
    '^': 'light_land',
    'd': 'dirt',
    'L': 'light_dirt',
    'm': 'mixed_dirt'
}
# Изображение игрока
PLAYER_IMAGE = load_image('Artur.png')
# Изображение пули
BULLET_IMAGE = load_image('bullet.png')
# Изображение врага
ENEMY_IMAGE = load_image('Enemy.png')
# Изображение heavy врага
HEAVY_ENEMY_IMAGE = load_image('Heavy_enemy.png')
# Изображение пули врага
ENEMY_BULLET_IMAGE = load_image('Enemy_bullet.png')
# Изображение активной кнопки продолжения игры
ACTIVE_CONTINUE_BUTTON_IMAGE = load_image('active_continue_button_image.png')
# Изображение неактивной кнопки продолжения игры
INACTIVE_CONTINUE_BUTTON_IMAGE = load_image(
    'inactive_continue_button_image.png'
)
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
# Листы со спрайтами монетки
COINS_SHEET = load_image('coins_sheet8x1.png')
# Счетчик снарядов в обойме
AMMO_COUNTER_IMAGE = load_image('ammo_counter.png')
# Счетчик монеток
COIN_COUNTER_IMAGE = load_image('coin_counter.png')
# Изображение курсора
MAIN_ARROW_IMAGE = load_image('main_cursor_image.png')
# Изображение курсора, наведенного на кликабельный предмет
CLICK_ARROW_IMAGE = load_image('click_cursor_image.png')

ARROW_IMAGES = [MAIN_ARROW_IMAGE, CLICK_ARROW_IMAGE]

# Звук открытия меню паузы
PAUSE_START_SOUND = pygame.mixer.Sound("data/sounds/pause_start_sound.wav")
# Звук закрытия меню паузы
PAUSE_STOP_SOUND = pygame.mixer.Sound("data/sounds/pause_stop_sound.wav")

COINS_DATA = {
    'sheet': COINS_SHEET, 'columns': 8, 'rows': 1, 'percent': 50,
    'coins_group': coins_group, 'all_sprites': all_sprites
}

# Игрок, размер уровня в ширину и в высоту
player, level_x, level_y = generate_level(load_level("level_1.txt"))
# Камера
camera = Camera((level_x, level_y))

running = True
# С какой стороны столкнулись спрайты
collide_side = ''

# счетчик прыжка
jump_counter = 0

# Монетки игрока (надо с БД брать)
coins = 0

# Нажата ли кнопка стрельбы
button_pushed = False

arrow_idx = 0

# Задержка между выстрелами
shot_delay = 0

skip = False

buttons = []
blured_background_image = None


def continue_game():
    global skip
    PAUSE_STOP_SOUND.play()
    del buttons[-1]
    pygame.mixer.music.pause()
    pygame.mixer.music.load(
        "data/sounds/main_saundtrack.mp3"
    )
    pygame.mixer.music.play()
    skip = not skip


def draw_arrow(screen, image, x, y):
    screen.blit(image, (x, y))


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
        if event.type == pygame.KEYDOWN:
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
                skip = not skip
                if skip:
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
                else:
                    PAUSE_STOP_SOUND.play()
                    del buttons[-1]
                    pygame.mixer.music.pause()
                    pygame.mixer.music.load(
                        "data/sounds/main_saundtrack.mp3"
                    )
                    pygame.mixer.music.play()

    if not skip:

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
                                 player.rect.y + player.rect.h // 2)
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
                player.rect.y += 5

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
            bullet.update([boxes_group, enemies_group], [bricks_group],
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
                enemy.ray = Ray(rays_group, enemy.direction, enemy.rect.x,
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
                                        ENEMY_BULLET_IMAGE, enemy.direction,
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
        boxes_group.draw(screen)
        bricks_group.draw(screen)
        player_group.draw(screen)
        bullet_group.draw(screen)
        coins_group.draw(screen)
        enemies_group.draw(screen)

        show_dashboard(player.ammo, coins)
    else:
        screen.blit(blured_background_image, (0, 0))
        screen.blit(PAUSE_BACKGROUND, (0, 0))

    for button in buttons:
        arrow_idx = button.draw(screen)

    x, y = pygame.mouse.get_pos()
    if 0 < x < WIDTH and \
            0 < y < HEIGHT:
        draw_arrow(screen, ARROW_IMAGES[arrow_idx], x, y)
        arrow_idx = 0

    pygame.display.flip()
    clock.tick(FPS)

terminate()
