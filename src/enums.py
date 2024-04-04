from enum import Enum, IntEnum, auto

import pygame


class EntityState(Enum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
    FALL_FAST = auto()
    FALL_SLOW = auto()


class ParticleEvent(IntEnum):
    STEAM_PARTICLE_SPAWN = pygame.event.custom_type()
    FURNACE_FIRE_PARTICLE_SPAWN = pygame.event.custom_type()
    FREEZER_ICE_PARTICLE_SPAWN = pygame.event.custom_type()
    DUST_PARTICLE_SPAWN = pygame.event.custom_type()


class LoadingState(Enum):
    THINGY = auto()
