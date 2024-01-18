from constants import WIDTH, HEIGHT


class Camera:
    """ Камера """

    def __init__(self, target) -> None:
        """
        :param target: объект за которым закреплена камера
        """
        # Экземпляр класса объекта
        self.target = target
        # Координаты
        self.x = 0
        self.y = 0
        # Изменение координат
        self.dx = -(self.target.rect.x +
                    self.target.rect.w // 2 - WIDTH // 2)
        self.dy = -(self.target.rect.y +
                    self.target.rect.h // 2 - HEIGHT // 1.4)

    def update(self, dx=0, dy=0):
        self.x += dx
        self.y += dy
        self.target.x += dx
        self.target.y += dy