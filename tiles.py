from pygame.sprite import Sprite, Group

from constants import TILE_WIDTH, TILE_HEIGHT, KEY_OBJECT_HEALTH_SCALE_WIDTH, \
    KEY_OBJECT_HEALTH_SCALE_HEIGTH, KEY_OBJECT_HEALTH_SCALE_BORDER
from pygame.draw import rect
from pygame import Rect


class Tile(Sprite):
    """ Базовый класс блоков """

    def __init__(self, tiles_group: Group,
                 all_sprites: Group,
                 image, pos_x: int, pos_y: int, chunk_number: int) -> None:
        """
        :param tiles_group: Группа, куда будет добавлен блок
        :param all_sprites: Все спрайты
        :param image: изображение блока
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :param chunk_number:
        """
        super().__init__(tiles_group, all_sprites)
        # Изображение спрайта
        self.image = image
        # Размещаем на экране текущий блок
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)
        # Координаты
        self.x = self.rect.x
        self.y = self.rect.y
        # Номер чанка
        self.chunk_number = chunk_number


class PhantomTile(Tile):
    """ Блок фантомного спрайта """

    def __init__(self, tiles_group: Group, all_sprites: Group, image,
                 pos_x: int, pos_y: int, chunk_number) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        """
        super().__init__(tiles_group, all_sprites, image, pos_x, pos_y,
                         chunk_number)


class Wall(Tile):
    """ Блок кирпичной стены """

    def __init__(self, tiles_group:Group, all_sprites: Group,
                 image, pos_x: int, pos_y: int, chunk_number: int) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param image: Название изображения
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :param chunk_number: чаек объекта
        """
        super().__init__(tiles_group, all_sprites, image, pos_x, pos_y,
                         chunk_number)


class Box(Tile):
    """ Блок с коробкой """

    def __init__(self, tiles_group: Group, all_sprites: Group,
                 image, pos_x: int, pos_y: int, chunk_number: int,
                 max_hp=5, is_key_object=False) -> None:
        """
        :param tiles_group: Группа, в которую будет добавлен текущий блок
        :param all_sprites: Все спрайты
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :param chunk_number: чаек объекта
        :key is_key_object: флаг для уровней с реактором
        """
        super().__init__(tiles_group, all_sprites, image, pos_x, pos_y,
                         chunk_number)
        # Флаг для уровня с реактором
        self.is_key_object = is_key_object
        # Тип
        self.type = 4
        # Хп
        self.max_hp = max_hp
        self.hp = self.max_hp
        # Координаты по оси
        self.y += 1

    def pin_to_ground(self, sprite_group):
        """Падение на землю"""
        for sprite in sprite_group:
            if sprite != self:
                if sprite.rect.collidepoint(self.rect.midbottom):
                    break
        else:
            self.y += 5
            self.rect.y += 5

    def draw_health_scale(self, screen, x, y):
        """Отрисовка шкалы здоровья"""
        rect(screen, '#2b2b2b', Rect(
            x, y, KEY_OBJECT_HEALTH_SCALE_WIDTH,
            KEY_OBJECT_HEALTH_SCALE_HEIGTH
        ))
        rect(screen, '#cb7043', Rect(
            x + KEY_OBJECT_HEALTH_SCALE_BORDER,
            y + KEY_OBJECT_HEALTH_SCALE_BORDER,
            (KEY_OBJECT_HEALTH_SCALE_WIDTH -
             KEY_OBJECT_HEALTH_SCALE_BORDER * 2) * (self.hp / self.max_hp),
            KEY_OBJECT_HEALTH_SCALE_HEIGTH -
            KEY_OBJECT_HEALTH_SCALE_BORDER * 2
        ))