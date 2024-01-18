from typing import Literal

from constants import DIRECTION_RIGHT, DIRECTION_LEFT, TILE_WIDTH, \
    TILE_HEIGHT, HEALTH_SCALE_WIDTH, HEALTH_SCALE_HEIGTH, HEALTH_SCALE_BORDER
from pygame.sprite import Sprite, Group, spritecollideany
from pygame import Rect
from pygame.draw import rect
from sqlite3 import connect
from pygame.transform import flip


class Entity(Sprite):
    """ Сущность """

    def __init__(self, sprite_groups,
                 entity_images,
                 pos_x: int, pos_y: int, max_hp=1,
                 is_key_object=False) -> None:
        """
        :param sprite_groups: Группы спрайтов, куда будет добавлена сущность
        :param entity_images: Изображения всех видов сущностей
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :key max_hp: максимальное хп
        :key is_key_object: флаг для уровней с реактором
        """
        super().__init__(*sprite_groups)
        # Флаг для уровней с реактором
        self.is_key_object = is_key_object
        # Координаты персонажа в сетке (в тайлах)
        self.grid_x = pos_x
        self.grid_y = pos_y
        # Хп сущности
        self.max_hp = max_hp
        self.hp = max_hp
        # Координаты персонажа в пикселях
        self.x = self.grid_x * TILE_WIDTH + 24
        self.y = self.grid_y * TILE_HEIGHT + 2
        # Список с флагами для проверки соприкосновений с группой спрайтов
        self.collide_list = [False for _ in range(8)]
        # Индекс для получения изображения сущности
        self.current_image_idx = 0
        # Изображения сущностей
        self.images = entity_images
        # Изображение самой сущности
        self.image = entity_images[self.current_image_idx]
        # Размещаем сущность на экране
        self.rect = self.image.get_rect().move(self.x, self.y)

    def check_collision_sides(self, sprite_group):
        """ Проверяем столкновение игрока с группой спрайтов, при этом
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
        """Отрисовка шкалы здоровья"""
        rect(screen, '#2b2b2b', Rect(
            x, y, HEALTH_SCALE_WIDTH, HEALTH_SCALE_HEIGTH
        ))
        rect(screen, '#cd3030', Rect(
            x + HEALTH_SCALE_BORDER, y + HEALTH_SCALE_BORDER,
            (HEALTH_SCALE_WIDTH - HEALTH_SCALE_BORDER * 2) *
            (self.hp / self.max_hp),
            HEALTH_SCALE_HEIGTH - HEALTH_SCALE_BORDER * 2
        ))


class Player(Entity):
    """Игрок"""

    def __init__(self, sprite_groups: tuple,
                 player_images: list, pos_x: int, pos_y: int) -> None:
        """
        :param sprite_groups: Группа, куда будет добавлен игрок
        :param player_images: Изображение игрока
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(sprite_groups, player_images,
                         pos_x, pos_y)

        # Подключаемся к базе данных
        self.con = connect('DataBase.sqlite')
        self.cur = self.con.cursor()

        # Монеты игрока
        self.coins = self.cur.execute(
            "SELECT Coins FROM Player_data"
        ).fetchone()[0]
        # Урон игрока
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
        # Скорость стрельбы
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

    def __init__(self, sprite_groups: list,
                 enemy_images: list, pos_x: int, pos_y: int,
                 chunk_number: int,
                 is_static=False, max_distance=150,
                 direction=DIRECTION_LEFT) -> None:
        """
        :param sprite_groups: Группа, куда будет добавлен враг
        :param enemy_images: Изображения врагов
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :param chunk_number: номер чанка
        :key is_static: флаг для определения движения
        :key max_distance: максимальная дистанция на которую ходит враг в
        одном направлении
        :key direction: направление врага
        """
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y)

        # Изменение изображения врага в зависимости стороны, в которую он
        # смотрит
        if direction == DIRECTION_LEFT:
            self.image = flip(
                enemy_images[self.current_image_idx], True, False
            )
        # номер чанка
        self.chunk_number = chunk_number
        # тип врага
        self.type = 0
        self.x -= 24
        # HP врага
        self.max_hp = 5
        self.hp = self.max_hp
        self.is_static = is_static
        # Пройденный промежуток в px
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
        # Таймер
        self.timer = 0
        # Скорость стрельбы
        self.shot_delay = 70
        # Максимальный объем обоймы
        self.clip_size = 5
        # Патроны
        self.ammo = self.clip_size
        # Таймер перезарядки
        self.recharge_timer = 120
        # Таймер для задержки атаки
        self.attack_timer = 0
        # Урон
        self.damage = 2
        # Луч видимости игрока
        self.ray = Ray(self.direction,
                       self.x + self.rect.w,
                       self.y + self.rect.h // 2)

    def update(self, camera, frame) -> None:
        """Перемещение врага"""
        # Проверка на тип поведения
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
            self.image = flip(
                self.images[self.current_image_idx], True, False
            )
        self.ray.rect.x = self.ray.x - camera.x + camera.dx
        self.ray.rect.y = self.ray.y - camera.y + camera.dy


class HeavyEnemy(Enemy):
    """Тяжелый враг"""

    def __init__(self, sprite_groups: list,
                 enemy_images: list, pos_x: int, pos_y: int,
                 chunk_number: int,
                 is_static=False, max_distance=100,
                 direction=DIRECTION_LEFT) -> None:
        """
            :param sprite_groups: Группа, куда будет добавлен враг
            :param enemy_images: Изображения врагов
            :param pos_x: позиция по оси x
            :param pos_y: позиция по оси y
            :param chunk_number: номер чанка
            :key is_static: флаг для определения движения
            :key max_distance: максимальная дистанция на которую ходит враг в
            одном направлении
            :key direction: направление врага
        """
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y,
                         chunk_number, is_static, max_distance, direction)
        # Тип врага
        self.type = 1
        # Хп врага
        self.max_hp = 20
        self.hp = self.max_hp
        # Урон врага
        self.damage = 1
        # Максимальный объем обоймы
        self.clip_size = 10
        # Патроны
        self.ammo = self.clip_size
        # Скорость стрельбы
        self.shot_delay = 25


class ArmoredEnemy(Enemy):
    """Враг с щитом"""

    def __init__(self, sprite_groups: list,
                 enemy_images: list, pos_x: int, pos_y: int,
                 chunk_number: int,
                 is_static=False, max_distance=150,
                 direction=DIRECTION_LEFT) -> None:
        """
            :param sprite_groups: Группа, куда будет добавлен враг
            :param enemy_images: Изображения врагов
            :param pos_x: позиция по оси x
            :param pos_y: позиция по оси y
            :param chunk_number: номер чанка
            :key is_static: флаг для определения движения
            :key max_distance: максимальная дистанция на которую ходит враг в
            одном направлении
            :key direction: направление врага
        """
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y,
                         chunk_number, is_static, max_distance, direction)
        # Тип врага
        self.type = 2
        # Хп врага
        self.max_hp = 7
        self.hp = self.max_hp
        # Максимальный объем обоймы
        self.clip_size = 2
        # Патроны
        self.ammo = self.clip_size
        # Скорость стрельбы
        self.shot_delay = 35
        # Урон
        self.damage = 7


class MarksmanEnemy(Enemy):
    """Снайпер"""

    def __init__(self, sprite_groups: list,
                 enemy_images: list, pos_x: int, pos_y: int,
                 chunk_number: int,
                 is_static=False, max_distance=70,
                 direction=DIRECTION_LEFT) -> None:
        """
            :param sprite_groups: Группа, куда будет добавлен враг
            :param enemy_images: Изображения врагов
            :param pos_x: позиция по оси x
            :param pos_y: позиция по оси y
            :param chunk_number: номер чанка
            :key is_static: флаг для определения движения
            :key max_distance: максимальная дистанция на которую ходит враг в
            одном направлении
            :key direction: направление врага
        """
        super().__init__(sprite_groups, enemy_images, pos_x, pos_y,
                         chunk_number, is_static, max_distance, direction)
        # Тип врага
        self.type = 3
        # Хп врага
        self.max_hp = 7
        self.hp = self.max_hp
        # Максимальный объем обоймы
        self.clip_size = 1
        # Патроны
        self.ammo = self.clip_size
        # Скорость стрельбы
        self.shot_delay = 160
        # Урон
        self.damage = 14
        # Длина и ширина луча видимости игрока (больше чем у других врагов)
        self.ray.rect.w += 150
        if self.direction == DIRECTION_RIGHT:
            self.ray.x += 150
        else:
            self.ray.x -= 150


class Ray(Sprite):
    """Луч для проверки наличия спрайта игрока в поле зрения врага"""

    def __init__(self, direction: Literal[0, 1],
                 pos_x: int, pos_y: int) -> None:
        """
        :param direction: направление луча
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__()
        # Позиция по оси x
        if direction:
            self.x = pos_x
        else:
            self.x = pos_x - 300
        # Позиция по оси y
        self.y = pos_y
        # Фигура луча
        self.rect = Rect(self.x, self.y, 300, 1)
        # Направление луча
        self.direction = direction

    def check_collide_with_player(
            self, player_group: Group
    ) -> bool:
        """Проверка столкновения с игроком"""
        if spritecollideany(self, player_group):
            return True
        return False
