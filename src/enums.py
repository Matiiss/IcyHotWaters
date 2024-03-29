from enum import Enum, auto


class EntityState(Enum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
