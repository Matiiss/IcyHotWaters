import pygame

from . import common, settings, states, assets

pygame.init()
common.screen = screen = pygame.display.set_mode(
    (settings.WIDTH, settings.HEIGHT), flags=settings.DISPLAY_FLAGS
)
clock = pygame.Clock()

assets.load_assets()

common.set_current_state(states.GamePlay())

title = pygame.image.load("assets/title_small.png").convert_alpha()
ice = pygame.image.load("assets/ice_cube.png").convert_alpha()

running = True
while running:
    dt = clock.tick(settings.FPS) / 1000
    common.dt = dt = pygame.math.clamp(dt, 0.0005, 0.05)
    pygame.display.set_caption(f"{settings.TITLE} | FPS: {clock.get_fps():.0f}")
    screen.fill("darkgreen")

    events = pygame.event.get()
    common.events = events
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # pygame.draw.rect(
    #     screen,
    #     "red",
    #     pygame.Rect(0, 0, 16, 32).move_to(
    #         center=(settings.WIDTH / 2, settings.HEIGHT / 2)
    #     ),
    # )
    #
    # for y in range(settings.HEIGHT // 16):
    #     for x in range(settings.WIDTH // 16):
    #         screen.blit(ice, (x * 16, y * 16))

    screen.blit(title, (5, 5))

    common.get_current_state().update()
    common.get_current_state().draw(common.screen)

    pygame.display.flip()
