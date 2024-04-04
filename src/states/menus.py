import collections
import collections.abc
import heapq
import math
import random
import types
import functools
import sys

import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from src import player, settings, common, enums, animation, assets, level, particles, ui


class MainMenu:
    def __init__(self):
        # mmmm
        from . import GamePlay, Tutorial

        self.ui_manager = ui.UIManager()
        self.ui_manager.add(
            ui.Button(
                (settings.WIDTH / 2, settings.HEIGHT / 2 - 24 - 48),
                "PLAY",
                pressed_image=assets.images["button_pressed_green_surf"],
                callback=lambda: common.set_current_state(GamePlay())
            ),
            initial_selected=True,
        ).add(
            ui.Button(
                (settings.WIDTH / 2, settings.HEIGHT / 2 - 24),
                "TUTORIAL",
                pressed_image=assets.images["button_pressed_yellow_surf"],
                callback=lambda: common.set_current_state(Tutorial()),
            ),
            ui.Button(
                (settings.WIDTH / 2, settings.HEIGHT / 2 + 24),
                "SETTINGS",
                pressed_image=assets.images["button_pressed_blue_surf"],
                callback=lambda: common.set_current_state(Settings())
            ),
            ui.Button(
                (settings.WIDTH / 2, settings.HEIGHT / 2 + 24 + 48),
                "EXIT",
                pressed_image=assets.images["button_pressed_surf"],
                callback=lambda: sys.exit()
            ),
        )

    def update(self):
        self.ui_manager.update()

    def draw(self):
        assets.images["title"].draw(dstrect=pygame.Rect(0, 0, *settings.SIZE).move_to(center=(settings.WIDTH / 2, settings.HEIGHT / 2)))
        self.ui_manager.draw()


class Settings:
    def __init__(self):
        self.ui_manager = ui.UIManager()
        self.ui_manager.add(
            ui.Button(
                (settings.WIDTH / 2, settings.HEIGHT / 2 - 48),
                "BACK",
                pressed_image=assets.images["button_pressed_yellow_surf"],
                callback=lambda: common.set_current_state(MainMenu())
            ),
            initial_selected=True,
        )

    def update(self):
        self.ui_manager.update()

    def draw(self):
        self.ui_manager.draw()
