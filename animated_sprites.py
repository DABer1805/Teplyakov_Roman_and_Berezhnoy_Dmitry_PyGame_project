from pygame.sprite import Sprite, Group
from pygame import Rect


class AnimatedSprite(Sprite):
    """Класс для анимации монет"""

    def __init__(
            self, sheet, columns: int, rows: int, x: int, y: int,
            target_group: Group,
            all_sprites: Group
    ):
        """
        :param sheet: изображение спрайта
        :param x: позиция по оси x
        :param y: позиция по оси y
        :param target_group: группа спрайтов в которой будут монеты
        :param all_sprites: группа всех спрайтов
        """
        super().__init__(target_group, all_sprites)
        # Фигура объекта
        self.rect = None
        # Координаты
        self.x = x
        self.y = y
        # Кадры
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        # Текущий кадр
        self.cur_frame = 0
        # Счетчик
        self.counter = 0
        # Текущее изображение
        self.image = self.frames[self.cur_frame]

    def cut_sheet(self, sheet, columns, rows) -> None:
        """'Нарезка' кадров, для анимации"""
        self.rect = Rect(0, 0, sheet.get_width() // columns,
                         sheet.get_height() // rows)

        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(Rect(
                    frame_location, self.rect.size)))

    def update(self):
        self.cur_frame = (self.cur_frame + 1) % len(self.frames)
        self.image = self.frames[self.cur_frame]


class Coin(AnimatedSprite):
    """Монеты"""

    def __init__(
            self, selection_sound, sheets, type_of_coin: int, columns: int,
            rows: int,
            x: int, y: int, target_group: Group,
            all_sprites: Group
    ):
        """
        :param selection_sound: звук подбора монеты
        :param sheets: изображения монеты
        :param type_of_coin: тип монеты
        :param x: позиция по оси x
        :param y: позиция по оси y
        :param target_group: группа спрайтов в которой будут монеты
        :param all_sprites: группа всех спрайтов
        """

        super().__init__(sheets[type_of_coin], columns, rows, x, y,
                         target_group, all_sprites)

        # Звук подбора
        self.selection_sound = selection_sound

        # Присваивание цены
        self.cost = None
        if type_of_coin == 0:
            self.cost = 1
        elif type_of_coin == 1:
            self.cost = 5
        elif type_of_coin == 2:
            self.cost = 15
