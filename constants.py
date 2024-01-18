# Размеры тайлов (всегда квадраты)
TILE_WIDTH = TILE_HEIGHT = 50
# FPS игры
FPS = 60
# Ширина экрана
WIDTH = 800
# Высота экрана
HEIGHT = 400
# На сколько пикселей перемещается игрок
STEP = 8
# Ширина пули
BULLET_WIDTH = 15
# Высота пули
BULLET_HEIGHT = 5
# Скорость пули
BULLET_SPEED = 5
# Игрок смотрит влево
DIRECTION_LEFT = 0
# Игрок смотрит вправо
DIRECTION_RIGHT = 1
# Толщина рамки у шкал прокачки
BORDER_WIDTH = 2
# Длина шкалы характеристики
IMPROVEMENT_SCALE_WIDTH = 123
# Длина шкалы HP у сущностей
HEALTH_SCALE_WIDTH = 50
# Высота шкалы HP у сущностей
HEALTH_SCALE_HEIGTH = 8
# Толщина рамки у шкалы HP у сущностей
HEALTH_SCALE_BORDER = 2
# Длина шкалы HP у сущностей
KEY_OBJECT_HEALTH_SCALE_WIDTH = 150
# Высота шкалы HP у сущностей
KEY_OBJECT_HEALTH_SCALE_HEIGTH = 16
# Толщина рамки у шкалы HP у сущностей
KEY_OBJECT_HEALTH_SCALE_BORDER = 3
# Длина шкалы перезарядки
RECHARGE_SCALE_WIDTH = 100
# Длина шкалы перезарядки
RECHARGE_SCALE_HEIGTH = 19
# Толщина рамки
RECHARGE_SCALE_BORDER = 3
# Длина шкалы HP у игрока
PLAYER_HEALTH_SCALE_WIDTH = 160
# Высота шкалы HP у игрока
PLAYER_HEALTH_SCALE_HEIGTH = 19
# Толщина рамки у шкалы HP у игрока
PLAYER_HEALTH_SCALE_BORDER = 3
# Длина шкалы щита у игрока
PLAYER_SHIELD_SCALE_WIDTH = 160
# Высота шкалы щита у игрока
PLAYER_SHIELD_SCALE_HEIGTH = 19
# Толщина рамки у шкалы щита у игрока
PLAYER_SHIELD_SCALE_BORDER = 3
# Награды за прохождение уровней
LEVELS_REWARD = {
    1: 150,
    2: 160
}
# Координаты для индикаторов, информирующих о количестве врагов каждого типа
ENEMIES_INFO_COORDS = [
    (115, 239), (215, 239), (115, 290), (215, 290)
]
# Координаты для счетчика монеток (текст)
TEXT_COIN_COUNTER_COORDS = (WIDTH * 0.8125, HEIGHT * 0.025)
# Номер текущего уровня - координаты
CURRENT_LEVEL_MARK_COORDS = (58, 57)
# Награда текущего уровня - координаты
CURRENT_LEVEL_REWARD_COORDS = (180, 107)
# Количество уровней
LEVELS_AMOUNT = len(LEVELS_REWARD)
# Координаты, куда лепить странички руководства
GUIDE_PAGES_COORDS = (220, 39)
# Координаты, куда лепить странички с прокачкой
UPGRADE_PAGES_COORDS = (300, 91)
# Обозначение стандартного курсора (стрелка)
DEFAULT_CURSOR = 0
# Обозначение курсора активного (палец)
ACTIVE_CURSOR = 1
# Обознаяение того, что никакое окно не нужно отображать
LEVEL_MAP = 0
# Обозначение главного меню
MAIN_MENU = 1
# Обохначение меню прокачки
UPGRADE_MENU = 2
# Обозначение меню паузы
PAUSE_MENU = 3
# Обозначение меню выбора уровня
SELECT_LEVEL_MENU = 4
# Обозначение меню смерти игрока :(
ENDGAME_MENU = 5
# Обозначение меню завершения уровня
VICTORY_MENU = 6
# Обозначение меню руководства
GUIDE_MENU = 7
