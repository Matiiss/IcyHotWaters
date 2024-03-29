from typing import Protocol

import pygame


class State(Protocol):
    def update(self) -> None:
        ...

    def draw(self, surface: pygame.Surface) -> None:
        ...
