import functools
import os
import json
import pathlib

import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from .spritesheet import AsepriteSpriteSheet
from . import common, level

images: dict = {}
sfx: dict[str, pygame.mixer.Sound] = {}
maps = {}
fonts: dict[str, dict[int, pygame.Font]] = {}


def image_path(path, extension="png"):
    return os.path.join("assets", f"{path}.{extension}")


def load_image(path):
    # return pygame.image.load(image_path(path)).convert_alpha()
    surf = pygame.image.load(image_path(path))
    return pg_sdl2.Texture.from_surface(common.renderer, surf)


def load_sound(path, extension="mp3"):
    return pygame.mixer.Sound(os.path.join("assets/sfx", f"{path}.{extension}"))


def load_fonts(path, sizes):
    return {size: pygame.Font(os.path.join("assets", path), size) for size in sizes}


@functools.cache
def load_tiles():
    dct = {}
    with open("assets/maps/tile_map.json") as file:
        data = json.load(file)

    for tile in data["tiles"]:
        path = pathlib.Path(tile["image"])
        dct[tile["id"]] = load_image(f"tiles/{path.stem}")

    return dct


def level_path(path, extension="json"):
    return os.path.join("assets/maps", f"{path}.{extension}")


def set_sound_volume(value):
    for sound in sfx.values():
        sound.set_volume(value)


def stop_all_sounds():
    for sound in sfx.values():
        sound.stop()


def load_assets():
    images.update(
        {
            "player": AsepriteSpriteSheet(image_path("player")),
            "ice_cube": load_image("ice_cube"),
            "ice_cube_invalid": load_image("ice_cube_invalid"),
            "ice_cube_icon": level.TextureTile(
                (0, 0), (0, 0), load_image("ice_cube_icon")
            ),
            "steam_particle": AsepriteSpriteSheet(image_path("steam_particle")),
            "rope": load_image("rope"),
            "freezer_loading_bar": AsepriteSpriteSheet(
                image_path("freezer_loading_bar")
            ),
            "fire_particles": AsepriteSpriteSheet(image_path("fire_particles")),
            "ice_particles": AsepriteSpriteSheet(image_path("ice_particles")),
            "dust_particles": AsepriteSpriteSheet(image_path("dust_particles")),
            "item_frame": load_image("item_frame"),
            "item_frame_selected": load_image("item_frame_selected"),
            # "tiles": load_tiles(),
        }
    )
    sfx.update(
        {
            "pop": load_sound("pop"),
            "ding": load_sound("ding"),
            "humm": load_sound("humm"),
            "splash": load_sound("splash"),
            "no": load_sound("no"),
            "knock": load_sound("knock"),
        }
    )
    # # maps.update({"level_1": Level(level_path("level_1"), load_tiles())})
    fonts.update(
        {
            "default": {
                16: pygame.Font(None, 16),
                12: pygame.Font(None, 12),
                10: pygame.Font(None, 10),
            },
            "pixelify_regular": {
                **load_fonts(
                    "Pixelify_Sans/static/PixelifySans-Regular.ttf",
                    [4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32],
                )
            },
            "pixelify_bold": {
                **load_fonts(
                    "Pixelify_Sans/static/PixelifySans-Bold.ttf",
                    [4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32],
                )
            },
            "pixelify_medium": {
                **load_fonts(
                    "Pixelify_Sans/static/PixelifySans-Medium.ttf",
                    [4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32],
                )
            },
            "pixelify_semibold": {
                **load_fonts(
                    "Pixelify_Sans/static/PixelifySans-SemiBold.ttf",
                    [4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32],
                )
            },
        }
    )
