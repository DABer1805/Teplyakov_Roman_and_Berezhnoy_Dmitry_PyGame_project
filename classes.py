from random import randrange, random

import pygame
import sqlite3

from constants import TILE_WIDTH, TILE_HEIGHT, WIDTH, HEIGHT, \
    DIRECTION_RIGHT, BULLET_SPEED, DIRECTION_LEFT, BULLET_WIDTH, \
    HEALTH_SCALE_WIDTH, HEALTH_SCALE_HEIGTH, HEALTH_SCALE_BORDER, \
    KEY_OBJECT_HEALTH_SCALE_WIDTH, KEY_OBJECT_HEALTH_SCALE_HEIGTH, \
    KEY_OBJECT_HEALTH_SCALE_BORDER

from functools import partial
from typing import Literal


class AnimatedSprite(pygame.sprite.Sprite):
    def __init__(self, sheet, columns, rows, x, y, target_group, all_sprites):
        super().__init__(target_group, all_sprites)
        self.x = x
        self.y = y
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.counter = 0
        self.image = self.frames[self.cur_frame]

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def update(self):
        self.cur_frame = (self.cur_frame + 1) % len(self.frames)
        self.image = self.frames[self.cur_frame]


class Coin(AnimatedSprite):
    def __init__(self, selection_sound, sheets, type, columns, rows, x, y,
                 target_group,
                 all_sprites):
        super().__init__(sheets[type], columns, rows, x, y,
                         target_group, all_sprites)
        self.selection_sound = selection_sound
        cost = None
        if type == 0:
            cost = 1
        elif type == 1:
            cost = 5
        elif type == 2:
            cost = 15
        self.cost = cost


class Tile(pygame.sprite.Sprite):
    """ Базовый класс блоков """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 image, pos_x, pos_y, chunk_number) -> None:
        """
        :param tiles_group: Группа, куда будет добавлен блок
        :param all_sprites: Все спрайты
        """
        super().__init__(tiles_group, all_sprites)
        # Изображение спрайта
        self.image = image
        # Размещаем на экране текущий блок
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)
        self.x = self.rect.x
        self.y = self.rect.y
        self.chunk_number = chunk_number


class PhantomTile(Tile):
    """ Блок фантомного спрайта """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group, image,
                 pos_x: int, pos_y: int, chunk_number) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param tile_images: Словарик с изображениями всех блоков
        :param image_name: Название изображения
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(tiles_group, all_sprites, image, pos_x, pos_y,
                         chunk_number)


class Wall(Tile):
    """ Блок кирпичной стены """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 image, pos_x: int, pos_y: int, chunk_number) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param tile_images: Словарик с изображениями всех блоков
        :param image_name: Название изображения
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(tiles_group, all_sprites, image, pos_x, pos_y,
                         chunk_number)


class Box(Tile):
    """ Блок с коробкой """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 image, pos_x: int, pos_y: int, chunk_number,
                 max_hp=5, is_key_object=False) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param tile_images: Словарик с изображениями всех блоков
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(tiles_group, all_sprites, image, pos_x, pos_y,
                         chunk_number)
        # Прочность блока
        self.is_key_object = is_key_object
        self.type = 4
        self.max_hp = max_hp
        self.hp = self.max_hp
        self.y += 1

    def pin_to_ground(self, sprite_group):
        for sprite in sprite_group:
            if sprite != self:
                if sprite.rect.collidepoint(
                        self.rect.midbottom
                ):
                    break
        else:
            self.y += 5
            self.rect.y += 5

    def draw_health_scale(self, screen, x, y):
        pygame.draw.rect(screen, '#2b2b2b', pygame.Rect(
            x, y, KEY_OBJECT_HEALTH_SCALE_WIDTH,
            KEY_OBJECT_HEALTH_SCALE_HEIGTH
        ))
        pygame.draw.rect(screen, '#cb7043', pygame.Rect(
            x + KEY_OBJECT_HEALTH_SCALE_BORDER,
            y + KEY_OBJECT_HEALTH_SCALE_BORDER,
            (KEY_OBJECT_HEALTH_SCALE_WIDTH -
             KEY_OBJECT_HEALTH_SCALE_BORDER * 2) * (self.hp / self.max_hp),
            KEY_OBJECT_HEALTH_SCALE_HEIGTH -
            KEY_OBJECT_HEALTH_SCALE_BORDER * 2
        ))


class Chunk:
    def __init__(self, tile_images, enemy_images, x, y, chunk_map, level_x):
        self.x, self.y = x, y
        # Все спрайты
        self.all_sprites = pygame.sprite.Group()
        # Спрайты коробок
        self.boxes_group = pygame.sprite.Group()
        # Спрайты кирпичных блоков
        self.bricks_group = pygame.sprite.Group()
        # Группа фантомных блоков (задний фон и украшения)
        self.phantom_group = pygame.sprite.Group()
        # Спрайты монеток
        self.coins_group = pygame.sprite.Group()
        # Спрайты врагов
        self.enemies_group = pygame.sprite.Group()
        for y, row in enumerate(chunk_map):
            for x, elem in enumerate(row[0]):
                # Тут те тайлы, котрые не рушатся, создаётся соответствующий
                # спрайт и добавляется в группу
                if elem in ('w', 's', 'l', 'd', 'L', '^', 'D'):
                    Wall(
                        self.bricks_group, self.all_sprites,
                        tile_images[elem], x + self.x * 8, y + self.y * 8,
                                           self.x + self.y * level_x,
                    )
                elif elem in ('#', '_', '-', '*', '/', '0', '1', '2', '3',
                              '4', '5', '6', '6', '7', '8', '9', 'r',
                              'а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з',
                              'и', 'й', 'к', 'л', 'м', 'н', 'о', 'п', 'р',
                              'с', 'т', 'у', 'ф', 'х', 'ц', 'ч', 'ш', 'щ'):
                    PhantomTile(
                        self.phantom_group, self.all_sprites,
                        tile_images[elem], x + self.x * 8, y + self.y * 8,
                                           self.x + self.y * level_x
                    )
                elif elem in ('b', 'B', '!'):
                    Box(
                        self.boxes_group, self.all_sprites,
                        tile_images[elem], x + self.x * 8, y + self.y * 8,
                                           self.x + self.y * level_x,
                        max_hp=10 if elem == '!' else 5,
                        is_key_object=elem == '!'
                    )
                elif elem == 'o':
                    Enemy(
                        [self.enemies_group, self.all_sprites],
                        enemy_images[0], x + self.x * 8, y + self.y * 8,
                                         self.x + self.y * level_x,
                        is_static=True
                    )
                elif elem == 'O':
                    Enemy([self.enemies_group, self.all_sprites],
                          enemy_images[0], x + self.x * 8, y + self.y * 8,
                          self.x + self.y * level_x)
                elif elem == 'h':
                    HeavyEnemy(
                        [self.enemies_group, self.all_sprites],
                        enemy_images[1], x + self.x * 8, y + self.y * 8,
                                         self.x + self.y * level_x,
                        is_static=True
                    )
                elif elem == 'H':
                    HeavyEnemy([self.enemies_group, self.all_sprites],
                               enemy_images[1], x + self.x * 8,
                               y + self.y * 8, self.x + self.y * level_x)
                elif elem == 'a':
                    ArmoredEnemy(
                        [self.enemies_group, self.all_sprites],
                        enemy_images[2], x + self.x * 8, y + self.y * 8,
                                         self.x + self.y * level_x,
                        is_static=True
                    )
                elif elem == 'A':
                    ArmoredEnemy([self.enemies_group, self.all_sprites],
                                 enemy_images[2], x + self.x * 8,
                                 y + self.y * 8, self.x + self.y * level_x)
                elif elem == 'm':
                    MarksmanEnemy(
                        [self.enemies_group, self.all_sprites],
                        enemy_images[3], x + self.x * 8, y + self.y * 8,
                                         self.x + self.y * level_x,
                        is_static=True
                    )
                elif elem == 'M':
                    MarksmanEnemy(
                        [self.enemies_group, self.all_sprites],
                        enemy_images[3], x + self.x * 8, y + self.y * 8,
                                         self.x + self.y * level_x
                    )

    def render(self, screen, camera, frame, player_group, shot_sounds,
               bullet_group, all_blocks_group, bullet_image):
        # Тут пришлось сделать так, а не методом draw для группы спрайтов,
        # чтобы сохранить начальные координаты спрайтов, иначе из-за
        # особенностей камеры всё съезжает и получаются пропасти между чанками
        for enemy in self.enemies_group:
            enemy.update(camera, frame)
            if enemy.ray.check_collide_with_player(player_group):
                enemy.attack_player = True
                enemy.current_image_idx = 0
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
                    if enemy.direction == DIRECTION_LEFT:
                        x = enemy.x - BULLET_WIDTH
                    else:
                        x = enemy.x + enemy.rect.w
                    if enemy.ammo:
                        if enemy.type == 0:
                            shot_sounds[0].play()
                        elif enemy.type == 1:
                            shot_sounds[1].play()
                        elif enemy.type == 2:
                            shot_sounds[2].play()
                        elif enemy.type == 3:
                            shot_sounds[3].play()
                        Bullet(bullet_group, bullet_image,
                               enemy.direction, x,
                               enemy.y + enemy.rect.h // 2,
                               is_enemy_bullet=True, damage=enemy.damage)
                        enemy.timer = enemy.shot_delay
                        enemy.ammo -= 1
                    else:
                        enemy.timer = enemy.recharge_timer
                        enemy.ammo = enemy.clip_size
                    enemy.is_shoot = False
                else:
                    enemy.timer -= 1
                    if enemy.timer == 0:
                        enemy.is_shoot = True

        for sprite in self.all_sprites:
            sprite.rect.x = sprite.x - camera.x + camera.dx
            sprite.rect.y = sprite.y - camera.y + camera.dy

        self.phantom_group.draw(screen)
        self.bricks_group.draw(screen)

        target_group = pygame.sprite.Group()
        target_group.add(self.boxes_group)
        target_group.add(self.bricks_group)
        for box in self.boxes_group:
            box.pin_to_ground(target_group)
            if box.is_key_object:
                box.draw_health_scale(
                    screen, box.rect.x - 25, box.rect.y - 20
                )
        self.boxes_group.draw(screen)

        for enemy in self.enemies_group:
            enemy.check_collision_sides(all_blocks_group)
            if not enemy.collide_list[7]:
                if enemy.collide_list[2]:
                    dx = 1
                elif enemy.collide_list[3]:
                    dx = -1
                else:
                    dx = 0
                enemy.x += dx
                enemy.y += 5
                enemy.ray.x += dx
                enemy.ray.y += 5
                enemy.ray.rect.x = enemy.ray.x - camera.x + camera.dx
                enemy.ray.rect.y = enemy.ray.y - camera.y + camera.dy
            enemy.draw_health_scale(
                screen, enemy.rect.x + (
                    10 if enemy.direction == DIRECTION_LEFT else -10
                ),
                        enemy.rect.y - 10
            )

        for coin in self.coins_group:
            player = pygame.sprite.spritecollide(coin, player_group, False)
            if pygame.sprite.spritecollideany(coin, player_group):
                player[0].coins += coin.cost
                coin.selection_sound.play()
                coin.kill()

            if pygame.sprite.spritecollideany(coin, self.boxes_group):
                coin.y -= 7
                coin.rect.y -= 5
            if coin.counter == 2:
                coin.update()
                coin.counter = 0
            else:
                coin.counter += 1
        self.coins_group.draw(screen)
        self.enemies_group.draw(screen)


class Camera:
    """ Камера """

    def __init__(self, target) -> None:
        """
        :param field_size: размеры уровня
        """
        self.target = target
        self.x = 0
        self.y = 0
        self.dx = -(self.target.rect.x +
                    self.target.rect.w // 2 - WIDTH // 2)
        self.dy = -(self.target.rect.y +
                    self.target.rect.h // 2 - HEIGHT // 1.4)

    def update(self, dx=0, dy=0):
        self.x += dx
        self.y += dy
        self.target.x += dx
        self.target.y += dy


class Entity(pygame.sprite.Sprite):
    """ Сущность """

    def __init__(self, sprite_groups,
                 entity_images,
                 pos_x: int, pos_y: int, max_hp=1,
                 is_key_object=False) -> None:
        """
        :param entity_group: Группа, куда будет добавлена сущность
        :param entity_image: Изображение сущности
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(*sprite_groups)
        self.is_key_object = is_key_object
        self.grid_x = pos_x
        self.grid_y = pos_y
        self.max_hp = max_hp
        self.hp = max_hp
        self.x = self.grid_x * TILE_WIDTH + 24
        self.y = self.grid_y * TILE_HEIGHT + 2
        self.collide_list = [False for _ in range(8)]
        self.current_image_idx = 0
        self.images = entity_images
        # Изображение сущности
        self.image = entity_images[self.current_image_idx]
        # Размещаем сущность на экране
        self.rect = self.image.get_rect().move(self.x, self.y)

    def check_collision_sides(self, sprite_group):
        """ Проверяем столкновение игрока с группой спрайтов, при это
        получая информацию о том, какими точками спрайт игрока
        соприкасается с другими спрайтами

        """
        self.collide_list = [False for _ in range(8)]

        for sprite in sprite_group:
            # Углы
            if not self.collide_list[0]:
                self.collide_list[0] = sprite.rect.collidepoint(
                    self.rect.topleft
                )
            if not self.collide_list[1]:
                self.collide_list[1] = sprite.rect.collidepoint(
                    self.rect.topright
                )
            if not self.collide_list[2]:
                self.collide_list[2] = sprite.rect.collidepoint(
                    self.rect.bottomleft
                )
            if not self.collide_list[3]:
                self.collide_list[3] = sprite.rect.collidepoint(
                    self.rect.bottomright
                )

            # Грани
            if not self.collide_list[4]:
                self.collide_list[4] = sprite.rect.collidepoint(
                    self.rect.midleft
                )
            if not self.collide_list[5]:
                self.collide_list[5] = sprite.rect.collidepoint(
                    self.rect.midright
                )
            if not self.collide_list[6]:
                self.collide_list[6] = sprite.rect.collidepoint(
                    self.rect.midtop
                )
            if not self.collide_list[7]:
                self.collide_list[7] = sprite.rect.collidepoint(
                    self.rect.midbottom
                )

    def draw_health_scale(self, screen, x, y):
        pygame.draw.rect(screen, '#2b2b2b', pygame.Rect(
            x, y, HEALTH_SCALE_WIDTH, HEALTH_SCALE_HEIGTH
        ))
        pygame.draw.rect(screen, '#cd3030', pygame.Rect(
            x + HEALTH_SCALE_BORDER, y + HEALTH_SCALE_BORDER,
            (HEALTH_SCALE_WIDTH - HEALTH_SCALE_BORDER * 2) *
            (self.hp / self.max_hp),
            HEALTH_SCALE_HEIGTH - HEALTH_SCALE_BORDER * 2
        ))


class Player(Entity):
    """ Игрок """

    def __init__(self, sprite_groups,
                 player_images,
                 pos_x: int, pos_y: int) -> None:
        """
        :param player_group: Групп, куда будет добавлен игрок
        :param all_sprites: Все спрайты
        :param player_image: Изображение игрока
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(sprite_groups, player_images,
                         pos_x, pos_y)

        # Подключаемся к базе данных
        self.con = sqlite3.connect('DataBase.sqlite')
        self.cur = self.con.cursor()

        self.coins = self.cur.execute(
            "SELECT Coins FROM Player_data"
        ).fetchone()[0]

        self.damage = self.cur.execute(
            "SELECT Damage FROM Player_data"
        ).fetchone()[0]

        # HP игрока
        self.max_hp = self.cur.execute(
            'SELECT HP FROM Player_data'
        ).fetchone()[0]
        self.hp = self.max_hp
        # Щит игрока
        self.max_shield = self.cur.execute(
            'SELECT Shields FROM Player_data'
        ).fetchone()[0]
        self.shield = self.max_shield
        # Таймер перезарядки щита
        self.shield_recharge = 0
        # Сколько патронов в обойме
        self.clip_size = self.cur.execute(
            'SELECT Ammo FROM Player_data'
        ).fetchone()[0]
        self.ammo = self.clip_size
        # Скорость стерльбы
        self.shot_delay = self.cur.execute(
            'SELECT Shot_delay FROM Player_data'
        ).fetchone()[0]
        self.timer = 0
        # Таймер перезарядки
        self.recharge_timer = 0
        # Направление, куда игрок смотрит
        self.direction: Literal[0, 1] = DIRECTION_RIGHT
        # Закрываем подключение к бд
        self.con.close()


class Enemy(Entity):
    """Враг"""

    def __init__(self, sprite_groups, enemy_images,
                 pos_x: int, pos_y: int,
                 chunk_number,
                 is_static=False, max_distance=150,
                 direction=DIRECTION_LEFT) -> None:
        """
        :param enemies_group: Группа, куда будет добавлен враг
        :param all_sprites: Все спрайты
        :param enemy_image: Изображение врага
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :key direction: направление врага
        """
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y)

        # Изменение изображения врага в зависимости стороны, в которую он
        # смотрит
        if direction == DIRECTION_LEFT:
            self.image = pygame.transform.flip(
                enemy_images[self.current_image_idx], True, False
            )

        self.chunk_number = chunk_number

        self.type = 0
        self.x -= 24
        # HP врага
        self.max_hp = 5
        self.hp = self.max_hp
        self.is_static = is_static
        # Пройденный промежуток px
        self.distance = 0
        self.max_distance = max_distance
        # Скорость
        self.speed = 1
        # Направление врага
        self.direction = direction
        # Флаг для определения логики врага
        self.attack_player = False
        # Флаг, для создания пули
        self.is_shoot = True
        # Значение таймера
        self.timer = 0
        self.shot_delay = 70
        self.clip_size = 5
        self.ammo = self.clip_size
        self.recharge_timer = 120
        # Таймер для задержки атаки
        self.attack_timer = 0
        self.damage = 2
        # Луч врага
        self.ray = Ray(self.direction,
                       self.x + self.rect.w,
                       self.y + self.rect.h // 2)

    def update(self, camera, frame) -> None:
        """Перемещение врага"""
        # Определяем направление движения врага
        if not self.is_static:
            if not self.attack_player:
                if self.direction and not any(
                        (
                                self.collide_list[5],
                                (
                                        not self.collide_list[7] and
                                        self.collide_list[3]
                                )
                        )
                ):
                    self.x += self.speed
                    self.ray.x += self.speed
                    if frame % 5 == 0:
                        self.current_image_idx += 1
                        if self.current_image_idx == len(self.images):
                            self.current_image_idx = 0
                elif not any(
                        (
                                self.collide_list[4],
                                (
                                        not self.collide_list[7] and
                                        self.collide_list[2]
                                )
                        )
                ):
                    self.x -= self.speed
                    self.ray.x -= self.speed
                    if frame % 5 == 0:
                        self.current_image_idx += 1
                        if self.current_image_idx == len(self.images):
                            self.current_image_idx = 0
        self.distance += self.speed

        # Меняем направление движения и изображение врага, если враг прошел
        # 150px
        if self.distance >= self.max_distance:
            if self.direction:
                self.direction = DIRECTION_LEFT
                self.ray.x -= self.ray.rect.w
            else:
                self.direction = DIRECTION_RIGHT
                self.ray.x += self.ray.rect.w
            # Обнуляем дистанцию
            self.distance = 0
        if self.direction == DIRECTION_RIGHT:
            self.image = self.images[self.current_image_idx]
        else:
            self.image = pygame.transform.flip(
                self.images[self.current_image_idx], True, False
            )
        self.ray.rect.x = self.ray.x - camera.x + camera.dx
        self.ray.rect.y = self.ray.y - camera.y + camera.dy


class HeavyEnemy(Enemy):
    def __init__(self, sprite_groups, enemy_images,
                 pos_x: int, pos_y: int,
                 chunk_number,
                 is_static=False, max_distance=100,
                 direction=DIRECTION_LEFT) -> None:
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y,
                         chunk_number, is_static, max_distance, direction)
        self.type = 1
        self.max_hp = 20
        self.hp = self.max_hp
        self.damage = 1
        self.clip_size = 10
        self.ammo = self.clip_size
        self.shot_delay = 25


class ArmoredEnemy(Enemy):
    def __init__(self, sprite_groups, enemy_images,
                 pos_x: int, pos_y: int,
                 chunk_number,
                 is_static=False, max_distance=150,
                 direction=DIRECTION_LEFT) -> None:
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y,
                         chunk_number, is_static, max_distance, direction)
        self.type = 2
        self.max_hp = 7
        self.hp = self.max_hp
        self.clip_size = 2
        self.ammo = self.clip_size
        self.shot_delay = 35
        self.damage = 7


class MarksmanEnemy(Enemy):
    def __init__(self, sprite_groups, enemy_images,
                 pos_x: int, pos_y: int, chunk_number,
                 is_static=False, max_distance=70,
                 direction=DIRECTION_LEFT) -> None:
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y,
                         chunk_number, is_static, max_distance, direction)
        self.type = 3
        self.max_hp = 7
        self.hp = self.max_hp
        self.clip_size = 1
        self.ammo = self.clip_size
        self.shot_delay = 160
        self.damage = 14
        self.ray.rect.w += 150
        if self.direction == DIRECTION_RIGHT:
            self.ray.x += 150
        else:
            self.ray.x -= 150


class Bullet(pygame.sprite.Sprite):
    """ Снаряд """

    def __init__(self, bullet_group: pygame.sprite.Group,
                 bullet_image: pygame.Surface,
                 user_direction: Literal[0, 1],
                 pos_x, pos_y, is_enemy_bullet=False, damage=1) -> None:
        """
        :param bullet_group: Группа, куда будет добавлен снаряд
        :param all_sprites: Все спрайты
        :param bullet_image: Изображение снаряда
        :param user_direction: Направление игрока (оно же будет и для снаряда)
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :key is_enemy_bullet: флаг для определения пули врага и игрока
        """
        super().__init__(bullet_group)
        self.damage = damage
        # Счетчик дальности полета
        self.destroy_timer = 45
        # Изображение снаряда
        self.image = bullet_image
        self.x = pos_x
        self.y = pos_y
        # Размещаем снаряд на экране
        self.rect = self.image.get_rect()
        self.direction = user_direction
        # Изменение координаты пули
        self.d_x = (1 if self.direction == DIRECTION_RIGHT else -1) * \
                   BULLET_SPEED
        # Флаг для различия пули игрока и пули врага
        self.is_enemy_bullet = is_enemy_bullet

    def update(self, player, destructible_groups, indestructible_groups,
               destroy_sounds, hit_sounds, player_group, camera,
               screen, drop_images, selection_sound, chunks):
        """ Перемещение снаряда """
        self.destroy_timer -= 1
        if not self.destroy_timer:
            hit_sounds[0].play()
            self.kill()
        # Определяем, в каком направлении передвигать снаряд
        self.x += self.d_x
        self.rect.x = self.x - camera.x + camera.dx
        self.rect.y = self.y - camera.y + camera.dy

        # Список, со всеми спрайтами, в которые ударился снаряд
        destructible_sprites_hit_list = pygame.sprite.spritecollide(
            self, destructible_groups, False
        )
        # Если есть хоть один, такой спрайт, то удаляем его вместе со
        # снарядом.
        if destructible_sprites_hit_list:
            if not self.is_enemy_bullet:
                if destructible_sprites_hit_list[0].type == 2:
                    if destructible_sprites_hit_list[0].direction != \
                            self.direction:
                        hit_sounds[1].play()
                        self.kill()
                        return False
                destructible_sprites_hit_list[0].hp -= player.damage
                if destructible_sprites_hit_list[0].hp <= 0:
                    sprite_type = destructible_sprites_hit_list[0].type
                    if sprite_type in (0, 1, 2, 3):
                        destroy_sounds[0].play()
                    elif sprite_type in (4,):
                        destroy_sounds[1].play()
                    chance = random()
                    coin_type = None
                    if chance <= 0.15:
                        coin_type = 2
                    elif 0.15 < chance <= 0.4:
                        coin_type = 1
                    elif 0.4 < chance <= 0.7:
                        coin_type = 0
                    if coin_type is not None:
                        Coin(
                            selection_sound, drop_images[:3], coin_type, 8, 1,
                            destructible_sprites_hit_list[0].x + 5,
                            destructible_sprites_hit_list[0].y + 5,
                            chunks[destructible_sprites_hit_list[
                                0].chunk_number].coins_group,
                            chunks[destructible_sprites_hit_list[
                                0].chunk_number].all_sprites
                        )
                    if destructible_sprites_hit_list[0].is_key_object:
                        return True
                    destructible_sprites_hit_list[0].kill()
            if destructible_sprites_hit_list[0].type in (4,) or \
                    not self.is_enemy_bullet:
                hit_sounds[0].play()
                self.kill()

        # Если снаряд столкнулся с каким-то из спрайтов и этот спрайт не
        # игрок, то удаляем снаряд
        if pygame.sprite.spritecollideany(self, indestructible_groups) and \
                not pygame.sprite.spritecollideany(self, player_group):
            hit_sounds[0].play()
            self.kill()
        # Если снаряд столкнулся с каким-то из спрайтов и этот спрайт не
        # игрок, то удаляем снаряд
        if pygame.sprite.spritecollideany(self, indestructible_groups) and \
                not pygame.sprite.spritecollideany(self, player_group):
            hit_sounds[1].play()
            self.kill()

        # Если пуля вражеская, то проверяем пересечение со спрайтом игрока и
        # отнимаем либо щит, либо хп
        if self.is_enemy_bullet:
            if pygame.sprite.spritecollideany(self, player_group):
                for player in player_group:
                    if player.shield > 0:
                        player.shield -= self.damage
                        if player.shield < 0:
                            player.shield = 0
                    else:
                        player.hp -= self.damage
                    if not player.shield_recharge:
                        player.shield_recharge = 150
                self.kill()

        screen.blit(self.image, (self.rect.x, self.rect.y))
        return False


class Button:
    """Класс для создания кнопок"""

    def __init__(self, width, height, pos_x, pos_y,
                 active_image, inactive_image, text,
                 action=None, font_size=20):
        self.width = width
        self.height = height
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.active_image = active_image
        self.inactive_image = inactive_image
        self.text = text
        self.action = action
        self.is_visible = True
        self.font_size = font_size

    def draw(self, screen):
        """Отрисовка кнопок"""
        if self.is_visible:
            mouse = pygame.mouse.get_pos()
            click = pygame.mouse.get_pressed()

            if (self.pos_x < mouse[0] < self.pos_x + self.width) and \
                    (self.pos_y < mouse[1] < self.pos_y + self.height):
                screen.blit(self.active_image, (self.pos_x, self.pos_y))

                if click[0] == 1 and self.action is not None:
                    # soundButton.play()
                    pygame.time.delay(300)
                    self.action()

                arrow_idx = 1
            else:
                screen.blit(self.inactive_image, (self.pos_x, self.pos_y))
                arrow_idx = 0
            self.print_text(screen, self.text, font_size=self.font_size)
            return arrow_idx
        return 0

    def print_text(self, screen, text: str,
                   font_color=(255, 255, 255),
                   font_name: str = 'bahnschrift',
                   font_size: int = 30):
        # Выбранный шрифт
        font = pygame.font.SysFont(font_name, font_size)
        # Отрисовываем на экране выбранный текст
        text_surface = font.render(text, True, font_color)
        text_rect = text_surface.get_rect(
            center=(self.pos_x + self.width / 2,
                    self.pos_y + self.height / 2 + 2)
        )
        screen.blit(text_surface, text_rect)


class Ray(pygame.sprite.Sprite):
    """Луч для проверки наличия спрайта игрока в поле зрения врага"""

    def __init__(self, direction: Literal[0, 1],
                 pos_x: int, pos_y: int) -> None:
        """
        :param direction: направление луча
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__()
        if direction:
            self.x = pos_x
        else:
            self.x = pos_x - 300
        self.y = pos_y
        self.rect = pygame.Rect(self.x, self.y, 300, 1)
        # Направление луча
        self.direction = direction

    def check_collide_with_player(
            self, player_group: pygame.sprite.Group
    ) -> bool:
        """Проверка столкновения с игроком"""
        if pygame.sprite.spritecollideany(self, player_group):
            return True
        return False


class ImprovementScalesHandler:
    pass


class ImprovementScales:

    def __init__(
            self, scale_objects, active_upgrade_button_image,
            inactive_upgrade_button_image, player, cur, con, upgrade_sound
    ):

        self.scale_objects = scale_objects
        self.upgrade_buttons = []

        for index in range(len(self.scale_objects)):
            self.upgrade_buttons.append(Button(
                21, 21, 472, 215 + index * 48,
                active_upgrade_button_image,
                inactive_upgrade_button_image,
                '', partial(
                    self.upgrade, index, player, cur, con, upgrade_sound
                )
            ))
            if scale_objects[index].current_cost == 'max':
                self.upgrade_buttons[index].is_visible = False

    def upgrade(self, index, player, cur, con, upgrade_sound):
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


class ImprovementScale:

    def __init__(self, pos_x, pos_y, width, height,
                 border_width, scale_name, cur):
        self.scale_name = scale_name

        self.stage = cur.execute(
            f'SELECT {scale_name} FROM Scales'
        ).fetchone()[0]

        self.external_rect = pygame.Rect(
            pos_x, pos_y, width * 0.2 * self.stage, height
        )
        self.internal_rect = pygame.Rect(
            pos_x + border_width, pos_y + border_width,
            width * 0.2 * self.stage - (border_width * 2),
            height - (border_width * 2)
        )

        self.current_cost = cur.execute(
            f'SELECT {scale_name} FROM Scales_costs WHERE Id = '
            f'{self.stage + 1}'
        ).fetchone()[0]

        self.delta_value = cur.execute(
            f'SELECT {scale_name} FROM Scales_delta'
        ).fetchone()[0]

        self.max_width = width
