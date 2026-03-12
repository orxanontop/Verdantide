from __future__ import annotations

"""animation_system.py

UI animation utilities.

For now this module re-exports the existing AnimationController and acts as the
expansion point for higher-level combat animation sequences (camera focus,
particles, etc.).

The combat engine never imports this module.
"""

from animation_controller import AnimationController