import pygame
import pygame._sdl2 as pg_sdl2  # noqa

from . import common, settings, assets


class UIManager:
    def __init__(self):
        self.widgets = []
        self.selector_arrow = SelectorArrow()

    def add(self, *widgets, initial_selected=False):
        if not initial_selected:
            self.widgets.extend(widgets)
        elif initial_selected and len(widgets) == 1:
            self.widgets.append(widgets[0])
            self.selector_arrow.last_selection = widgets[0]
            self.selector_arrow.shown = True
            self.selector_arrow.rect.midright = pygame.Vector2(
                widgets[0].rect.midleft
            ) - (
                self.selector_arrow.dist,
                0,
            )
            self.selector_arrow.current_idx = len(self.widgets) - 1
        else:
            raise Exception("only one initial selected can be specified at a time")
        return self

    def update(self):
        selected = None
        for event in common.events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_s, pygame.K_DOWN):
                    self.selector_arrow.current_idx += 1
                    if self.selector_arrow.current_idx >= len(self.widgets):
                        self.selector_arrow.current_idx = len(self.widgets) - 1
                    if self.widgets:
                        selected = self.widgets[self.selector_arrow.current_idx]
                elif event.key in (pygame.K_w, pygame.K_UP):
                    self.selector_arrow.current_idx -= 1
                    if self.selector_arrow.current_idx < 0:
                        self.selector_arrow.current_idx = 0
                    if self.widgets:
                        selected = self.widgets[self.selector_arrow.current_idx]
                elif event.key == pygame.K_RETURN:
                    if self.selector_arrow.last_selection is not None:
                        self.selector_arrow.last_selection.is_pressed = True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_RETURN:
                    if self.selector_arrow.last_selection is not None:
                        getattr(
                            self.selector_arrow.last_selection, "callback", lambda: None
                        )()

        for widget in self.widgets:
            widget.update()
            if getattr(widget, "is_selected", False):
                if selected is None:
                    selected = widget
                else:
                    widget.is_selected = False

        if selected is not None:
            self.selector_arrow.rect.midright = pygame.Vector2(
                selected.rect.midleft
            ) - (
                self.selector_arrow.dist,
                0,
            )
            self.selector_arrow.shown = True
            self.selector_arrow.last_selection = selected
        elif self.selector_arrow.last_selection is None:
            self.selector_arrow.shown = False

    def draw(self, target: pg_sdl2.Texture | None = None) -> None:
        current_target = common.renderer.target
        common.renderer.target = target

        for widget in self.widgets:
            widget.image.alpha = 150
            widget.image.draw(dstrect=widget.rect)

        if self.selector_arrow.shown:
            self.selector_arrow.image.alpha = 150
            self.selector_arrow.image.draw(dstrect=self.selector_arrow.rect)

        common.renderer.target = current_target


class SelectorArrow:
    def __init__(self, dist=16):
        self.dist = dist
        self.image = assets.images["selector_arrow"]
        self.rect = pygame.Rect(0, 0, self.image.width, self.image.height)
        self.shown = False
        self.last_selection = None
        self.current_idx = 0


class Label:
    def __init__(self, position, text: str, font: pygame.Font | None = None) -> None:
        self.position = pygame.Vector2(position)
        font = assets.fonts["pixelify_semibold"][18] if font is None else font
        text_surf = font.render(text, False, "#050e1a")
        self.image = assets.images["button_surf"].copy()
        self.rect = self.image.get_rect(center=position)
        self.image.blit(
            text_surf, text_surf.get_rect(center=self.image.get_rect().center)
        )
        self.image = pg_sdl2.Texture.from_surface(common.renderer, self.image)

    def update(self):
        pass


class Button:
    def __init__(
        self,
        position,
        text: str,
        font: pygame.Font | None = None,
        callback=lambda: None,
        pressed_image: pygame.Surface | None = None,
    ) -> None:
        self.position = pygame.Vector2(position)
        font = assets.fonts["pixelify_semibold"][18] if font is None else font
        text_surf = font.render(text, False, "#050e1a")

        surf = assets.images["button_surf"].copy()
        self.rect = surf.get_rect(center=position)
        surf.blit(text_surf, text_surf.get_rect(center=surf.get_rect().center))
        self.idle = pg_sdl2.Texture.from_surface(common.renderer, surf)

        surf = (
            assets.images["button_pressed_surf"]
            if pressed_image is None
            else pressed_image
        ).copy()
        self.rect = surf.get_rect(center=position)
        surf.blit(text_surf, text_surf.get_rect(center=surf.get_rect().center))
        self.pressed = pg_sdl2.Texture.from_surface(common.renderer, surf)

        self.image = self.idle
        self.callback = callback
        self.is_selected = False
        self.is_pressed = False

    def update(self):
        for event in common.events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.is_pressed = (
                    event.button == pygame.BUTTON_LEFT
                    and self.rect.collidepoint(event.pos)
                )

            elif event.type == pygame.MOUSEBUTTONUP:
                if self.is_pressed and self.rect.collidepoint(event.pos):
                    self.callback()
                self.is_pressed = False

            elif event.type == pygame.MOUSEMOTION:
                self.is_selected = self.rect.collidepoint(event.pos)

        if self.is_pressed:
            self.image = self.pressed
        else:
            self.image = self.idle
