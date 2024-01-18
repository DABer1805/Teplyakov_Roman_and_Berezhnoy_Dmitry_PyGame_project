from pygame.time import delay
from pygame.mouse import get_pos, get_pressed

from blit_text import blit_text
from constants import DEFAULT_CURSOR, ACTIVE_CURSOR


class Button:
    """Класс для создания кнопок"""

    def __init__(self, width: int, height: int, pos_x: int, pos_y: int,
                 active_image, inactive_image, text: str,
                 action=None, font_size=20):
        """
        :param width: ширина
        :param height: высота
        :param pos_x: координата позиции по оси x
        :param pos_y: координата позиции по оси y
        :param active_image: изображение нажатой кнопки
        :param inactive_image: изображение неактивной кнопки
        :key action: действие
        :key font_size: размер шрифта
        """
        # Ширина
        self.width = width
        # Высота
        self.height = height
        # Координата позиции по оси x
        self.pos_x = pos_x
        # Координата позиции по оси y
        self.pos_y = pos_y
        # Изображение нажатой кнопки
        self.active_image = active_image
        # Изображение неактивной кнопки
        self.inactive_image = inactive_image
        # Текст кнопки
        self.text = text
        # Действие кнопки
        self.action = action
        # Флаг видимости
        self.is_visible = True
        # Размер шрифта
        self.font_size = font_size

    def draw(self, screen):
        """Отрисовка кнопок"""
        result = None
        arrow_idx = DEFAULT_CURSOR
        if self.is_visible:
            mouse = get_pos()
            click = get_pressed()

            if (self.pos_x < mouse[0] < self.pos_x + self.width) and \
                    (self.pos_y < mouse[1] < self.pos_y + self.height):
                screen.blit(self.active_image, (self.pos_x, self.pos_y))

                if click[0] == 1 and self.action is not None:
                    # soundButton.play()
                    delay(300)
                    result = self.action()

                arrow_idx = ACTIVE_CURSOR
            else:
                screen.blit(self.inactive_image, (self.pos_x, self.pos_y))
            blit_text(
                screen, self.text, int(self.pos_x + self.width / 2),
                int(self.pos_y + self.height / 2 + 2),
                font_size=self.font_size, center=True
            )
        return (arrow_idx, *result) if result is not None else (
            arrow_idx, None
        )
