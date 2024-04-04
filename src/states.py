import collections
import collections.abc
import heapq
import math
import random
import types
import functools

import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from . import player, settings, common, enums, animation, assets, level, particles


def calculate_initial_velocity(jump_height: float, gravity: float) -> float:
    return -((2 * gravity * jump_height) ** 0.5)


def collide_circle(p1, r1, p2, r2):
    return p1.distance_squared_to(p2) <= (r1 + r2) ** 2


@functools.cache
def get_number_as_texture(
    number: int, font: pygame.Font | None = None
) -> tuple[pg_sdl2.Texture, pygame.Rect]:
    if font is None:
        font = assets.fonts["pixelify_medium"][14]
    surf = font.render(str(number), False, "black")
    text = pg_sdl2.Texture.from_surface(common.renderer, surf)
    return text, surf.get_rect()


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

        self.level = level.Level("map_1", 1)

        # pos = (340, 672)
        pos = (
            self.level.player_position[0] * 16,
            (self.level.player_position[1] - 1) * 16,
        )  # FIXME hardcoded values
        self.camera = (
            pygame.Vector2(pos) + (0, 16) - settings.SIZE
        )  # FIXME more hardcoded values...

        self.player = types.SimpleNamespace(
            position=pygame.Vector2(pos),
            velocity=pygame.Vector2(),
            terminal_y_vel=700,
            rect=pygame.FRect(0, 0, 16, 32).move_to(center=pos),
            collision_rect=pygame.FRect(0, 0, 7, 31).move_to(center=pos),
            mask=pygame.Mask((7, 31), fill=True),
            walk_speed=60,
            walk_speed_on_ground=60,
            jump_height=30,
            # jump_height=120,
            animation=animation.EntityAnimation(sprite_sheet=assets.images["player"]),
            state=enums.EntityState.IDLE,
            flip=False,
            is_grounded=False,
            jump_timer=0,
            inventory=collections.defaultdict(list),
            alive=True,
            in_water=False,
            active_item=None,
        )

        assets.stop_all_sounds()

        self.extra_colliders = collections.defaultdict(list)
        self.extra_cleared_colliders = collections.defaultdict(list)
        self.colliders = CombinedDict(
            self.level.colliders, self.extra_colliders, self.extra_cleared_colliders
        )

        self.extra_decorations = {}
        self.extra_cleared_decorations = {}

        pygame.time.set_timer(enums.ParticleEvent.STEAM_PARTICLE_SPAWN, 100)
        pygame.time.set_timer(enums.ParticleEvent.FURNACE_FIRE_PARTICLE_SPAWN, 150)
        pygame.time.set_timer(enums.ParticleEvent.FREEZER_ICE_PARTICLE_SPAWN, 150)
        pygame.time.set_timer(enums.ParticleEvent.DUST_PARTICLE_SPAWN, 150)

        fade_in_alpha_range = range(5, 255 + 1, 25)
        fade_out_alpha_range = range(255, 5 - 1, -25)
        self.text_particle_manager = particles.TextParticleManager(
            font=assets.fonts["pixelify_regular"][14],
            count=len(fade_in_alpha_range) + len(fade_out_alpha_range),
            delay=[50] * (len(fade_in_alpha_range) - 1)
            + [500] * 2
            + [50] * (len(fade_out_alpha_range) - 1),
            alpha=list(fade_in_alpha_range) + list(fade_out_alpha_range),
            color="black",
            aa=False,
        )
        self.furnace_particles = particles.ParticleManager(
            assets.images["steam_particle"]
        )
        self.fire_particles = particles.ParticleManager(assets.images["fire_particles"])
        self.ice_particles = particles.ParticleManager(assets.images["ice_particles"])
        self.dust_particles = particles.ParticleManager(assets.images["dust_particles"])

        self.particle_managers = [
            self.dust_particles,
            self.furnace_particles,
            self.fire_particles,
            self.ice_particles,
            self.text_particle_manager,
        ]

        self.ui_layer = pg_sdl2.Texture(common.renderer, settings.SIZE, target=True)
        self.ui_layer.blend_mode = pygame.BLENDMODE_BLEND

        self.was_down = set()

        self.player.inventory["ice_cubes"].append(
            assets.images["ice_cube_icon"]
        )
        self.player.inventory["ice_cubes"].append(
            assets.images["ice_cube_icon"]
        )
        self.player.inventory["ice_cubes"].append(
            assets.images["ice_cube_icon"]
        )

        self.player.inventory["ice_cubes"].append(
            assets.images["ice_cube_icon"]
        )

    def update(self) -> None:
        # yikes
        if not self.player.alive:
            self.__init__()

        self.extra_cleared_colliders.clear()
        self.extra_cleared_decorations.clear()

        if self.player.active_item is not None:
            if not self.player.inventory[self.player.active_item]:
                self.player.active_item = None

        keys = pygame.key.get_pressed()
        gravity = 400
        player_grid_x, player_grid_y = (
            self.player.position.x // 16,
            self.player.position.y // 16,
        )

        player_just_out_of_water = False
        if (player_grid_x, player_grid_y) in self.level.water or (
            player_grid_x,
            player_grid_y + 1,
        ) in self.level.water:
            self.player.in_water = True
            gravity = 100
        else:
            if self.player.in_water:
                player_just_out_of_water = True
            self.player.in_water = False

        if self.player.in_water:
            self.player.walk_speed = 30
        else:
            self.player.walk_speed = self.player.walk_speed_on_ground

        self.player.state = enums.EntityState.IDLE
        allow_repeat_jump = True
        e_just_pressed = False

        for event in common.events:
            if event.type == pygame.KEYDOWN:
                try:
                    self.was_down.add(event.key)
                except KeyError:
                    pass
                if event.key == pygame.K_w and self.player.is_grounded and not self.player.in_water:
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
                elif event.key == pygame.K_r:
                    self.player.alive = False
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    if self.player.flip and pygame.K_d in self.was_down:
                        self.player.flip = False
                elif event.key == pygame.K_d:
                    if not self.player.flip and pygame.K_a in self.was_down:
                        self.player.flip = True
                try:
                    self.was_down.remove(event.key)
                except KeyError:
                    pass
            elif event.type == pygame.MOUSEWHEEL:
                x, y = common.renderer.logical_size
                step_x, step_y = settings.WIDTH // 3, settings.HEIGHT // 3
                x -= event.y * step_x
                y -= event.y * step_y
                x = pygame.math.clamp(x, step_x, settings.WIDTH)
                y = pygame.math.clamp(y, step_y, settings.HEIGHT)
                common.renderer.logical_size = (x, y)
            elif event.type == enums.ParticleEvent.STEAM_PARTICLE_SPAWN:
                for furnace in self.level.furnaces.values():
                    if not furnace.is_filled:
                        continue
                    position = pygame.Vector2(furnace.rect.midtop)
                    self.furnace_particles.spawn(
                        position + pygame.Vector2(random.randint(-1, 1), 1),
                        pygame.Vector2(0, -1).rotate(random.randint(-3, 3))
                        * random.randint(40, 50),
                    )
            elif event.type == enums.ParticleEvent.FURNACE_FIRE_PARTICLE_SPAWN:
                for furnace in self.level.furnaces.values():
                    # for _ in range(random.choices([1, 2, 3], k=1, weights=[5, 3, 2])[0]):
                    position = pygame.Vector2(furnace.rect.midbottom) + (
                        random.randint(-2, 3),
                        -random.randint(4, 5),
                    )
                    self.fire_particles.spawn(
                        position,
                        pygame.Vector2(random.randint(3, 5), 0).rotate(
                            random.randint(-150, -30)
                        ),
                    )
            elif event.type == enums.ParticleEvent.FREEZER_ICE_PARTICLE_SPAWN:
                # pygame.time.set_timer(
                #     enums.ParticleEvent.FREEZER_ICE_PARTICLE_SPAWN,
                #     random.randrange(1000, 2000 + 1, 100),
                # )
                for freezer in self.level.big_freezers.values():
                    for _ in range(random.randint(0, 2)):
                        sides = [freezer.rect.left - 1, freezer.rect.right + 1]
                        side = random.randint(0, 1)
                        if side == 0:
                            position = (
                                sides[side],
                                random.randint(
                                    int(freezer.rect.top + 5),
                                    int(freezer.rect.bottom - 5),
                                ),
                            )
                            direction = pygame.Vector2(1, 0).rotate(
                                random.randint(-150, -110)
                            )
                        else:
                            position = (
                                sides[side],
                                random.randint(
                                    int(freezer.rect.top + 5),
                                    int(freezer.rect.bottom - 5),
                                ),
                            )
                            direction = pygame.Vector2(1, 0).rotate(
                                random.randint(-80, -30)
                            )

                        self.ice_particles.spawn(
                            position,
                            direction * random.randint(3, 5),
                        )
            elif event.type == enums.ParticleEvent.DUST_PARTICLE_SPAWN:
                for wheel in self.level.lift_wheels.values():
                    for _ in range(
                        int(
                            wheel.angular_velocity / wheel.angular_terminal_velocity * 5
                        )
                    ):
                        if wheel.angular_velocity > 0:
                            direction = pygame.Vector2(1, 0).rotate(
                                random.randrange(360)
                            )
                            self.dust_particles.spawn(
                                pygame.Vector2(wheel.rect.center) + direction * 1,
                                direction
                                * wheel.angular_velocity
                                / wheel.angular_terminal_velocity
                                * 10,
                            )

        self.player.velocity.x = 0
        if keys[pygame.K_a]:
            self.player.velocity.x -= self.player.walk_speed
            self.player.state = enums.EntityState.WALK
            # self.player.flipped = True
        if keys[pygame.K_d]:
            self.player.velocity.x += self.player.walk_speed
            self.player.state = enums.EntityState.WALK
            # self.player.flipped = False

        self.player.jump_timer -= common.dt
        if self.player.jump_timer <= 0:
            self.player.jump_timer = 0

        if (
            keys[pygame.K_w]
            and allow_repeat_jump
            and self.player.is_grounded
            and self.player.jump_timer == 0
            and not self.player.in_water
        ):
            initial_velocity = calculate_initial_velocity(
                self.player.jump_height, gravity
            )
            self.player.velocity.y = initial_velocity
            self.player.jump_timer = abs(initial_velocity / gravity)
        elif keys[pygame.K_w] and self.player.in_water:
            self.player.velocity.y -= 300 * common.dt
            self.player.velocity.y = max(self.player.velocity.y, -20)

        if player_just_out_of_water:
            gravity = -3000
            # self.player.velocity.y = -50

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
        if self.mask_collides_any_with_colliders(self.level.spikes, self.player.collision_rect, self.player.mask):
            self.player.alive = False

        if self.player.velocity.y > 350:
            self.player.state = enums.EntityState.FALL_FAST
        elif self.player.velocity.y > 160:
            self.player.state = enums.EntityState.FALL_SLOW

        self.player.position.xy = self.player.collision_rect.center
        self.player.rect.center = self.player.collision_rect.center

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

        if self.player.inventory["ice_cubes"] and self.player.active_item == "ice_cubes":
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
            cube_in_water = (cube_gx, cube_gy) in self.level.water
            cube_overlaps_spike = (cube_gx, cube_gy) in self.level.spikes

            cube_invalid_location = any(
                [
                    cube_collides_with_player,
                    cube_overlaps_collider,
                    cube_overlaps_interactive,
                    cube_mid_air,
                    cube_on_lift_platform,
                    cube_in_water,
                    cube_overlaps_spike,
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
                        assets.sfx["knock"].play()
                        self.extra_colliders[(cube_gx, cube_gy)].append(cube_tile)
                        self.player.inventory["ice_cubes"].pop()

        for furnace in self.level.furnaces.values():
            if collide_circle(
                pygame.Vector2(furnace.rect.center), 10, self.player.position, 10
            ):
                if e_just_pressed:
                    if self.player.inventory["buckets"] and furnace.bucket is None:
                        assets.sfx["splash"].play()
                        furnace.is_filled = True
                        furnace.bucket = self.player.inventory["buckets"].pop()
                    elif furnace.bucket is not None:
                        assets.sfx["pop"].play()
                        furnace.is_filled = False
                        self.player.inventory["buckets"].append(furnace.bucket)
                        furnace.bucket = None
                if not furnace.spawned_prompt:
                    self.text_particle_manager.spawn(
                        "PRESS E",
                        pygame.Vector2(furnace.rect.midtop) + pygame.Vector2(0, -26),
                        pygame.Vector2(0, -10),
                    )
                furnace.spawned_prompt = True
            else:
                furnace.spawned_prompt = False

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
            grid_x, grid_y = (
                pygame.Vector2(wheel.platform.collider_rect.topleft).elementwise()
                // self.level.collider_cell_size
            )
            if (grid_x, grid_y + 1) in self.extra_colliders or (
                grid_x + 1,
                grid_y + 1,
            ) in self.extra_colliders:
                wheel.platform_initial_position.y = (
                    grid_y - 2
                ) * self.level.collider_cell_size[1]
            wheel.platform.position.y = pygame.math.clamp(
                wheel.platform.position.y,
                wheel.platform_min_position,
                wheel.platform_initial_position.y,
            )
        # end wheel for loop :sobbing:

        random_ahh_time = pygame.time.get_ticks()
        to_remove = []  # because couldn't care less
        for pos, bucket in self.level.buckets.items():
            bucket.rect.top = (
                bucket.position.y
                - 2
                - math.sin(
                    (random_ahh_time + (bucket.position.x % 100) * 1000) / 1000 * 2
                )
                * 4
            )
            if collide_circle(
                bucket.position + (8, 8), 8, self.player.position, 8
            ):  # hardcoded values once again...
                self.player.inventory["buckets"].append(bucket)
                to_remove.append(pos)
                assets.sfx["pop"].play()
        for pos in to_remove:
            self.level.buckets.pop(pos)

        for freezer in self.level.big_freezers.values():
            if collide_circle(
                pygame.Vector2(freezer.rect.center), 18, self.player.position, 10
            ):
                if e_just_pressed:
                    if self.player.inventory["buckets"] and freezer.bucket is None:
                        freezer.is_freezing_water = True
                        freezer.bucket = self.player.inventory["buckets"].pop()
                        assets.sfx["humm"].play()
                    elif freezer.bucket is not None:
                        assets.sfx["humm"].stop()
                        assets.sfx["pop"].play()
                        self.text_particle_manager.spawn(
                            "CANCELLED",
                            pygame.Vector2(freezer.rect.midtop)
                            + pygame.Vector2(0, -10),
                            pygame.Vector2(0, -10),
                        )
                        freezer.is_freezing_water = False
                        self.player.inventory["buckets"].append(freezer.bucket)
                        freezer.bucket = None
                    elif not self.player.inventory["buckets"]:
                        assets.sfx["no"].play()
                        self.text_particle_manager.spawn(
                            "NO BUCKETS",
                            pygame.Vector2(freezer.rect.midtop)
                            + pygame.Vector2(0, -10),
                            pygame.Vector2(0, -10),
                        )
                if not freezer.spawned_prompt:
                    self.text_particle_manager.spawn(
                        "PRESS E",
                        pygame.Vector2(freezer.rect.midtop) + pygame.Vector2(0, -10),
                        pygame.Vector2(0, -10),
                    )
                freezer.spawned_prompt = True
            else:
                freezer.spawned_prompt = False

        for freezer in self.level.big_freezers.values():
            if not freezer.is_freezing_water:
                freezer.loading_bar_image = None
                freezer.loading_bar_animation.reset()
                continue
            try:
                freezer.loading_bar_image = freezer.loading_bar_animation.update(
                    enums.LoadingState.THINGY
                )
            except StopIteration:
                assets.sfx["humm"].stop()
                assets.sfx["ding"].play()
                freezer.is_freezing_water = False
                freezer.loading_bar_image = None
                freezer.bucket = None
                self.player.inventory["ice_cubes"].append(
                    assets.images["ice_cube_icon"]
                )

        for particle_manager in self.particle_managers:
            particle_manager.update()
        self.update_camera()

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

    @staticmethod
    def mask_collides_in_grid_with_colliders(colliders, rect, mask, grid_pos) -> bool:
        if grid_pos not in colliders:
            return False

        return any(
            tile.mask.overlap(mask, rect.topleft - tile.position)
            for tile in colliders[grid_pos]
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

    def mask_collides_any_with_colliders(self, colliders, rect, mask) -> bool:
        for grid_pos in self.get_colliding_cells(rect):
            if grid_pos not in colliders:
                continue
            if self.mask_collides_in_grid_with_colliders(colliders, rect, mask, grid_pos):
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
        displacements = [
            (0, 0, 0, 0)
        ]  # dist_squared, penalty, displacement_x, displacement_y
        seen_displacements = {(0, 0)}

        while True:
            _, _, dis_x, dis_y = heapq.heappop(displacements)
            dis_xy = (dis_x, dis_y)
            displaced_rect = rect.move(dis_xy)

            if not self.mask_collides_any(displaced_rect, mask):
                best_displacement = dis_xy
                break
            else:
                for dx, dy in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
                    new_dis_xy = new_dis_x, new_dis_y = dis_x + dx, dis_y + dy
                    if new_dis_xy in seen_displacements:
                        continue

                    dist_squared = new_dis_x**2 + new_dis_y**2

                    # give preference to direct upwards movement, this allows to climb slopes
                    # also allows climbing slopes using the head, at least if going to the right...
                    if dis_x == 0 and dy == -1:
                        # print(new_dis_xy)
                        # since distance is squared this gives a roughly 3 pixel advantage
                        # for upwards movement, i.e., the slope can be 3 pixels up for 1 pixel across
                        dist_squared -= 9

                    # gives preference to upwards and downwards movement to combat climbing slopes
                    # from below
                    penalty = 0
                    if dy == 0:
                        penalty = 1

                    seen_displacements.add(new_dis_xy)
                    heapq.heappush(
                        displacements, (dist_squared, penalty, new_dis_x, new_dis_y)
                    )

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
                if self.player.velocity.y * dy < 0:
                    self.player.velocity.y = 0

            self.player.is_grounded = self.rect_collides_any(rect.move(0, 1))

    def update_camera(self):
        viewport_size = pygame.Vector2(
            common.renderer.logical_size  # noqa PyCharm's type hints...
        )
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
        actual_camera = self.camera.copy()
        # self.camera = round(self.camera)  # dunno, kinda choppy when zoomed in

        for layer_texture in self.level.tile_texture_layers:
            layer_texture.draw(dstrect=-self.camera)

        for interactives in self.level.interactives.values():
            for tile in interactives.values():
                tile.image.draw(dstrect=tile.rect.topleft - self.camera)
        for grid_pos, furnace in self.level.furnaces.items():
            if furnace.is_filled:
                tile = self.level.filled_furnaces[grid_pos]
                tile.image.draw(dstrect=tile.rect.topleft - self.camera)

        for platform in self.level.lift_platforms.values():
            platform.texture.draw(dstrect=platform.rect.topleft - self.camera)
        for wheel in self.level.lift_wheels.values():
            # scuffed
            assets.images["rope"].draw(
                dstrect=(
                    int(wheel.platform.rect.centerx) - 1 - self.camera.x,
                    wheel.platform_min_position - self.camera.y,
                    assets.images["rope"].width,
                    abs(wheel.platform_min_position - wheel.platform.rect.top),
                ),
                srcrect=(
                    0,
                    assets.images["rope"].height
                    - abs(wheel.platform_min_position - wheel.platform.rect.top),
                    assets.images["rope"].width,
                    abs(wheel.platform_min_position - wheel.platform.rect.top),
                ),
            )
            # what the even is this??? thingy? other_thingy? cmon
            # destination = pygame.Vector2(int(wheel.platform.rect.centerx) - 1, wheel.platform_min_position)
            # start = pygame.Vector2(wheel.rect.center)
            # thingy = destination - start
            # angle = thingy.as_polar()[1]
            # other_thingy = pygame.Vector2((wheel.platform.rect.centerx - wheel.rect.centerx) / 2, 0).rotate(angle)
            # more_thingies = pygame.Vector2((wheel.platform.rect.centerx - wheel.rect.centerx) / 2, 0).rotate(angle)
            # assets.images["rope"].draw(
            #     dstrect=(
            #         start
            #         - self.camera
            #         - (
            #             -other_thingy.x,
            #             (wheel.platform.rect.centerx - wheel.rect.centerx)
            #             - 8
            #             + other_thingy.y,
            #         ),
            #         (2, wheel.platform.rect.centerx - wheel.rect.centerx + 16),
            #     ),
            #     angle=angle - 90,
            # )
            # alr, scrap this, we're using the background for this, I can't... :sobbing:

            wheel.texture.draw(
                dstrect=wheel.rect.topleft - self.camera, angle=wheel.angle
            )

        for tiles in self.extra_colliders.values():
            for texture_tile in tiles:
                texture_tile.image.draw(dstrect=texture_tile.rect.topleft - self.camera)

        for texture_tile in self.extra_cleared_decorations.values():
            texture_tile.image.draw(dstrect=texture_tile.rect.topleft - self.camera)

        # render the loading bar in front of the cubes
        random_ahh_time = pygame.time.get_ticks()
        for freezer in self.level.big_freezers.values():
            if freezer.loading_bar_image is None:
                continue
            freezer.loading_bar_rect.left = (
                freezer.loading_bar_position.x
                + math.sin(random_ahh_time / 1000 * 70) * 1
            )
            freezer.loading_bar_image.draw(
                dstrect=freezer.loading_bar_rect.topleft - self.camera
            )

        for particle_manager in self.particle_managers:
            particle_manager.render(self.camera)

        player_texture = self.player.animation.update(self.player.state)
        player_texture.draw(
            dstrect=self.player.rect.topleft - self.camera, flip_x=self.player.flip
        )

        self.level.water_texture.draw(dstrect=-self.camera)

        mouse_pos = pygame.Vector2(pygame.mouse.get_pos()).elementwise() / common.renderer.scale
        mouse_just_pressed = False
        for event in common.events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    mouse_just_pressed = True

        current_target = common.renderer.target
        current_color = common.renderer.draw_color
        common.renderer.target = self.ui_layer
        common.renderer.draw_color = (0, 0, 0, 0)
        common.renderer.clear()
        common.renderer.draw_color = current_color

        yep = 0
        for why_not, items in sorted(self.player.inventory.items()):
            # even more scuffed (maybe)
            if not items:
                continue
            if isinstance(items[0], level.TextureTile):
                item_rect = items[0].rect.move_to(topleft=(yep * (16 + 2) + 2, 2))
                if mouse_just_pressed and item_rect.collidepoint(mouse_pos):
                    if self.player.active_item is None or self.player.active_item != why_not:
                        self.player.active_item = why_not
                    elif self.player.active_item == why_not:
                        self.player.active_item = None
                if self.player.active_item == why_not:
                    assets.images["item_frame_selected"].draw(dstrect=item_rect)
                else:
                    assets.images["item_frame"].draw(dstrect=item_rect)
                items[0].image.draw(dstrect=item_rect)
                texture, rect = get_number_as_texture(len(items))
                texture.draw(
                    dstrect=rect.move_to(midtop=item_rect.move(0, 2).midbottom)
                )
            else:
                raise NotImplemented("mmm")
            yep += 1

        common.renderer.target = current_target

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

        self.ui_layer.draw()
        self.camera = actual_camera
