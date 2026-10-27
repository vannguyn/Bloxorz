"""
Bridge connecting the GUI with search solvers.
Supports both the synchronous on_solve() interface (plan §4)
and an asynchronous multiprocessing worker to prevent Pygame event loop blocking.
"""
from __future__ import annotations

import multiprocessing as mp
from enum import Enum
from typing import Callable
from core.interfaces import BlockState, GameState, Level, SolverResult
from ui.dependencies import get_solver, run_solver


class SolverBridgeState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    ERROR = "error"


def on_solve(algo: str, level: Level, start: GameState | BlockState) -> SolverResult:
    """
    Synchronous solver invocation per docs/parallel-engineering-plan.en.md §4.
    Runs the chosen solver directly and returns SolverResult.
    """
    # Keep the public helper compatible with older callers that passed only
    # level.start instead of the complete GameState contract.
    if isinstance(start, BlockState):
        start = GameState(
            block=start,
            bridge_mask=getattr(level, "initial_bridge_mask", 0),
        )

    solver = get_solver(algo)
    return run_solver(solver, level, start)


def _worker_entry(
    algo: str,
    level: Level,
    start: GameState,
    result_queue: mp.Queue,
) -> None:
    """Entry point for the isolated background solver process."""
    try:
        solver = get_solver(algo)
        res = run_solver(solver, level, start)
        result_queue.put(("SUCCESS", res))
    except Exception as exc:
        result_queue.put(("ERROR", str(exc)))


class AsyncSolverBridge:
    """
    Non-blocking solver process runner.
    Ensures Pygame maintains 60 FPS while search algorithms execute in an isolated process.
    """

    def __init__(self):
        self.state = SolverBridgeState.IDLE
        self.current_algo: str | None = None
        self._process: mp.Process | None = None
        self._result_queue: mp.Queue | None = None
        self.last_result: SolverResult | None = None
        self.error_message: str | None = None

    def start_solve(self, algo: str, level: Level, start: GameState) -> None:
        """Launches search in a separate process."""
        self.cancel()  # Clean up any existing run

        self.current_algo = algo
        self.state = SolverBridgeState.RUNNING
        self.last_result = None
        self.error_message = None

        self._result_queue = mp.Queue()
        self._process = mp.Process(
            target=_worker_entry,
            args=(algo, level, start, self._result_queue),
            daemon=True,
        )
        self._process.start()

    def cancel(self) -> None:
        """Terminates any active solver worker."""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=0.1)
        self._process = None
        self._result_queue = None
        if self.state == SolverBridgeState.RUNNING:
            self.state = SolverBridgeState.CANCELLED

    def poll(self) -> SolverResult | None:
        """
        Polls the worker queue non-blockingly. Called on each Pygame frame.
        Returns the completed SolverResult if finished on this frame, else None.
        """
        if self.state != SolverBridgeState.RUNNING or not self._result_queue:
            return None

        try:
            status, payload = self._result_queue.get_nowait()
            if status == "SUCCESS":
                self.last_result = payload
                self.state = SolverBridgeState.FINISHED
                self._process = None
                return payload
            else:
                self.error_message = str(payload)
                self.state = SolverBridgeState.ERROR
                self._process = None
                return None
        except Exception:
            # Queue is empty, still calculating
            pass

        # Check if process unexpectedly died
        if self._process and not self._process.is_alive():
            if self.state == SolverBridgeState.RUNNING:
                self.state = SolverBridgeState.ERROR
                self.error_message = "Solver worker process terminated unexpectedly."
                self._process = None

        return None
