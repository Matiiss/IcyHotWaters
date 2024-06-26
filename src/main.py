import itertools

import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from . import common, settings, assets, states

pygame.init()
# common.screen = screen = pygame.display.set_mode(
#     (settings.WIDTH, settings.HEIGHT), flags=settings.DISPLAY_FLAGS
# )

common.window = window = pygame.Window(title=settings.TITLE, size=settings.WINDOW_SIZE)
common.renderer = renderer = pg_sdl2.Renderer(window)
renderer.logical_size = settings.SIZE
common.clock = clock = pygame.Clock()

assets.load_assets()

# common.set_current_state(states.GamePlay())
common.set_current_state(states.MainMenu())

# title = pygame.image.load("assets/title_wrapped.png")
# title_rect = title.get_rect(midtop=(settings.WIDTH / 2, 20))
# title = pg_sdl2.Texture.from_surface(renderer, title)
# ice = pygame.image.load("assets/ice_cube.png")

MUSIC_ENDED = pygame.event.custom_type()
music_cycle = itertools.cycle([f"assets/music/track_{i}.mp3" for i in range(1, 5 + 1)])
pygame.mixer.music.set_endevent(MUSIC_ENDED)
pygame.mixer.music.load(next(music_cycle))
pygame.mixer.music.queue(next(music_cycle))
pygame.mixer.music.play()

pygame.mixer.music.set_volume(0.1)

# prev_sfx_volume = common.sfx_volume

running = True
while running:
    dt = clock.tick(settings.FPS) / 1000
    common.dt = dt = pygame.math.clamp(dt, 0.0005, 0.05)
    window.title = f"{settings.TITLE} | FPS: {clock.get_fps():.0f}"

    renderer.draw_color = (0, 0, 0)
    renderer.clear()

    events = pygame.event.get()
    common.events = events
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                common.set_current_state(states.MainMenu())

    for event in common.events:
        if event.type == MUSIC_ENDED:
            pygame.mixer.music.queue(next(music_cycle))

    # pygame.mixer.music.set_volume(common.music_volume)
    # if prev_sfx_volume != common.sfx_volume:
    #     assets.set_sound_volume(common.sfx_volume)
    #     prev_sfx_volume = common.sfx_volume

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
