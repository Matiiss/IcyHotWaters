import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from . import common, settings, states, assets

pygame.init()
# common.screen = screen = pygame.display.set_mode(
#     (settings.WIDTH, settings.HEIGHT), flags=settings.DISPLAY_FLAGS
# )

common.window = window = pygame.Window(title=settings.TITLE, size=settings.WINDOW_SIZE)
common.renderer = renderer = pg_sdl2.Renderer(window)
renderer.logical_size = settings.SIZE
common.clock = clock = pygame.Clock()

assets.load_assets()

common.set_current_state(states.GamePlay())

title = pygame.image.load("assets/title_wrapped.png")
title_rect = title.get_rect(midtop=(settings.WIDTH / 2, 20))
title = pg_sdl2.Texture.from_surface(renderer, title)
ice = pygame.image.load("assets/ice_cube.png")

running = True
while running:
    dt = clock.tick(settings.FPS) / 1000
    common.dt = dt = pygame.math.clamp(dt, 0.0005, 0.05)
    window.title = f"{settings.TITLE} | FPS: {clock.get_fps():.0f}"

    renderer.draw_color = (0, 0, 0)
    renderer.clear()
    renderer.draw_color = (0, 150, 150)
    renderer.fill_rect((0, 0, *renderer.logical_size))

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

    # screen.blit(title, title.get_rect(center=(settings.WIDTH // 2, settings.HEIGHT // 2 - 20)))
    # title.draw(dstrect=title_rect)

    common.get_current_state().update()
    common.get_current_state().draw()

    renderer.present()
