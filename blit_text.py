from typing import Union
from pygame.font import SysFont


def blit_text(screen, text: str, pos_x: int, pos_y: int,
              font_color: Union[tuple[int, int, int], str] = (255, 255, 255),
              font_name: str = 'bahnschrift',
              font_size: int = 30, center: bool = False) -> None:
    """ Отрисовка текста на экране

    :param text: текст, который будет отображён на экране
    :param pos_x: x координата текста
    :param pos_y: y координата текста
    :param font_color: цвет, в который будет окрашен текст
    :param font_name: название шрифта, который будет использован
    :param font_size: размер шрифта
    :param center: если указан данный флажок, то pos_x и pos_y будут
    указывать не координаты левого верхнего угла, а центра поверхности с
    текстом

    """
    # Выбранный шрифт
    font = SysFont(font_name, font_size)
    # Рендерим текст в поверхность
    text_surface = font.render(text, True, font_color)
    if not center:
        # Отрисовываем на экране выбранный текст
        screen.blit(text_surface, (pos_x, pos_y))
    else:
        text_rect = text_surface.get_rect(center=(pos_x, pos_y))
        screen.blit(text_surface, text_rect)
