from typing import Iterable

import pygame


type SpritesArg = pygame.sprite.Sprite | Iterable[pygame.sprite.Sprite]


class Group(pygame.sprite.Group):
    def __init__(self, *sprites: SpritesArg):
        super().__init__(*sprites)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fblits([(sprite.image, sprite.rect) for sprite in self.sprites()])

    def add(self, *sprites: SpritesArg) -> None:
        super().add(*sprites)
