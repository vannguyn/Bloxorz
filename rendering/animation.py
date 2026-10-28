"""
Solution Replay and Animation Engine for Bloxorz.
Replays a solver path step-by-step through the core transition API.
Supports Play, Pause, Step forward/backward, and adjustable replay delay.
"""
from __future__ import annotations

from typing import Callable
from core.interfaces import GameState, Level

# Integration adapter import for transitions deferred to bottom to avoid circular import with ui package


class SolutionReplayer:
    """Manages playback of a solution move sequence."""

    def __init__(
        self,
        level: Level,
        initial_state: GameState,
        path: list[str],
        step_delay: float = 0.35,
        speed_multiplier: float = 1.0,
        apply_fn: Callable[[GameState, str, Level], GameState | None] | None = None,
    ):
        if apply_fn is None:
            from ui.dependencies import apply_move
            apply_fn = apply_move
        self.level = level
        self.path = list(path)
        self.step_delay = step_delay
        self.speed_multiplier = float(speed_multiplier)
        self.apply_fn = apply_fn

        # Pre-compute or trace trajectory states
        self.states: list[GameState] = [initial_state]
        self._build_trajectory(initial_state)

        self.current_index = 0
        self.is_playing = True
        self.timer = 0.0

    def set_speed_multiplier(self, multiplier: float) -> None:
        self.speed_multiplier = float(multiplier)

    @property
    def effective_delay(self) -> float:
        return self.step_delay / max(0.1, self.speed_multiplier)

    def _build_trajectory(self, start_state: GameState) -> None:
        curr = start_state
        for act in self.path:
            nxt = self.apply_fn(curr, act, self.level)
            if nxt is None:
                # Transition blocked or fell off
                break
            self.states.append(nxt)
            curr = nxt

    @property
    def initial_state(self) -> GameState:
        return self.states[0]

    @property
    def total_steps(self) -> int:
        return len(self.path)

    @property
    def current_state(self) -> GameState:
        return self.states[self.current_index]

    @property
    def is_finished(self) -> bool:
        return self.current_index >= len(self.states) - 1

    def play(self) -> None:
        if self.is_finished:
            self.current_index = 0
        self.is_playing = True
        self.timer = 0.0

    def pause(self) -> None:
        self.is_playing = False

    def toggle_pause(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def step_forward(self) -> bool:
        self.pause()
        if self.current_index < len(self.states) - 1:
            self.current_index += 1
            return True
        return False

    def step_backward(self) -> bool:
        self.pause()
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False

    def reset(self) -> None:
        self.current_index = 0
        self.is_playing = False
        self.timer = 0.0

    def update(self, dt: float) -> bool:
        """
        Advances the replay based on elapsed time dt (in seconds).
        Returns True if the current displayed step changed.
        """
        if self.is_finished:
            self.is_playing = False
            return False

        if not self.is_playing:
            return False

        self.timer += dt
        eff = self.effective_delay
        changed = False
        steps_taken = 0
        max_steps_per_frame = 10  # Cap against frame freezes

        while self.timer >= eff and not self.is_finished and steps_taken < max_steps_per_frame:
            self.timer -= eff
            self.current_index += 1
            changed = True
            steps_taken += 1

        if self.is_finished:
            self.is_playing = False

        return changed

