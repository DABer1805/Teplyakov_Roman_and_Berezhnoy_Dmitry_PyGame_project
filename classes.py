import pygame

from constants import TILE_WIDTH, TILE_HEIGHT, WIDTH, HEIGHT, \
    DIRECTION_RIGHT, BULLET_SPEED


class Tile(pygame.sprite.Sprite):
    """ Тайл """

    def __init__(self, tiles_group, all_sprites, tile_type,
                 tile_images, pos_x, pos_y):
        super().__init__(tiles_group, all_sprites)
        self.image = tile_images[tile_type]
        self.rect = self.image.get_rect().move(TILE_WIDTH * pos_x,
                                               TILE_HEIGHT * pos_y)


class Box(Tile):
    """ Коробка """

    def __init__(self, tiles_group, all_sprites, tile_type,
                 tile_images, pos_x, pos_y):
        super().__init__(tiles_group, all_sprites, tile_type,
                         tile_images, pos_x, pos_y)
        self.hp = 5


class Brick(Tile):
    """ Кирпич """
    pass


class Camera:
    def __init__(self, field_size):
        self.dx = 0
        self.dy = 0
        self.field_size = (field_size[0], field_size[1] - 1)

    # сдвинуть объект obj на смещение камеры
    def apply(self, obj):
        obj.rect.x += self.dx
        obj.rect.y += self.dy

    # позиционировать камеру на объекте target
    def update(self, target):
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
        self.direction = DIRECTION_RIGHT


class Bullet(pygame.sprite.Sprite):
    def __init__(self, bullet_group, all_sprites, bullet_image,
                 user_direction, pos_x, pos_y):
        super().__init__(bullet_group, all_sprites)
        self.image = bullet_image
        self.rect = self.image.get_rect().move(pos_x, pos_y)
        self.direction = user_direction

    def update(self, destructible_groups, indestructible_groups):
        if self.direction == DIRECTION_RIGHT:
            self.rect.x += BULLET_SPEED
        else:
            self.rect.x -= BULLET_SPEED

        for destructible_group in destructible_groups:
            destructible_sprites_hit_list = pygame.sprite.spritecollide(
                self, destructible_group, False
            )
            if destructible_sprites_hit_list:
                destructible_sprites_hit_list[0].kill()
                self.kill()

        for indestructible_group in indestructible_groups:
            if pygame.sprite.spritecollideany(self, indestructible_group):
                self.kill()
