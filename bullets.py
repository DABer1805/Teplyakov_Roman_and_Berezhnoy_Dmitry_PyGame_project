from random import random
from typing import Literal

from pygame.sprite import Sprite, Group, spritecollideany, spritecollide
from pygame.mixer import Sound
from pygame import Surface

from animated_sprites import Coin
from camera import Camera
from constants import DIRECTION_RIGHT, BULLET_SPEED
from entites import Player


class Bullet(Sprite):
    """ Снаряд """

    def __init__(self, bullet_group: Group,
                 bullet_image: Surface,
                 user_direction: Literal[0, 1],
                 pos_x, pos_y, is_enemy_bullet=False, damage=1) -> None:
        """
        :param bullet_group: Группа спрайтов, куда будет добавлен снаряд
        :param bullet_image: Изображение снаряда
        :param user_direction: Направление игрока (оно же будет и для снаряда)
        :param pos_x: позиция по оси x
        :param pos_y: позиция по оси y
        :key is_enemy_bullet: флаг для определения пули врага и игрока
        """
        super().__init__(bullet_group)
        self.damage = damage
        # Счетчик дальности полета
        self.destroy_timer = 45
        # Изображение снаряда
        self.image = bullet_image
        self.x = pos_x
        self.y = pos_y
        # Размещаем снаряд на экране
        self.rect = self.image.get_rect()
        self.direction = user_direction
        # Изменение координаты пули
        self.d_x = (1 if self.direction == DIRECTION_RIGHT else -1) * \
                   BULLET_SPEED
        # Флаг для различия пули игрока и пули врага
        self.is_enemy_bullet = is_enemy_bullet

    def update(
            self, player: Player, destructible_groups: Group,
            indestructible_groups: Group,
            destroy_sounds: list, hit_sounds: list,
            player_group: Group, camera: Camera,
            screen: Surface, coin_images: list,
            coin_selection_sound: Sound, chunks: list
    ) -> bool:
        """ Перемещение снаряда
        :param player: экземпляр класса игрока
        :param destructible_groups: группа разрушаемых спрайтов
        :param indestructible_groups: группа неразрушимых спрайтов
        :param destroy_sounds: список разрушения блоков или смерти врагов
        :param hit_sounds: список звуков попаданий по блокам или врагам
        :param player_group: группа спрайта игрока
        :param camera: экземпляр класса камеры
        :param screen: окно приложения
        :param coin_images: изображения монетки
        :param coin_selection_sound: звук подбора монеты
        :param chunks: список чанков
        """
        self.destroy_timer -= 1
        if not self.destroy_timer:
            hit_sounds[0].play()
            self.kill()
        # Определяем, в каком направлении передвигать снаряд
        self.x += self.d_x
        self.rect.x = self.x - camera.x + camera.dx
        self.rect.y = self.y - camera.y + camera.dy

        # Список, со всеми спрайтами, в которые ударился снаряд
        destructible_sprites_hit_list = spritecollide(
            self, destructible_groups, False
        )
        # Если есть хоть один, такой спрайт, то удаляем его вместе со
        # снарядом.
        if destructible_sprites_hit_list:
            if not self.is_enemy_bullet:
                if destructible_sprites_hit_list[0].type == 2:
                    if destructible_sprites_hit_list[0].direction != \
                            self.direction:
                        hit_sounds[1].play()
                        self.kill()
                        return False
                destructible_sprites_hit_list[0].hp -= player.damage
                if destructible_sprites_hit_list[0].hp <= 0:
                    sprite_type = destructible_sprites_hit_list[0].type
                    if sprite_type in (0, 1, 2, 3):
                        destroy_sounds[0].play()
                    elif sprite_type in (4,):
                        destroy_sounds[1].play()
                    chance = random()
                    coin_type = None
                    if chance <= 0.15:
                        coin_type = 2
                    elif 0.15 < chance <= 0.4:
                        coin_type = 1
                    elif 0.4 < chance <= 0.7:
                        coin_type = 0
                    if coin_type is not None:
                        Coin(coin_selection_sound, coin_images[:3], coin_type,
                             8, 1, destructible_sprites_hit_list[0].x + 5,
                             destructible_sprites_hit_list[0].y + 5,
                             chunks[destructible_sprites_hit_list[
                                 0].chunk_number].coins_group,
                             chunks[destructible_sprites_hit_list[
                                 0].chunk_number].all_sprites)
                    if destructible_sprites_hit_list[0].is_key_object:
                        return True
                    destructible_sprites_hit_list[0].kill()
            if destructible_sprites_hit_list[0].type in (4,) or \
                    not self.is_enemy_bullet:
                hit_sounds[0].play()
                self.kill()

        # Если снаряд столкнулся с каким-то из спрайтов и этот спрайт не
        # игрок, то удаляем снаряд
        if spritecollideany(self, indestructible_groups) and \
                not spritecollideany(self, player_group):
            hit_sounds[0].play()
            self.kill()
        # Если снаряд столкнулся с каким-то из спрайтов и этот спрайт не
        # игрок, то удаляем снаряд
        if spritecollideany(self, indestructible_groups) and \
                not spritecollideany(self, player_group):
            hit_sounds[1].play()
            self.kill()

        # Если пуля вражеская, то проверяем пересечение со спрайтом игрока и
        # отнимаем либо щит, либо хп
        if self.is_enemy_bullet:
            if spritecollideany(self, player_group):
                for player in player_group:
                    if player.shield > 0:
                        player.shield -= self.damage
                        if player.shield < 0:
                            player.shield = 0
                    else:
                        player.hp -= self.damage
                    if not player.shield_recharge:
                        player.shield_recharge = 150
                self.kill()

        screen.blit(self.image, (self.rect.x, self.rect.y))
        return False
