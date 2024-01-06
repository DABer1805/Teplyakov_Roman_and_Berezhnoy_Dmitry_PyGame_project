from random import randrange

import pygame

from constants import TILE_WIDTH, TILE_HEIGHT, WIDTH, HEIGHT, \
    DIRECTION_RIGHT, BULLET_SPEED, DIRECTION_LEFT

from typing import Literal


class AnimatedSprite(pygame.sprite.Sprite):
    def __init__(self, sheet, columns, rows, x, y, target_group, all_sprites):
        super().__init__(target_group, all_sprites)
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.counter = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x, y)

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


class Tile(pygame.sprite.Sprite):
    """ Базовый класс блоков """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group) -> None:
        """
        :param tiles_group: Группа, куда будет добавлен блок
        :param all_sprites: Все спрайты
        """
        super().__init__(tiles_group, all_sprites)



class PhantomTile(Tile):
    """ Блок фантомного спрайта """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 tile_images: dict[str, pygame.Surface],
                 image_name: str,
                 pos_x: int, pos_y: int) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param tile_images: Словарик с изображениями всех блоков
        :param image_name: Название изображения
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(tiles_group, all_sprites)
        # Изображение спрайта
        self.image = tile_images[image_name]
        # Размещаем на экране текущий блок
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)


class Wall(Tile):
    """ Блок кирпичной стены """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 tile_images: dict[str, pygame.Surface],
                 image_name: str,
                 pos_x: int, pos_y: int) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param tile_images: Словарик с изображениями всех блоков
        :param image_name: Название изображения
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(tiles_group, all_sprites)
        # Изображение спрайта
        self.image = tile_images[image_name]
        # Размещаем на экране текущий блок
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)


class Box(Tile):
    """ Блок с коробкой """

    def __init__(self, tiles_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 tile_images: dict[str, pygame.Surface],
                 image_name: str,
                 pos_x: int, pos_y: int) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param tile_images: Словарик с изображениями всех блоков
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(tiles_group, all_sprites)
        # Изображение спрайта
        self.image = tile_images[image_name]
        # Размещаем на экране текущий блок
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)
        # Прочность блока
        self.hp = 5


class Camera:
    """ Камера """

    def __init__(self, field_size) -> None:
        """
        :param field_size: размеры уровня
        """
        # Смещение по оси x
        self.dx = 0
        # Смещение по оси y
        self.dy = 0
        # Размеры уровня
        self.field_size = (field_size[0], field_size[1] - 1)

    # сдвинуть объект obj на смещение камеры
    def apply(self, obj):
        obj.rect.x += self.dx
        obj.rect.y += self.dy

    # позиционировать камеру на объекте target
    def update(self, target, collide_side):
        # Столкнулся ли персонаж с каким-либо из спрайтов блоков
        if not collide_side:
            self.dx = -(target.rect.x + target.rect.w // 2 - WIDTH // 2)
            self.dy = -(target.rect.y + target.rect.h // 2 - HEIGHT // 1.4)
        else:
            self.dx, self.dy = 0, 0


class Entity(pygame.sprite.Sprite):
    """ Сущность """

    def __init__(self, entity_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 entity_image: pygame.Surface,
                 pos_x: int, pos_y: int) -> None:
        """
        :param entity_group: Группа, куда будет добавлена сущность
        :param all_sprites: Все спрайты
        :param entity_image: Изображение сущности
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(entity_group, all_sprites)
        # Изображение сущности
        self.image = entity_image
        # Размещаем сущность на экране
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x + 15,
                                               TILE_HEIGHT * pos_y + 1)


class Player(Entity):
    """ Игрок """

    def __init__(self, player_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 player_image: pygame.Surface, hp: int,
                 pos_x: int, pos_y: int) -> None:
        """
        :param player_group: Групп, куда будет добавлен игрок
        :param all_sprites: Все спрайты
        :param player_image: Изображение игрока
        :param hp: HP игрока
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(player_group, all_sprites, player_image,
                         pos_x, pos_y)
        # HP игрока
        self.hp = hp
        # Сколько патронов в обойме
        self.ammo = 5
        # Таймер перезарядки
        self.recharge_timer = 0
        # Направление, куда игрок смотрит
        self.direction: Literal[0, 1] = DIRECTION_RIGHT


class Enemy(Entity):
    """Враг"""

    def __init__(self, enemies_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 enemy_image: pygame.Surface,
                 pos_x: int, pos_y: int, direction=DIRECTION_LEFT) -> None:
        """
        :param enemies_group: Группа, куда будет добавлен враг
        :param all_sprites: Все спрайты
        :param enemy_image: Изображение врага
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :key direction: направление врага
        """
        super().__init__(enemies_group, all_sprites, enemy_image,
                         pos_x, pos_y)

        # Изменение изображения врага в зависимости стороны, в которую он
        # смотрит
        if direction == DIRECTION_LEFT:
            self.image = pygame.transform.flip(enemy_image, True, False)

        # HP врага
        self.hp = 3
        # Фигура врага (чтоб стоял ровно на земле)
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x + 15,
                                               TILE_HEIGHT * pos_y + 1)
        # Пройденный промежуток px
        self.distance = 0
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
        # Таймер для задержки атаки
        self.attack_timer = 0
        # Луч врага
        self.ray = None

    def update(self, direction) -> None:
        """Перемещение врага"""
        # Определяем направление движения врага
        if self.direction:
            self.rect.x += self.speed
        else:
            self.rect.x -= self.speed
        # Добавляем в пройденную дистанцию
        self.distance += self.speed
        # Меняем направление движения и изображение врага, если враг прошел
        # 150px
        if self.distance >= 150:
            if self.direction:
                self.direction = DIRECTION_LEFT
            else:
                self.direction = DIRECTION_RIGHT
            # Отражаем изображение врага
            self.image = pygame.transform.flip(self.image, True, False)
            # Обнуляем дистанцию
            self.distance = 0


class Bullet(pygame.sprite.Sprite):
    """ Снаряд """

    def __init__(self, bullet_group: pygame.sprite.Group,
                 all_sprites: pygame.sprite.Group,
                 bullet_image: pygame.Surface,
                 user_direction: Literal[0, 1],
                 pos_x, pos_y, is_enemy_bullet=False) -> None:
        """
        :param bullet_group: Группа, куда будет добавлен снаряд
        :param all_sprites: Все спрайты
        :param bullet_image: Изображение снаряда
        :param user_direction: Направление игрока (оно же будет и для снаряда)
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :key is_enemy_bullet: флаг для определения пули врага и игрока
        """
        super().__init__(bullet_group, all_sprites)
        # Изображение снаряда
        self.image = bullet_image
        # Размещаем снаряд на экране
        self.rect = self.image.get_rect().move(pos_x, pos_y)
        # Направление снаряда
        self.direction = user_direction
        # Флаг для различия пули игрока и пули врага
        self.is_enemy_bullet = is_enemy_bullet

    def update(self, destructible_groups, indestructible_groups, coin_data,
               destroy_sound, hit_sound, player_group):
        """ Перемещение снаряда """
        # Определяем, в каком направлении передвигать снаряд
        if self.direction == DIRECTION_RIGHT:
            self.rect.x += BULLET_SPEED
        else:
            self.rect.x -= BULLET_SPEED

        # Пробегаемся по переданным группам РАЗРУШАЕМЫХ спрайтов, в которых
        # будет проверяться столкновение
        for destructible_group in destructible_groups:
            # Список, со всеми спрайтами, в которые ударился снаряд
            destructible_sprites_hit_list = pygame.sprite.spritecollide(
                self, destructible_group, False
            )
            # Если есть хоть один, такой спрайт, то удаляем его вместе со
            # снарядом
            if destructible_sprites_hit_list and not self.is_enemy_bullet:
                destructible_sprites_hit_list[0].hp -= 1
                if not destructible_sprites_hit_list[0].hp:
                    destroy_sound.play()
                    if randrange(100) < coin_data['percent']:
                        AnimatedSprite(
                            coin_data['sheet'],
                            coin_data['columns'],
                            coin_data['rows'],
                            destructible_sprites_hit_list[0].rect.x + 5,
                            destructible_sprites_hit_list[0].rect.y + 5,
                            coin_data['coins_group'],
                            coin_data['all_sprites']
                        )
                    destructible_sprites_hit_list[0].kill()
                hit_sound.play()
                self.kill()

        # Пробегаемся по переданным группам НЕ РАЗРУШАЕМЫХ спрайтов,
        # в которых будет проверяться столкновение
        for indestructible_group in indestructible_groups:
            # Если снаряд столкнулся с каким-то из спрайтов и этот спрайт не
            # игрок, то удаляем снаряд
            if pygame.sprite.spritecollideany(self, indestructible_group) and \
                    not pygame.sprite.spritecollideany(self, player_group):
                hit_sound.play()
                self.kill()


class Button:
    """Класс для создания кнопок"""

    def __init__(self, width, height, pos_x, pos_y,
                 active_image, inactive_image, button_name,
                 action=None):
        self.width = width
        self.height = height
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.active_image = active_image
        self.inactive_image = inactive_image
        self.button_name = button_name
        self.action = action
        self.is_visible = True

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
            return arrow_idx
        return 0


class Ray(pygame.sprite.Sprite):
    """Луч для проверки наличия спрайта игрока в поле зрения врага"""

    def __init__(self, rays_group: pygame.sprite.Group,
                 direction: Literal[0, 1],
                 pos_x: int, pos_y: int) -> None:
        """
        :param rays_group: группа спрайтов лучей
        :param direction: направление луча
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(rays_group)
        # Фигура луча
        if direction:
            self.rect = pygame.Rect(pos_x, pos_y, 300, 1)
        else:
            self.rect = pygame.Rect(pos_x - 300, pos_y, 300, 1)
        # Направление луча
        self.direction = direction

    def check_collide_with_player(self,
                                  player_group: pygame.sprite.Group) -> bool:
        """Проверка столкновения с игроком"""
        if pygame.sprite.spritecollideany(self, player_group):
            del self
            return True
        return False
