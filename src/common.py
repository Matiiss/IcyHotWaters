import types

import pygame

from . import stubs

screen: pygame.Surface
dt: float
events: list[pygame.Event]
_current_state: stubs.State


def set_current_state(state: stubs.State) -> None:
    global _current_state
    _current_state = state


def get_current_state() -> stubs.State:
    return _current_state
