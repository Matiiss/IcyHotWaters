import types

import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from . import stubs

window: pygame.Window
renderer: pg_sdl2.Renderer

# screen: pygame.Surface  # using _sdl2

dt: float
events: list[pygame.Event]
clock: pygame.Clock

_current_state: stubs.State


def set_current_state(state: stubs.State) -> None:
    global _current_state
    _current_state = state


def get_current_state() -> stubs.State:
    return _current_state
