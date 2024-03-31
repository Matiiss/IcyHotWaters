import json
import pathlib

import pygame

MAPS_PATH = pathlib.Path("assets", "maps")


class TileSet:
    tiles: list[pygame.Surface]

    def __init__(self, path: str, tile_size: tuple[int, int]):
        sheet = pygame.image.load(MAPS_PATH / path).convert_alpha()
        width, height = tile_size
        self.tiles = [
            sheet.subsurface((0, y, width, height))
            for y in range(0, sheet.get_height(), height)
        ]
        self.tile_width, self.tile_height = width, height


class Tile:
    def __init__(
        self,
        position: tuple[int, int],
        grid_position: tuple[int, int],
        image: pygame.Surface,
    ):
        self.position = position
        self.grid_position = grid_position
        self.image = image
        self.rect = self.image.get_rect(topleft=position)


class Level:
    def __init__(self, name: str):
        self.name = name
        with open(MAPS_PATH / name / "sprite.json") as file:
            self.data = json.load(file)

        self.tile_sets = [
            TileSet(
                ts["image"],
                (ts["grid"]["tileSize"]["width"], ts["grid"]["tileSize"]["height"]),
            )
            for ts in self.data["tilesets"]
        ]

        self.colliders = get_tiles(
            self.data,
            "collisions",
            self.tile_sets[get_layer_by_name(self.data, "collisions")["tileset"]],
        )

        self.background = get_tiles(
            self.data,
            "background",
            self.tile_sets[get_layer_by_name(self.data, "background")["tileset"]],
        )

        self.tile_layers = [self.background, self.colliders]


def get_tiles(data: dict, layer_name: str, tile_set: TileSet):
    tiles = {}
    (x_off, y_off), (columns, rows), tiles = get_tile_map(data, layer_name)
    width, height = tile_set.tile_width, tile_set.tile_height

    col_off = x_off // width
    row_off = y_off // height

    for i, tile_idx in enumerate(tiles):
        row, col = divmod(i, columns)
        grid_x = col_off + col
        grid_y = row_off + row
        x = x_off + col * width
        y = y_off + row * height

        tiles[(grid_x, grid_y)] = Tile(
            position=(x, y),
            grid_position=(grid_x, grid_y),
            image=tile_set.tiles[tile_idx],
        )

    return tiles


def get_tile_map(
    data: dict, layer_name: str, frame: int = 0
) -> tuple[tuple[int, int], tuple[int, int], list[int]]:
    layer = get_layer_by_name(data, layer_name)
    tile_map = layer["cels"][
        frame
    ]  # TODO do a linear search over the `cels` array to find the correct frame

    x_off, y_off = tile_map["bounds"]["x"], tile_map["bounds"]["y"]
    columns, rows = tile_map["tilemap"]["width"], tile_map["tilemap"]["height"]
    tiles = tile_map["tiles"]

    return (x_off, y_off), (columns, rows), tiles


def get_layer_by_name(data: dict, name: str) -> dict:
    for layer in data["layers"]:
        if layer["name"] == name:
            return layer


if __name__ == "__main__":
    Level(name="map_1")
