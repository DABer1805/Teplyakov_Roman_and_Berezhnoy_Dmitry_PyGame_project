from pygame import Rect
from pygame.draw import rect
from blit_text import blit_text
from constants import TEXT_COIN_COUNTER_COORDS


class DashboardScale:
    def __init__(self, pos_x, pos_y, width, height, border,
                 cur_value, max_value, colors):
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.width = width
        self.height = height
        self.border = border
        self.cur_value = cur_value
        self.max_value = max_value
        self.colors = colors

    def draw(self, screen):
        rect(
            screen, self.colors[0], Rect(
                self.pos_x, self.pos_y, self.width, self.height
            )
        )
        rect(
            screen, self.colors[1], Rect(
                self.pos_x + self.border, self.pos_y + self.border,
                self.width * (self.cur_value / self.max_value) -
                self.border * 2, self.height - self.border * 2
            )
        )
        rect(
            screen, self.colors[2], Rect(
                self.pos_x + self.border * 2, self.pos_y + self.border * 2,
                self.width * (self.cur_value / self.max_value) -
                self.border * 4, self.height - self.border * 4
            )
        )


class Dashboard:
    def __init__(self, scales, images, coins):
        self.scales = scales
        self.coins = coins
        self.images = images

    def draw(self, screen):
        for scale in self.scales:
            scale.draw(screen)

        for image, coords in self.images:
            screen.blit(image, coords)

        blit_text(screen, str(self.coins),
                  *TEXT_COIN_COUNTER_COORDS, "white", font_size=30)

    def update(self, player):
        self.coins = player.coins
        self.scales[0].max_value = player.clip_size
        self.scales[0].cur_value = player.ammo
        self.scales[1].max_value = player.max_hp
        self.scales[1].cur_value = player.hp
        self.scales[2].max_value = player.max_shield
        self.scales[2].cur_value = player.shield
