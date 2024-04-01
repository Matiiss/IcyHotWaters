import heapq
import types

import pygame

from . import player, settings, common, enums, animation, assets, level


def calculate_initial_velocity(jump_height: float, gravity: float) -> float:
    return -((2 * gravity * jump_height) ** 0.5)


class GamePlay:
    def __init__(self):
        center = (settings.WIDTH / 2, settings.HEIGHT / 2)
        self.player = types.SimpleNamespace(
            position=pygame.Vector2(240, 672),
            velocity=pygame.Vector2(),
            rect=pygame.FRect(0, 0, 16, 32).move_to(center=(240, 672)),
            collision_rect=pygame.FRect(0, 0, 7, 32).move_to(center=(240, 672)),
            mask=pygame.Mask((7, 32), fill=True),
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

    def update(self) -> None:
        keys = pygame.key.get_pressed()
        gravity = 400

        self.player.state = enums.EntityState.IDLE
        allow_repeat_jump = True
        for event in common.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w and self.player.is_grounded:
                    initial_velocity = calculate_initial_velocity(self.player.jump_height, gravity)
                    self.player.velocity.y = initial_velocity
                    self.player.jump_timer = abs(initial_velocity / gravity)
                    allow_repeat_jump = False
                elif event.key == pygame.K_a:
                    self.player.flip = True
                elif event.key == pygame.K_d:
                    self.player.flip = False

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

        if keys[pygame.K_w] and allow_repeat_jump and self.player.is_grounded and self.player.jump_timer == 0:
            initial_velocity = calculate_initial_velocity(self.player.jump_height, gravity)
            self.player.velocity.y = initial_velocity
            self.player.jump_timer = abs(initial_velocity / gravity)

        self.player.velocity.y += gravity * common.dt
        self.player.velocity.y = pygame.math.clamp(self.player.velocity.y, -9999, 700)

        self.player.position.x += self.player.velocity.x * common.dt
        self.player.position.y += (
            self.player.velocity.y * common.dt + 0.5 * gravity * common.dt**2
        )

        self.player.collision_rect.center = self.player.position

        self.handle_collisions()

        if self.player.velocity.y > 350:
            self.player.state = enums.EntityState.FALL_FAST
        elif self.player.velocity.y > 150:
            self.player.state = enums.EntityState.FALL_SLOW

        self.player.position.xy = self.player.collision_rect.center
        self.player.rect.center = self.player.collision_rect.center

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
        if grid_pos not in self.level.colliders:
            return False
        return rect.colliderect(self.level.colliders[grid_pos].rect)

    def mask_collides_in_grid(self, rect, mask, grid_pos) -> bool:
        if grid_pos not in self.level.colliders:
            return False
        tile = self.level.colliders[grid_pos]
        offset = rect.topleft - tile.position
        return bool(tile.mask.overlap(mask, offset))

    def rect_collides_any(self, rect) -> bool:
        for grid_pos in self.get_colliding_cells(rect):
            if grid_pos not in self.level.colliders:
                continue
            if self.rect_collides_in_grid(rect, grid_pos):
                break
        else:
            return False
        return True

    def mask_collides_any(self, rect, mask):
        for grid_pos in self.get_colliding_cells(rect):
            if grid_pos not in self.level.colliders:
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
        seen_displacements = set()

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
                dx += int(rect.x) - rect.x - 1
            elif dx < 0:
                dx += int(rect.x) - rect.x + 1 - 1e-8
            if dy < 0:
                dy += int(rect.y) - rect.y + 1

            rect.x += dx
            rect.y += dy

            if dx != 0:
                self.player.velocity.x = 0
                # self.player.state = enums.EntityState.IDLE
            if dy < 0:
                self.player.velocity.y = 0

            self.player.is_grounded = self.rect_collides_any(rect.move(0, 1))

    def update_camera(self):
        viewport_size = pygame.Vector2(common.renderer.get_viewport().size)
        half_viewport_size = viewport_size / 2
        self.camera = self.camera.lerp(
            self.player.position - half_viewport_size, 5 * common.dt
        )
        # self.camera = self.player.position - half_viewport_size

    def draw(self) -> None:
        for layer_texture in self.level.tile_texture_layers:
            layer_texture.draw(dstrect=-self.camera)

        player_texture = self.player.animation.update(self.player.state)
        player_texture.draw(
            dstrect=self.player.rect.topleft - self.camera, flip_x=self.player.flip
        )

        # current_color = common.renderer.draw_color
        # common.renderer.draw_color = (255, 0, 0)
        # common.renderer.fill_rect(self.player.collision_rect.move(-self.camera))
        # common.renderer.draw_color = current_color
