from enum import Enum, IntEnum, auto

import pygame


class EntityState(Enum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
    FALL_FAST = auto()
    FALL_SLOW = auto()


class ParticleEvent(IntEnum):
    FURNACE_PARTICLE_SPAWN = pygame.event.custom_type()
