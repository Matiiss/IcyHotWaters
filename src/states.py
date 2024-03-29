import types

import pygame

from . import player, settings, common, enums, animation, assets


def calculate_initial_velocity(jump_height: float, gravity: float) -> float:
    return -((2 * gravity * jump_height) ** 0.5)


class GamePlay:
    def __init__(self):
        center = (settings.WIDTH / 2, settings.HEIGHT / 2)
        self.player = types.SimpleNamespace(
            position=pygame.Vector2(center),
            velocity=pygame.Vector2(),
            rect=pygame.FRect(0, 0, 16, 32).move_to(center=center),
            walk_speed=100,
            jump_height=30,
            animation=animation.Animation(sprite_sheet=assets.images["player"]),
            state=enums.EntityState.IDLE,
            flip=False,
        )

    def update(self) -> None:
        keys = pygame.key.get_pressed()
        gravity = 200

        self.player.state = enums.EntityState.IDLE

        for event in common.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w:
                    self.player.velocity.y = calculate_initial_velocity(
                        self.player.jump_height, gravity
                    )
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

        self.player.velocity.y += gravity * common.dt
        self.player.velocity.y = pygame.math.clamp(self.player.velocity.y, -9999, 500)

        self.player.position.x += self.player.velocity.x * common.dt
        self.player.position.y += (
            self.player.velocity.y * common.dt + 0.5 * gravity * common.dt**2
        )

        self.player.rect.center = self.player.position

        if self.player.rect.bottom > settings.HEIGHT:
            # if self.player.velocity.y > 0:
            self.player.rect.bottom = settings.HEIGHT
            self.player.position.xy = self.player.rect.center

    def draw(self, surface: pygame.Surface) -> None:
        # pygame.draw.rect(surface, "red", self.player.rect)
        surface.fblits(
            [
                (
                    pygame.transform.flip(
                        self.player.animation.update(self.player.state),
                        self.player.flip,
                        False,
                    ),
                    self.player.rect,
                )
            ]
        )
