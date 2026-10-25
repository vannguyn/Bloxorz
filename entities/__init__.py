"""Game entities shared by the logic and presentation layers."""

from entities.block_entity import BlockEntity
from entities.bridge import Bridge
from entities.switch import Switch, SwitchEffect
from entities.tile import Tile, TileType

__all__ = ["BlockEntity", "Bridge", "Switch", "SwitchEffect", "Tile", "TileType"]