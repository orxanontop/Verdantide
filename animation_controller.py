from __future__ import annotations

"""animation_controller.py

Tiny Tk 'after'-based scheduler for 150–300ms micro-animations.
- tween(): runs an eased 0..1 timeline
- run_sequence(): chains multiple animation steps
"""

import time
from typing import Callable


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


_EASING = {
    "out_cubic": _ease_out_cubic,
    "in_out_quad": _ease_in_out_quad,
}


class AnimationController:
    """Tiny scheduler for 150–300ms micro-animations using Tk's `after`."""

    def __init__(self, widget):
        self._w = widget
        self._jobs: set[str] = set()

    def cancel_all(self) -> None:
        for job in list(self._jobs):
            try:
                self._w.after_cancel(job)
            except Exception:
                pass
            self._jobs.discard(job)

    def tween(
        self,
        duration_ms: int,
        on_update: Callable[[float], None],
        on_done: Callable[[], None] | None = None,
        *,
        fps: int = 60,
        easing: str = "out_cubic",
    ) -> None:
        duration_ms = max(1, int(duration_ms))
        step_ms = max(10, int(1000 / max(1, int(fps))))
        ease = _EASING.get(easing, _ease_out_cubic)
        start = time.perf_counter()

        def tick():
            now = time.perf_counter()
            t = (now - start) * 1000.0 / duration_ms
            t = max(0.0, min(1.0, t))
            try:
                on_update(ease(t))
            except Exception:
                # UI errors should not crash the app loop.
                pass

            if t >= 1.0:
                if on_done:
                    try:
                        on_done()
                    except Exception:
                        pass
                return

            job = self._w.after(step_ms, tick)
            self._jobs.add(job)

        job0 = self._w.after(0, tick)
        self._jobs.add(job0)

    def run_sequence(
        self,
        steps: list[Callable[[Callable[[], None]], None]],
        on_done: Callable[[], None] | None = None,
    ) -> None:
        steps = list(steps)

        def run_next(i: int) -> None:
            if i >= len(steps):
                if on_done:
                    on_done()
                return

            def done():
                run_next(i + 1)

            steps[i](done)

        run_next(0)
