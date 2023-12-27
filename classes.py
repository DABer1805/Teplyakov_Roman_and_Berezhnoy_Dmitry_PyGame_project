import pygame

from constants import TILE_WIDTH, TILE_HEIGHT, WIDTH, HEIGHT


class Tile(pygame.sprite.Sprite):
    def __init__(self, tiles_group, all_sprites):
        super().__init__(tiles_group, all_sprites)


class Wall(Tile):
    def __init__(self, tiles_group, all_sprites, tile_images, pos_x, pos_y):
        super().__init__(tiles_group, all_sprites)
        self.image = tile_images['brick']
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)


class Box(Tile):
    def __init__(self, tiles_group, all_sprites, tile_images, pos_x, pos_y):
        super().__init__(tiles_group, all_sprites)
        self.image = tile_images['box']
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)
        self.hp = 50


class Camera:
    def __init__(self, field_size):
        self.dx = 0
        self.dy = 0
        self.field_size = (field_size[0], field_size[1] - 1)

    def apply(self, obj):
        obj.rect.x += self.dx
        obj.rect.y += self.dy

    def update(self, target, tiles_group):
        if not pygame.sprite.spritecollideany(target, tiles_group):
            self.dx = -(target.rect.x + target.rect.w // 2 - WIDTH // 2)
            self.dy = -(target.rect.y + target.rect.h // 2 - HEIGHT // 2)


class Entity(pygame.sprite.Sprite):
    def __init__(self, entity_group, all_sprites,
                 entity_image, pos_x, pos_y):
        super().__init__(entity_group, all_sprites)
        self.image = entity_image
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x + 15,
                                               TILE_HEIGHT * pos_y + 5)


class Player(Entity):
    def __init__(self, player_group, all_sprites, player_image, hp,
                 pos_x, pos_y):
        super().__init__(player_group, all_sprites, player_image,
                         pos_x, pos_y)
        self.hp = hp
