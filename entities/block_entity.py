"""Display-facing wrapper for a core block or split cube."""

from __future__ import annotations

from dataclasses import dataclass

from core.block import Piece


@dataclass(frozen=True, slots=True)
class BlockEntity:
    piece: Piece
    active: bool = True