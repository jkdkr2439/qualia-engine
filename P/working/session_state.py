"""P/working/session_state.py — Session tracking: mode, Gamma_acc, spin_count, session_id."""
from __future__ import annotations
import uuid
import time


class SessionState:
    """
    Tracks within-session metrics. Resets each time Pete starts.
    Gamma_acc: accumulated chaos — triggers dream cycle if > theta_Gamma=3.0
    """
    THETA_GAMMA = 3.0     # trigger dream after this much accumulated chaos

    def __init__(self):
        self.session_id:  str   = str(uuid.uuid4())[:8]
        self.start_time:  float = time.time()
        self.mode:        str   = "NORMAL"    # current processing mode
        self.Gamma_acc:   float = 0.0         # accumulated noise/chaos
        self.spin_count:  int   = 0           # total spins this session
        self.tick_count:  int   = 0
        self.mode_history: list[str] = []

    def tick(self, mode: str, odfs_S: float) -> bool:
        """
        Update session state per tick.
        Returns True if dream cycle should trigger (Gamma_acc > theta).
        """
        self.tick_count += 1
        self.spin_count += 1
        self.mode = mode
        self.mode_history.append(mode)
        if len(self.mode_history) > 100:
            self.mode_history = self.mode_history[-100:]

        # Gamma accumulates when S_combined low (chaos/confusion)
        if odfs_S < 0.3:
            self.Gamma_acc += 0.05
        elif odfs_S > 0.6:
            self.Gamma_acc = max(0.0, self.Gamma_acc - 0.02)

        return self.Gamma_acc >= self.THETA_GAMMA

    def dream_triggered(self) -> None:
        """Reset Gamma_acc after dream cycle runs."""
        self.Gamma_acc = 0.0

    def elapsed_secs(self) -> float:
        return time.time() - self.start_time

    def to_dict(self) -> dict:
        return {
            "session_id":  self.session_id,
            "mode":        self.mode,
            "Gamma_acc":   round(self.Gamma_acc, 4),
            "spin_count":  self.spin_count,
            "tick_count":  self.tick_count,
            "elapsed_s":   round(self.elapsed_secs(), 1),
            "dream_ready": self.Gamma_acc >= self.THETA_GAMMA,
        }
