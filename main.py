import os
import sys
import pygame

from constants import WIDTH, HEIGHT, FPS, STEP, DIRECTION_LEFT, \
    DIRECTION_RIGHT

from classes import Player, Wall, Box, Camera, Bullet

# Задаём параметры приложения
pygame.init()
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


def load_image(name, color_key=None):
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


def load_level(filename):
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
            if level[y][x] == '#':
                Wall(bricks_group, all_sprites, TILE_IMAGES,
                     x, y)
            elif level[y][x] == '@':
                new_player = Player(player_group, all_sprites, PLAYER_IMAGE,
                                    5, x, y)
            elif level[y][x] == ':':
                Box(boxes_group, all_sprites, TILE_IMAGES,
                    x, y)
    # вернем игрока, а также размер поля в клетках
    return new_player, x, y


def terminate():
    pygame.quit()
    sys.exit()


# Изображениями тайлов
TILE_IMAGES = {'brick': load_image('bricks.png'),
               'box': load_image('box.png')}
# Изображение игрока
PLAYER_IMAGE = load_image('Artur.png')
# Изображение пули
BULLET_IMAGE = load_image('bullet.png')

player, level_x, level_y = generate_level(load_level("level_1.txt"))
camera = Camera((level_x, level_y))

running = True
collide_side = ''

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
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
            if event.key == pygame.K_SPACE:
                if not (pygame.sprite.spritecollideany(player, bricks_group)
                        or pygame.sprite.spritecollideany(
                            player, boxes_group)):
                    player.rect.y -= STEP
                    collide_side = ''
                elif collide_side != 'up' and collide_side:
                    player.rect.y -= STEP
                    collide_side = ''
                else:
                    collide_side = 'up'
            if event.key == pygame.K_f:
                new_bul = Bullet(bullet_group, all_sprites, BULLET_IMAGE,
                                 player.direction,
                                 player.rect.x + player.rect.w,
                                 player.rect.y + player.rect.h // 2)

    camera.update(player, [bricks_group, boxes_group])

    for sprite in all_sprites:
        camera.apply(sprite)

    for bullet in bullet_group:
        bullet.update([boxes_group], [bricks_group])

    screen.fill(pygame.Color(89, 151, 254))
    boxes_group.draw(screen)
    bricks_group.draw(screen)
    player_group.draw(screen)
    bullet_group.draw(screen)

    pygame.display.flip()

    clock.tick(FPS)

terminate()
