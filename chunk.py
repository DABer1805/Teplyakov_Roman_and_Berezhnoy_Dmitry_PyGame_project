from random import random

import pygame

from bullets import Bullet

from constants import BULLET_WIDTH
from tiles import *
from entites import *


class Chunk:
    """Чанк"""

    def __init__(
            self, tile_images: dict, enemy_images: list, x: int, y: int,
            chunk_map: list, level_x: int
    ):
        """
        :param tile_images: изображение всех тайлов
        :param enemy_images: изображения всех врагов
        :param x: координата по оси x
        :param y: координата по оси y
        :param chunk_map: карта разбитая на сетку чанков
        :param level_x: длина уровня по оси x
        """
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
                # Тут те тайлы, которые не рушатся, создаётся соответствующий
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

        # Смещение фигуры спрайтов
        for sprite in self.all_sprites:
            sprite.rect.x = sprite.x - camera.x + camera.dx
            sprite.rect.y = sprite.y - camera.y + camera.dy

        # Отрисовка блоков
        self.phantom_group.draw(screen)
        self.bricks_group.draw(screen)

        target_group = pygame.sprite.Group()
        target_group.add(self.boxes_group)
        target_group.add(self.bricks_group)
        # Смещение коробок в воздухе на блоки
        for box in self.boxes_group:
            box.pin_to_ground(target_group)
            if box.is_key_object:
                box.draw_health_scale(
                    screen, box.rect.x - 25, box.rect.y - 20
                )
        # Отрисовка коробок
        self.boxes_group.draw(screen)

        # Перемещение врагов
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
                ), enemy.rect.y - 10
            )

        # Удаление при подборе или смещение и анимация монет
        for coin in self.coins_group:
            player = pygame.sprite.spritecollide(coin, player_group, False)
            if pygame.sprite.spritecollideany(coin, player_group):
                con = connect('DataBase.sqlite')
                cur = con.cursor()
                player[0].coins += coin.cost
                # Перезаписываем поле с монетками в БД
                cur.execute(f"UPDATE Player_data SET Coins = "
                            f"{player[0].coins}")
                con.commit()
                con.close()
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

        # Отрисовка монет
        self.coins_group.draw(screen)
        # Отрисовка врагов
        self.enemies_group.draw(screen)
