import dataclasses
import itertools
import json
import pathlib
import queue
from typing import Iterable

import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from . import common, animation, assets

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
        self.rect = pygame.FRect(*position, texture.width, texture.height)
        self.mask = pygame.mask.Mask(
            self.rect.size, fill=True
        )  # TODO make it use the actual mask


class WaterTile:
    def __init__(
        self,
        position: tuple[int, int],
        grid_position: tuple[int, int],
        texture: pg_sdl2.Texture,
        idx: int,
    ):
        self.idx = idx
        self.position = pygame.Vector2(position)
        self.grid_position = grid_position
        self.image = texture
        self.rect = pygame.FRect(*position, texture.width, texture.height)
        self.mask = pygame.mask.Mask(
            self.rect.size, fill=True
        )  # TODO make it use the actual mask


class BigFreezer:
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

        self.loading_bar_animation = animation.LoadingBarAnimation(
            assets.images["freezer_loading_bar"], cycle=False
        )
        self.loading_bar_image = None
        self.loading_bar_rect = pygame.Rect(0, 0, 32, 16).move_to(
            midbottom=self.rect.midtop
        )
        self.loading_bar_position = pygame.Vector2(self.loading_bar_rect.topleft)
        self.bucket = None

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
        self.angular_acceleration = 80
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


class Pool:
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
        segments: set[tuple[int, int]],
    ):
        self.position = pygame.Vector2(position)
        self.grid_position = grid_position

        min_x, min_y = min(x for x, _ in segments), min(y for _, y in segments)
        max_x, max_y = max(x for x, _ in segments), max(y for _, y in segments)

        self.texture = pg_sdl2.Texture(
            common.renderer,
            (
                (max_x - min_x + 1) * 16,
                (max_y - min_y + 1) * 16,
            ),
            target=True,
        )  # FIXME don't use hardcoded values...
        self.texture.blend_mode = pygame.BLEND_RGBA_MULT

        self.level_count = max_y - min_y + 1
        max_col_count = max_x - min_x + 1
        self.levels = []
        self.pool_positions = []
        x, y = grid_position
        for y_off in range(self.level_count):
            self.levels.append([])
            self.pool_positions.append([])
            for x_off in range(max_col_count):
                if (x + x_off, y + y_off) in segments:
                    self.levels[y_off].append((x + x_off, y + y_off))
                    self.pool_positions[y_off].append((x_off, y_off))

        self.filled_levels = 0
        self.colliders = set(itertools.chain(*self.levels))


class Doors:
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
            common.renderer, (16, 32), target=True
        )  # FIXME don't use hardcoded values...
        self.texture.blend_mode = pygame.BLENDMODE_BLEND

        current_target = common.renderer.target
        common.renderer.target = self.texture
        for i, segment in enumerate(segments):
            y, x = divmod(i, 1)  # hardcoded again :sobbing:
            x *= 16  # yeah...
            y *= 16  # mhm
            segment.image.draw(dstrect=(x, y))
        common.renderer.target = current_target

        self.mask = pygame.mask.Mask(self.collider_rect.size, fill=True)
        self.is_locked = True

    @property
    def rect(self) -> pygame.FRect:
        return pygame.FRect(*self.position, self.texture.width, self.texture.height)

    @property
    def collider_rect(self) -> pygame.FRect:
        return pygame.FRect(0, 0, 16, 32).move_to(midbottom=self.rect.midbottom)

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

        self.player_position = get_tiles(
            self.data,
            "spawn",
            self.tile_sets[get_layer_by_name(self.data, "spawn")["tileset"]],
            frame=frame,
        )
        assert len(self.player_position) == 1
        self.player_position = list(self.player_position)[0]

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

        self.background_2 = get_tiles(
            self.data,
            "background_2",
            self.tile_sets[get_layer_by_name(self.data, "background_2")["tileset"]],
            frame,
        )

        self.background_3 = get_tiles(
            self.data,
            "background_3",
            self.tile_sets[get_layer_by_name(self.data, "background_3")["tileset"]],
            frame,
        )

        self.water_tiles = get_tiles(
            self.data,
            "water",
            self.tile_sets[get_layer_by_name(self.data, "water")["tileset"]],
            frame,
        )

        self.spikes = get_tiles(
            self.data,
            "spikes",
            self.tile_sets[get_layer_by_name(self.data, "spikes")["tileset"]],
            frame,
        )

        self.tile_layers = [
            self.background_3,
            self.background_2,
            self.background,
            self.colliders,
            self.spikes,
        ]
        self.map_size = map_size = (self.data["width"], self.data["height"])
        self.tile_texture_layers = [
            create_big_texture(map_size, self.background_3.values()),
            create_big_texture(map_size, self.background_2.values()),
            create_big_texture(map_size, self.background.values()),
            create_big_texture(map_size, self.colliders.values()),
            create_big_texture(map_size, self.spikes.values()),
        ]

        self.water_texture = create_big_texture(map_size, self.water_tiles.values())
        self.water_texture.blend_mode = pygame.BLEND_RGBA_MULT
        self.water = get_tile_positions(
            self.data,
            "water",
            self.tile_sets[get_layer_by_name(self.data, "water")["tileset"]],
            frame,
        )
        self.spikes = {grid_pos: [tile] for grid_pos, tile in self.spikes.items()}

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

        self.big_freezers = {}
        seen = set()
        current = []
        for (x, y), tile in self.freezers.items():
            if (x, y) in seen:
                continue
            for x_off, y_off in [(0, 0), (1, 0), (0, 1), (1, 1)]:
                new_x, new_y = x + x_off, y + y_off
                seen.add((new_x, new_y))

                tile = self.freezers[(new_x, new_y)]
                current.append(tile)
            big_freezer = BigFreezer(
                (x * 16, y * 16), (x, y), current
            )  # FIXME don't use hardcoded tile size values...
            self.big_freezers[(x, y)] = big_freezer
            current.clear()

        for freezer in self.big_freezers.values():
            freezer.is_freezing_water = False
            freezer.spawned_prompt = False

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
            furnace.bucket = None

        filled_furnaces = "filled_furnaces"
        self.filled_furnaces = get_texture_tiles(
            interactives_layer,
            filled_furnaces,
            self.texture_tile_sets[
                get_layer_by_name(interactives_layer, filled_furnaces)["tileset"]
            ],
            frame,
        )

        buckets = "buckets"
        self.buckets = get_texture_tiles(
            interactives_layer,
            buckets,
            self.texture_tile_sets[
                get_layer_by_name(interactives_layer, buckets)["tileset"]
            ],
            frame,
        )

        self.interactives = {
            freezers: self.freezers,
            furnaces: self.furnaces,
            buckets: self.buckets,
        }
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
            # print(x, y)
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

        pools_layer = get_layer_by_name(self.data, "pools")
        pool_nodes = get_tile_positions(
            pools_layer,
            "top",
            self.texture_tile_sets[
                get_layer_by_name(lifts_layer, platforms)["tileset"]
            ],
            frame,
        ) | get_tile_positions(
            pools_layer,
            "body",
            self.texture_tile_sets[
                get_layer_by_name(lifts_layer, platforms)["tileset"]
            ],
            frame,
        )

        self.pools = {}
        seen = set()
        for x, y in pool_nodes:
            if (x, y) in seen:
                continue
            nodes = find_all_connected_nodes((x, y), pool_nodes)
            grid_x, grid_y = min(x for x, _ in nodes), min(y for _, y in nodes)
            self.pools[(grid_x, grid_y)] = Pool(
                (
                    grid_x * self.collider_cell_size[0],
                    grid_y * self.collider_cell_size[1],
                ),
                (grid_x, grid_y),
                nodes,
            )
            seen.update(nodes)

        transport_layer = get_layer_by_name(self.data, "transport")
        teleports = "teleports"
        self.teleports = get_texture_tiles(
            transport_layer,
            teleports,
            self.texture_tile_sets[
                get_layer_by_name(transport_layer, teleports)["tileset"]
            ],
            frame,
        )

        keys = "keys"
        self.keys = get_texture_tiles(
            transport_layer,
            keys,
            self.texture_tile_sets[get_layer_by_name(transport_layer, keys)["tileset"]],
            frame,
        )

        doors = "doors"
        self.doors = {}
        door_segments = get_texture_tiles(
            transport_layer,
            doors,
            self.texture_tile_sets[
                get_layer_by_name(transport_layer, doors)["tileset"]
            ],
            frame,
        )
        seen = set()
        current = []
        for (x, y), tile in door_segments.items():
            if (x, y) in seen:
                continue
            for x_off, y_off in [(0, 0), (0, 1)]:
                new_x, new_y = x + x_off, y + y_off
                seen.add((new_x, new_y))

                tile = door_segments[(new_x, new_y)]
                current.append(tile)
            doors = Doors(
                (x * 16, y * 16), (x, y), current
            )  # FIXME don't use hardcoded tile size values...
            self.doors[(x, y)] = doors
            current.clear()

        for door in self.doors.values():
            door.spawned_prompt = False

        for joiner in ["door_teleport_joiners_1"]:
            door_teleport_joiner_segments = get_tile_positions(
                transport_layer,
                joiner,
                self.texture_tile_sets[
                    get_layer_by_name(transport_layer, joiner)["tileset"]
                ],
                frame,
            )
            seen = set()
            for x, y in door_teleport_joiner_segments:
                if (x, y) in seen:
                    continue
                (endpoint_1, endpoint_2), traversed = find_end_nodes_from_path_segment(
                    (x, y), door_teleport_joiner_segments
                )
                seen.update(traversed)
                try:
                    if endpoint_1 in self.doors:
                        door = self.doors[endpoint_1]
                        teleport = self.teleports[endpoint_2]
                    else:
                        door = self.doors[endpoint_2]
                        teleport = self.teleports[endpoint_1]
                except KeyError:
                    raise Exception(
                        "joiners are not properly joining the door and the teleport, "
                        "make sure the joiners end up on the top left grid occupied by "
                        "the door and the teleport"
                    )
                door.teleport = teleport

        assert all(hasattr(door, "teleport") for door in self.doors.values())

        for joiner in ["door_key_joiners_1", "door_key_joiners_2"]:
            door_key_joiner_segments = get_tile_positions(
                transport_layer,
                joiner,
                self.texture_tile_sets[
                    get_layer_by_name(transport_layer, joiner)["tileset"]
                ],
                frame,
            )
            seen = set()
            for x, y in door_key_joiner_segments:
                if (x, y) in seen:
                    continue
                (endpoint_1, endpoint_2), traversed = find_end_nodes_from_path_segment(
                    (x, y), door_key_joiner_segments
                )
                seen.update(traversed)
                try:
                    if endpoint_1 in self.doors:
                        door = self.doors[endpoint_1]
                        key = self.keys[endpoint_2]
                    else:
                        door = self.doors[endpoint_2]
                        key = self.keys[endpoint_1]
                except KeyError:
                    raise Exception(
                        "joiners are not properly joining the door and the key, "
                        "make sure the joiners end up on the top left grid occupied by "
                        "the door and the key"
                    )
                door.key = key

        assert all(
            True if hasattr(door, "key") else [print(door.grid_position), False][-1]
            for door in self.doors.values()
        )

        self.endpoint = get_texture_tiles(
            self.data,
            "endpoint",
            self.texture_tile_sets[get_layer_by_name(self.data, "endpoint")["tileset"]],
            frame,
        )
        self.endpoint = {key: [value] for key, value in self.endpoint.items()}
        assert len(self.endpoint) == 1


def find_all_connected_nodes(start: tuple[int, int], all_nodes: set[tuple[int, int]]):
    all_traversed = {start}
    traversing = queue.Queue()
    traversing.put(start)
    while not traversing.empty():
        x, y = traversing.get()
        for x_dir, y_dir in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            new_xy = x + x_dir, y + y_dir
            if new_xy in all_traversed or new_xy not in all_nodes:
                continue

            all_traversed.add(new_xy)
            traversing.put(new_xy)

    return all_traversed


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
    # print(found_segments)
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
        # if layer_name != "water":

        try:
            grid_map[(grid_x, grid_y)] = Tile(
                position=(x, y),
                grid_position=(grid_x, grid_y),
                image=tile_set.tiles[tile_idx],
            )
        except IndexError as e:
            print(e, (grid_x, grid_y), layer_name)
        # else:
        #     grid_map[(grid_x, grid_y)] = WaterTile(
        #         position=(x, y),
        #         grid_position=(grid_x, grid_y),
        #         image=tile_set.tiles[tile_idx],
        #         idx=tile_idx,
        #     )

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
    except KeyError:
        # print(e)
        return (0, 0), (0, 0), []

    x_off, y_off = tile_map["bounds"]["x"], tile_map["bounds"]["y"]
    columns, rows = tile_map["tilemap"]["width"], tile_map["tilemap"]["height"]
    tiles = tile_map["tilemap"]["tiles"]

    return (x_off, y_off), (columns, rows), tiles


def get_layer_by_name(data: dict, name: str) -> dict:
    for layer in data["layers"]:
        if layer["name"] == name:
            return layer
    try:
        raise Exception(f"layer {name!r} not found in layer {data['name']!r}")
    except KeyError:
        return {}


def get_frame(layer: dict, frame: int) -> dict:
    for cel in layer["cels"]:
        if cel["frame"] == frame:
            return cel
    raise Exception(
        f"frame {frame!r} not found in layer {layer['name']!r}, might be empty"
    )


if __name__ == "__main__":
    Level("map_1", 0)
