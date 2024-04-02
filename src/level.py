import dataclasses
import json
import pathlib
from typing import Iterable

import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from . import common

MAPS_PATH = pathlib.Path("assets", "maps")


class TileSet:
    tiles: list[pygame.Surface]

    def __init__(self, path: str, tile_size: tuple[int, int]):
        # sheet = pygame.image.load(MAPS_PATH / path).convert_alpha()
        sheet = pygame.image.load(MAPS_PATH / path)
        width, height = tile_size
        self.tiles = [
            sheet.subsurface((0, y, width, height))
            for y in range(0, sheet.get_height(), height)
        ]
        self.tile_size = self.tile_width, self.tile_height = width, height


class TextureTileSet:
    tiles: list[pg_sdl2.Texture]

    def __init__(self, path: str, tile_size: tuple[int, int]):
        # sheet = pygame.image.load(MAPS_PATH / path).convert_alpha()
        sheet = pygame.image.load(MAPS_PATH / path)
        width, height = tile_size
        surf_tiles = [
            sheet.subsurface((0, y, width, height))
            for y in range(0, sheet.get_height(), height)
        ]
        self.tiles = [
            pg_sdl2.Texture.from_surface(common.renderer, surf) for surf in surf_tiles
        ]
        self.tile_size = self.tile_width, self.tile_height = width, height


class Tile:
    def __init__(
        self,
        position: tuple[int, int],
        grid_position: tuple[int, int],
        image: pygame.Surface,
    ):
        self.position = pygame.Vector2(position)
        self.grid_position = grid_position
        self.image = image
        self.rect = self.image.get_rect(topleft=position)
        self.mask = pygame.mask.from_surface(image)


class TextureTile:
    def __init__(
        self,
        position: tuple[int, int],
        grid_position: tuple[int, int],
        texture: pg_sdl2.Texture,
    ):
        self.position = pygame.Vector2(position)
        self.grid_position = grid_position
        self.image = texture
        self.rect = pygame.Rect(*position, texture.width, texture.height)
        self.mask = pygame.mask.Mask(
            self.rect.size, fill=True
        )  # TODO make it use the actual mask


class LiftPlatform:
    # don't remove this from here, an isinstance check might depend on it
    @dataclasses.dataclass
    class Collider:
        position: pygame.Vector2
        rect: pygame.FRect
        mask: pygame.mask.Mask

    def __init__(
        self,
        position: tuple[int, int],
        grid_position: tuple[int, int],
        segments: list[TextureTile],
    ):
        self.position = pygame.Vector2(position)
        self.grid_position = grid_position

        self.texture = pg_sdl2.Texture(
            common.renderer, (32, 48), target=True
        )  # FIXME don't use hardcoded values...
        self.texture.blend_mode = pygame.BLENDMODE_BLEND

        current_target = common.renderer.target
        common.renderer.target = self.texture
        for i, segment in enumerate(segments):
            y, x = divmod(i, 2)  # hardcoded again :sobbing:
            x *= 16  # yeah...
            y *= 16  # mhm
            segment.image.draw(dstrect=(x, y))
        common.renderer.target = current_target

        self.mask = pygame.mask.Mask(self.collider_rect.size, fill=True)

    @property
    def rect(self) -> pygame.FRect:
        return pygame.FRect(*self.position, self.texture.width, self.texture.height)

    @property
    def collider_rect(self) -> pygame.FRect:
        return pygame.FRect(0, 0, 32, 16).move_to(midbottom=self.rect.midbottom)

    @property
    def collider(self):
        return type(self).Collider(
            position=pygame.Vector2(self.collider_rect.topleft),
            rect=self.collider_rect,
            mask=self.mask,
        )


class LiftWheel:
    # don't remove this from here, an isinstance check might depend on it
    @dataclasses.dataclass
    class Collider:
        position: pygame.Vector2
        rect: pygame.FRect
        mask: pygame.mask.Mask

    def __init__(
        self,
        position: tuple[int, int],
        grid_position: tuple[int, int],
        segments: list[TextureTile],
    ):
        self.position = pygame.Vector2(position)
        self.grid_position = grid_position

        self.texture = pg_sdl2.Texture(
            common.renderer, (32, 32), target=True
        )  # FIXME don't use hardcoded values...
        self.texture.blend_mode = pygame.BLENDMODE_BLEND

        current_target = common.renderer.target
        common.renderer.target = self.texture
        for i, segment in enumerate(segments):
            y, x = divmod(i, 2)  # hardcoded again :sobbing:
            x *= 16  # yeah...
            y *= 16  # mhm
            segment.image.draw(dstrect=(x, y))
        common.renderer.target = current_target

        self.mask = pygame.mask.Mask(self.collider_rect.size, fill=True)

        self.angle = 0
        self.angular_velocity = 0
        self.angular_terminal_velocity = 180
        self.angular_acceleration = 100
        self.drag = -40

    @property
    def rect(self) -> pygame.FRect:
        return pygame.FRect(*self.position, self.texture.width, self.texture.height)

    @property
    def collider_rect(self) -> pygame.FRect:
        return pygame.FRect(0, 0, 32, 32).move_to(midbottom=self.rect.midbottom)

    @property
    def collider(self):
        return type(self).Collider(
            position=pygame.Vector2(self.collider_rect.topleft),
            rect=self.collider_rect,
            mask=self.mask,
        )


class Level:
    tile_texture_layers: list[pg_sdl2.Texture]

    def __init__(self, name: str, frame: int):
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
        self.texture_tile_sets = [
            TextureTileSet(
                ts["image"],
                (ts["grid"]["tileSize"]["width"], ts["grid"]["tileSize"]["height"]),
            )
            for ts in self.data["tilesets"]
        ]

        self.player_position = list(get_tiles(self.data, "spawn", self.tile_sets[
            get_layer_by_name(self.data, "spawn")["tileset"]
        ], frame=frame))[0]

        collider_tile_set = self.tile_sets[
            get_layer_by_name(self.data, "collisions")["tileset"]
        ]
        self.collider_cell_size = collider_tile_set.tile_size
        self.colliders = get_tiles(self.data, "collisions", collider_tile_set, frame)

        self.background = get_tiles(
            self.data,
            "background",
            self.tile_sets[get_layer_by_name(self.data, "background")["tileset"]],
            frame,
        )

        self.tile_layers = [self.background, self.colliders]
        self.map_size = map_size = (self.data["width"], self.data["height"])
        self.tile_texture_layers = [
            create_big_texture(map_size, self.background.values()),
            create_big_texture(map_size, self.colliders.values()),
        ]

        interactives_layer = get_layer_by_name(self.data, "interactives")
        freezers = "freezers"
        self.freezers = get_texture_tiles(
            interactives_layer,
            freezers,
            self.texture_tile_sets[
                get_layer_by_name(interactives_layer, freezers)["tileset"]
            ],
            frame,
        )

        furnaces = "furnaces"
        self.furnaces = get_texture_tiles(
            interactives_layer,
            furnaces,
            self.texture_tile_sets[
                get_layer_by_name(interactives_layer, furnaces)["tileset"]
            ],
            frame,
        )
        for furnace in self.furnaces.values():
            furnace.is_filled = False
            furnace.spawned_prompt = False

        self.interactives = {freezers: self.freezers, furnaces: self.furnaces}
        self.interactives_grid_positions = set()
        for interactive in self.interactives.values():
            self.interactives_grid_positions |= interactive.keys()

        lifts_layer = get_layer_by_name(self.data, "lifts")
        platforms = "platforms"
        self.lift_platforms = {}
        lift_platform_segments = get_texture_tiles(
            lifts_layer,
            platforms,
            self.texture_tile_sets[
                get_layer_by_name(lifts_layer, platforms)["tileset"]
            ],
            frame,
        )
        seen = set()
        current = []
        for (x, y), tile in lift_platform_segments.items():
            if (x, y) in seen:
                continue
            for x_off, y_off in [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)]:
                new_x, new_y = x + x_off, y + y_off
                seen.add((new_x, new_y))

                tile = lift_platform_segments[(new_x, new_y)]
                current.append(tile)
            lift_platform = LiftPlatform(
                (x * 16, y * 16), (x, y), current
            )  # FIXME don't use hardcoded tile size values...
            self.lift_platforms[(x, y)] = lift_platform
            current.clear()

        wheels = "wheels"
        self.lift_wheels = {}
        lift_wheel_segments = get_texture_tiles(
            lifts_layer,
            wheels,
            self.texture_tile_sets[get_layer_by_name(lifts_layer, wheels)["tileset"]],
            frame,
        )
        seen = set()
        current = []
        for (x, y), tile in lift_wheel_segments.items():
            if (x, y) in seen:
                continue
            for x_off, y_off in [(0, 0), (1, 0), (0, 1), (1, 1)]:
                new_x, new_y = x + x_off, y + y_off
                seen.add((new_x, new_y))

                tile = lift_wheel_segments[(new_x, new_y)]
                current.append(tile)
            lift_wheel = LiftWheel(
                (x * 16, y * 16), (x, y), current
            )  # FIXME don't use hardcoded tile size values...
            self.lift_wheels[(x, y)] = lift_wheel
            current.clear()

        joiners = "joiners"
        lift_joiner_segments = get_tile_positions(
            lifts_layer,
            joiners,
            self.texture_tile_sets[get_layer_by_name(lifts_layer, joiners)["tileset"]],
            frame,
        )
        seen = set()
        for x, y in lift_joiner_segments:
            if (x, y) in seen:
                continue
            (endpoint_1, endpoint_2), traversed = find_end_nodes_from_path_segment(
                (x, y), lift_joiner_segments
            )
            seen.update(traversed)
            try:
                if endpoint_1 in self.lift_wheels:
                    wheel = self.lift_wheels[endpoint_1]
                    platform = self.lift_platforms[endpoint_2]
                else:
                    wheel = self.lift_wheels[endpoint_2]
                    platform = self.lift_platforms[endpoint_1]
            except KeyError:
                raise Exception(
                    "joiners are not properly joining the wheel and the platform, "
                    "make sure the joiners end up on the top left grid occupied by "
                    "the wheel and the platform"
                )
            wheel.platform = platform
            wheel.platform_initial_position = platform.position.copy()
            # basically height
            wheel.platform_min_position = (
                min(tpl[1] for tpl in traversed) + 1
            ) * self.collider_cell_size[1]


def find_end_nodes_from_path_segment(
    start: tuple[int, int], segments: set[tuple[int, int]], came_from=(0, 0)
):
    # this whole thing is super janky
    x, y = start
    found_segments = set()
    all_segments = {start}
    going_other_direction = False
    i = 0
    for x_dir, y_dir in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        if (-x_dir, -y_dir) == came_from:
            continue

        if len(found_segments) == 1 and came_from != (0, 0):
            if not going_other_direction:
                continue
            else:
                going_other_direction = True

        new_start = x + x_dir, y + y_dir
        if new_start not in segments:
            continue

        i += 1
        segment, traversed = find_end_nodes_from_path_segment(
            new_start, segments, (x_dir, y_dir)
        )
        all_segments.update(traversed)
        found_segments.update(segment)

    if i == 0:
        found_segments.add(start)
    elif i == 1 and came_from == (0, 0):
        found_segments.add(start)

    return found_segments, all_segments


def create_big_texture(size: tuple[int, int], tiles: Iterable[Tile]) -> pg_sdl2.Texture:
    surf = pygame.Surface(size, flags=pygame.SRCALPHA)
    surf.fblits([(tile.image, tile.rect) for tile in tiles])
    texture = pg_sdl2.Texture.from_surface(common.renderer, surf)
    return texture


def get_tile_positions(
    data: dict, layer_name: str, tile_set: TileSet | TextureTileSet, frame: int
) -> set[tuple[int, int]]:
    grid_positions = set()
    (x_off, y_off), (columns, rows), tiles = get_tile_map(data, layer_name, frame)
    width, height = tile_set.tile_width, tile_set.tile_height

    col_off = x_off // width
    row_off = y_off // height

    for i, tile_idx in enumerate(tiles):
        # skip empty tiles
        if tile_idx == 0:
            continue

        row, col = divmod(i, columns)
        grid_x = col_off + col
        grid_y = row_off + row

        grid_positions.add((grid_x, grid_y))

    return grid_positions


def get_tiles(
    data: dict, layer_name: str, tile_set: TileSet, frame: int
) -> dict[tuple[int, int], Tile]:
    grid_map = {}
    (x_off, y_off), (columns, rows), tiles = get_tile_map(data, layer_name, frame)
    width, height = tile_set.tile_width, tile_set.tile_height

    col_off = x_off // width
    row_off = y_off // height
    # print(layer_name)
    # print(tiles)

    for i, tile_idx in enumerate(tiles):
        # skip empty tiles
        if tile_idx == 0:
            continue

        row, col = divmod(i, columns)
        grid_x = col_off + col
        grid_y = row_off + row
        x = x_off + col * width
        y = y_off + row * height
        # print(grid_x, grid_y)
        grid_map[(grid_x, grid_y)] = Tile(
            position=(x, y),
            grid_position=(grid_x, grid_y),
            image=tile_set.tiles[tile_idx],
        )

    return grid_map


def get_texture_tiles(
    data: dict, layer_name: str, tile_set: TextureTileSet, frame: int
) -> dict[tuple[int, int], TextureTile]:
    grid_map = {}
    (x_off, y_off), (columns, rows), tiles = get_tile_map(data, layer_name, frame)
    width, height = tile_set.tile_width, tile_set.tile_height

    col_off = x_off // width
    row_off = y_off // height

    for i, tile_idx in enumerate(tiles):
        # skip empty tiles
        if tile_idx == 0:
            continue

        row, col = divmod(i, columns)
        grid_x = col_off + col
        grid_y = row_off + row
        x = x_off + col * width
        y = y_off + row * height

        grid_map[(grid_x, grid_y)] = TextureTile(
            position=(x, y),
            grid_position=(grid_x, grid_y),
            texture=tile_set.tiles[tile_idx],
        )

    return grid_map


def get_tile_map(
    data: dict, layer_name: str, frame: int
) -> tuple[tuple[int, int], tuple[int, int], list[int]]:
    layer = get_layer_by_name(data, layer_name)

    try:
        tile_map = get_frame(layer, frame)
    except Exception as e:
        print(e)
        return (0, 0), (0, 0), []

    x_off, y_off = tile_map["bounds"]["x"], tile_map["bounds"]["y"]
    columns, rows = tile_map["tilemap"]["width"], tile_map["tilemap"]["height"]
    tiles = tile_map["tilemap"]["tiles"]

    return (x_off, y_off), (columns, rows), tiles


def get_layer_by_name(data: dict, name: str) -> dict:
    for layer in data["layers"]:
        if layer["name"] == name:
            return layer
    raise Exception(f"layer {name!r} not found in layer {data['name']!r}")


def get_frame(layer: dict, frame: int) -> dict:
    for cel in layer["cels"]:
        if cel["frame"] == frame:
            return cel
    raise Exception(f"frame {frame!r} not found in layer {layer['name']!r}, might be empty")


if __name__ == "__main__":
    Level("map_1", 0)
