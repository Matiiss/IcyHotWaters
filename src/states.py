import collections
import collections.abc
import heapq
import math
import random
import types

import pygame

from . import player, settings, common, enums, animation, assets, level, particles


def calculate_initial_velocity(jump_height: float, gravity: float) -> float:
    return -((2 * gravity * jump_height) ** 0.5)


def collide_circle(p1, r1, p2, r2):
    return p1.distance_squared_to(p2) <= (r1 + r2) ** 2


class CombinedDict:
    def __init__(self, *dicts):
        super().__init__()
        self.dicts = dicts

    def __getitem__(self, item):
        items = []
        for dct in self.dicts:
            if item not in dct:
                continue

            value = dct[item]
            if isinstance(value, collections.abc.Iterable):
                items.extend(value)
            else:
                items.append(value)

        return items

    def __contains__(self, item):
        for dct in self.dicts:
            if item in dct:
                return True
        return False

    def keys(self):
        for dct in self.dicts:
            yield from dct.keys()

    def values(self):
        for dct in self.dicts:
            for value in dct.values():
                if not isinstance(value, collections.abc.Iterable):
                    yield [value]
                else:
                    yield value

    def items(self):
        for dct in self.dicts:
            yield from dct.items()


class GamePlay:
    def __init__(self):
        center = (settings.WIDTH / 2, settings.HEIGHT / 2)
        pos = (340, 672)
        self.player = types.SimpleNamespace(
            position=pygame.Vector2(pos),
            velocity=pygame.Vector2(),
            terminal_y_vel=700,
            rect=pygame.FRect(0, 0, 16, 32).move_to(center=pos),
            collision_rect=pygame.FRect(0, 0, 7, 31).move_to(center=pos),
            mask=pygame.Mask((7, 31), fill=True),
            walk_speed=60,
            jump_height=30,
            animation=animation.Animation(sprite_sheet=assets.images["player"]),
            state=enums.EntityState.IDLE,
            flip=False,
            is_grounded=False,
            jump_timer=0,
        )

        self.level = level.Level("map_1")

        self.camera = pygame.Vector2()

        self.extra_colliders = collections.defaultdict(list)
        self.extra_cleared_colliders = collections.defaultdict(list)
        self.colliders = CombinedDict(
            self.level.colliders, self.extra_colliders, self.extra_cleared_colliders
        )

        self.extra_decorations = {}
        self.extra_cleared_decorations = {}

        self.furnace_particles = particles.ParticleManager(
            assets.images["steam_particle"]
        )
        pygame.time.set_timer(enums.ParticleEvent.FURNACE_PARTICLE_SPAWN, 100)

        fade_in_alpha_range = range(5, 255 + 1, 25)
        fade_out_alpha_range = range(255, 5 - 1, -25)
        self.furnace_prompt_particles = particles.ParticleManager.from_string(
            assets.fonts["default"][16],
            "Press E",
            len(fade_in_alpha_range) + len(fade_out_alpha_range),
            delay=[50] * (len(fade_in_alpha_range) - 1)
            + [500] * 2
            + [50] * (len(fade_out_alpha_range) - 1),
            alpha=list(fade_in_alpha_range) + list(fade_out_alpha_range),
            color="black",
            aa=False,
        )

    def update(self) -> None:
        self.extra_cleared_colliders.clear()
        self.extra_cleared_decorations.clear()

        keys = pygame.key.get_pressed()
        gravity = 400

        self.player.state = enums.EntityState.IDLE
        allow_repeat_jump = True
        e_just_pressed = False
        for event in common.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w and self.player.is_grounded:
                    initial_velocity = calculate_initial_velocity(
                        self.player.jump_height, gravity
                    )
                    self.player.velocity.y = initial_velocity
                    self.player.jump_timer = abs(initial_velocity / gravity)
                    allow_repeat_jump = False
                elif event.key == pygame.K_a:
                    self.player.flip = True
                elif event.key == pygame.K_d:
                    self.player.flip = False
                elif event.key == pygame.K_e:
                    e_just_pressed = True
            elif event.type == pygame.MOUSEWHEEL:
                c_x, c_y = common.renderer.scale
                c_x += event.y * 1
                c_y += event.y * 1
                c_x = pygame.math.clamp(c_x, 2, 5)
                c_y = pygame.math.clamp(c_y, 2, 5)
                common.renderer.scale = (c_x, c_y)
            elif event.type == enums.ParticleEvent.FURNACE_PARTICLE_SPAWN:
                for furnace in self.level.furnaces.values():
                    if not furnace.is_filled:
                        continue
                    position = pygame.Vector2(furnace.rect.midtop)
                    self.furnace_particles.spawn(
                        position + pygame.Vector2(random.randint(-1, 1), 1),
                        pygame.Vector2(0, -1).rotate(random.randint(-3, 3))
                        * random.randint(40, 50),
                    )

        self.player.velocity.x = 0
        if keys[pygame.K_a]:
            self.player.velocity.x -= self.player.walk_speed
            self.player.state = enums.EntityState.WALK
        if keys[pygame.K_d]:
            self.player.velocity.x += self.player.walk_speed
            self.player.state = enums.EntityState.WALK

        self.player.jump_timer -= common.dt
        if self.player.jump_timer <= 0:
            self.player.jump_timer = 0

        if (
            keys[pygame.K_w]
            and allow_repeat_jump
            and self.player.is_grounded
            and self.player.jump_timer == 0
        ):
            initial_velocity = calculate_initial_velocity(
                self.player.jump_height, gravity
            )
            self.player.velocity.y = initial_velocity
            self.player.jump_timer = abs(initial_velocity / gravity)

        self.player.velocity.y += gravity * common.dt
        self.player.velocity.y = pygame.math.clamp(
            self.player.velocity.y, -9999, self.player.terminal_y_vel
        )

        self.player.position.x += self.player.velocity.x * common.dt
        self.player.position.y += (
            self.player.velocity.y * common.dt + 0.5 * gravity * common.dt**2
        )

        self.player.collision_rect.center = self.player.position

        for platform in self.level.lift_platforms.values():
            # platform.position.y += -5 * common.dt
            for position in self.get_colliding_cells(platform.collider_rect):
                self.extra_cleared_colliders[position].append(platform.collider)

        self.handle_collisions()

        if self.player.velocity.y > 350:
            self.player.state = enums.EntityState.FALL_FAST
        elif self.player.velocity.y > 160:
            self.player.state = enums.EntityState.FALL_SLOW

        self.player.position.xy = self.player.collision_rect.center
        self.player.rect.center = self.player.collision_rect.center

        self.update_camera()

        mouse_pos = (
            pygame.Vector2(pygame.mouse.get_pos()).elementwise()
            / common.renderer.scale  # noqa
        )
        mouse_world_pos = self.camera + mouse_pos
        m_gx, m_gy = mouse_grid_pos = (
            mouse_world_pos.elementwise() // self.level.collider_cell_size
        )

        player_grid_pos = (
            self.player.position.elementwise() // self.level.collider_cell_size
        )
        cube_gx = int(
            pygame.math.clamp(m_gx, player_grid_pos.x - 2, player_grid_pos.x + 2)
        )
        cube_gy = int(
            pygame.math.clamp(m_gy, player_grid_pos.y - 2, player_grid_pos.y + 2)
        )
        cube_tile = level.TextureTile(
            (
                cube_gx * self.level.collider_cell_size[0],
                cube_gy * self.level.collider_cell_size[1],
            ),
            (cube_gx, cube_gy),
            assets.images["ice_cube"],
        )
        cube_collides_with_player = self.player.collision_rect.colliderect(
            cube_tile.rect
        )
        cube_overlaps_collider = (cube_gx, cube_gy) in self.colliders and any(
            cube_tile.rect.colliderect(collider.rect)
            for collider in self.colliders[(cube_gx, cube_gy)]
        )
        cube_overlaps_interactive = (
            cube_gx,
            cube_gy,
        ) in self.level.interactives_grid_positions
        cube_mid_air = True
        if (cube_gx, cube_gy + 1) in self.colliders:
            cube_mid_air = not any(
                cube_tile.rect.move(0, 1).colliderect(collider.rect)
                for collider in self.colliders[(cube_gx, cube_gy + 1)]
            )
        if (
            cube_mid_air
            and (cube_gx, cube_gy + 1) in self.level.interactives_grid_positions
        ):
            cube_mid_air = False
        cube_on_lift_platform = any(
            isinstance(collider, level.LiftPlatform.Collider)
            and cube_tile.rect.move(0, 1).colliderect(collider.rect)
            for collider in self.colliders[(cube_gx, cube_gy + 1)]
        )

        cube_invalid_location = any(
            [
                cube_collides_with_player,
                cube_overlaps_collider,
                cube_overlaps_interactive,
                cube_mid_air,
                cube_on_lift_platform,
            ]
        )

        self.extra_cleared_decorations[(cube_gx, cube_gy)] = cube_tile

        if cube_invalid_location:
            cube_tile.image = assets.images["ice_cube_invalid"]

        for event in common.events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    if cube_invalid_location:
                        continue
                    self.extra_colliders[(cube_gx, cube_gy)].append(cube_tile)

        self.furnace_particles.update()

        for furnace in self.level.furnaces.values():
            if collide_circle(
                pygame.Vector2(furnace.rect.center), 10, self.player.position, 10
            ):
                if e_just_pressed:
                    furnace.is_filled = not furnace.is_filled
                if not furnace.spawned_prompt:
                    self.furnace_prompt_particles.spawn(
                        pygame.Vector2(furnace.rect.midtop) + pygame.Vector2(0, -20),
                        pygame.Vector2(),
                    )
                furnace.spawned_prompt = True
            else:
                furnace.spawned_prompt = False

        self.furnace_prompt_particles.update()

        for wheel in self.level.lift_wheels.values():
            if any(
                collide_circle(pygame.Vector2(wheel.rect.center), 8, p.pos, 3)
                for p in self.furnace_particles.particles
            ):
                wheel.angular_velocity += wheel.angular_acceleration * common.dt

            wheel.angular_velocity += wheel.drag * common.dt
            wheel.angular_velocity = pygame.math.clamp(
                wheel.angular_velocity, 0, wheel.angular_terminal_velocity
            )
            wheel.angle += wheel.angular_velocity * common.dt
            wheel.platform.position.y += (
                -5
                * wheel.angular_velocity
                / wheel.angular_terminal_velocity
                * common.dt
            )
            if wheel.angular_velocity == 0:
                wheel.platform.position = wheel.platform.position.move_towards(
                    wheel.platform_initial_position, 5 * common.dt
                )
            wheel.platform.position.y = pygame.math.clamp(
                wheel.platform.position.y,
                wheel.platform_min_position,
                wheel.platform_initial_position.y,
            )

    def get_colliding_cells(self, rect):
        min_x = int(rect.x // self.level.collider_cell_size[0])
        min_y = int(rect.y // self.level.collider_cell_size[1])
        max_x = int(rect.right // self.level.collider_cell_size[0])
        max_y = int(rect.bottom // self.level.collider_cell_size[1])

        for grid_y in range(min_y, max_y + 1):
            for grid_x in range(min_x, max_x + 1):
                yield grid_x, grid_y

    def rect_collides_in_grid(self, rect, grid_pos) -> bool:
        if grid_pos not in self.colliders:
            return False
        return any(rect.colliderect(tile.rect) for tile in self.colliders[grid_pos])

    def mask_collides_in_grid(self, rect, mask, grid_pos) -> bool:
        if grid_pos not in self.colliders:
            return False

        return any(
            tile.mask.overlap(mask, rect.topleft - tile.position)
            for tile in self.colliders[grid_pos]
        )

    def rect_collides_any(self, rect) -> bool:
        for grid_pos in self.get_colliding_cells(rect):
            if grid_pos not in self.colliders:
                continue
            if self.rect_collides_in_grid(rect, grid_pos):
                break
        else:
            return False
        return True

    def mask_collides_any(self, rect, mask):
        for grid_pos in self.get_colliding_cells(rect):
            if grid_pos not in self.colliders:
                continue
            if self.mask_collides_in_grid(rect, mask, grid_pos):
                break
        else:
            return False
        return True

    def handle_collisions(self):
        self.player.is_grounded = False
        rect = self.player.collision_rect
        mask = self.player.mask

        if not self.rect_collides_any(rect):
            return

        best_displacement = None
        displacements = [(0, 0, 0)]  # dist_squared, displacement_x, displacement_y
        seen_displacements = {(0, 0)}

        while True:
            _, dis_x, dis_y = heapq.heappop(displacements)
            dis_xy = (dis_x, dis_y)
            displaced_rect = rect.move(dis_xy)

            if not self.mask_collides_any(displaced_rect, mask):
                best_displacement = dis_xy
                break
            else:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    new_dis_xy = new_dis_x, new_dis_y = dis_x + dx, dis_y + dy
                    if new_dis_xy in seen_displacements:
                        continue

                    dist_squared = new_dis_x**2 + new_dis_y**2
                    seen_displacements.add(new_dis_xy)
                    heapq.heappush(displacements, (dist_squared, new_dis_x, new_dis_y))

        if best_displacement is None:
            print("uh oh")
        else:
            dx, dy = best_displacement

            if dx > 0:
                dx += math.floor(rect.x) - rect.x
            elif dx < 0:
                dx += math.ceil(rect.x) - rect.x

            if dy > 0:
                dy += math.floor(rect.y) - rect.y
            elif dy < 0:
                dy += math.ceil(rect.y) - rect.y

            rect.x += dx
            rect.y += dy

            if dx != 0:
                self.player.velocity.x = 0
                # self.player.state = enums.EntityState.IDLE
            if dy != 0:
                self.player.velocity.y = 0

            self.player.is_grounded = self.rect_collides_any(rect.move(0, 1))

    def update_camera(self):
        viewport_size = pygame.Vector2(common.renderer.get_viewport().size)
        half_viewport_size = viewport_size / 2
        self.camera = self.camera.lerp(
            self.player.position - half_viewport_size, 5 * common.dt
        )

        for event in common.events:
            if event.type == pygame.MOUSEWHEEL:
                self.camera = self.player.position - half_viewport_size

        self.camera.x = pygame.math.clamp(
            self.camera.x, 0, self.level.map_size[0] - viewport_size[0]
        )
        self.camera.y = pygame.math.clamp(
            self.camera.y, 0, self.level.map_size[1] - viewport_size[1]
        )

    def draw(self) -> None:
        for layer_texture in self.level.tile_texture_layers:
            layer_texture.draw(dstrect=-self.camera)

        for interactives in self.level.interactives.values():
            for tile in interactives.values():
                tile.image.draw(dstrect=tile.rect.topleft - self.camera)

        for platform in self.level.lift_platforms.values():
            platform.texture.draw(dstrect=platform.rect.topleft - self.camera)
        for wheel in self.level.lift_wheels.values():
            wheel.texture.draw(
                dstrect=wheel.rect.topleft - self.camera, angle=wheel.angle
            )

        for tiles in self.extra_colliders.values():
            for texture_tile in tiles:
                texture_tile.image.draw(dstrect=texture_tile.rect.topleft - self.camera)

        for texture_tile in self.extra_cleared_decorations.values():
            texture_tile.image.draw(dstrect=texture_tile.rect.topleft - self.camera)

        player_texture = self.player.animation.update(self.player.state)
        player_texture.draw(
            dstrect=self.player.rect.topleft - self.camera, flip_x=self.player.flip
        )

        self.furnace_particles.render(self.camera)
        self.furnace_prompt_particles.render(self.camera)

        # current_color = common.renderer.draw_color
        # common.renderer.draw_color = (255, 0, 0)
        # for colliders in self.colliders.values():
        #     for collider in colliders:
        #         common.renderer.fill_rect(collider.rect.move(-self.camera))
        # common.renderer.draw_color = current_color
        #
        # current_color = common.renderer.draw_color
        # common.renderer.draw_color = (255, 255, 0)
        # common.renderer.fill_rect(self.player.collision_rect.move(-self.camera))
        # common.renderer.draw_color = current_color
