"""Input monitoring utilities: typing speed, typing errors, mouse entropy, input idle time.

This module uses pynput to monitor keyboard and mouse events. It's optional and
designed to fail gracefully if pynput is not installed. All monitoring is local-only.
"""
from typing import Dict, Tuple
import time
import threading
import math

try:
    from pynput import keyboard, mouse
    _HAVE_PYNPUT = True
except Exception:
    _HAVE_PYNPUT = False


class InputMonitor:
    def __init__(self):
        self._running = False
        self._kb_listener = None
        self._mouse_listener = None

        # Typing metrics
        self._keypress_times = []  # timestamps of keypresses
        self._backspace_count = 0
        self._char_count = 0

        # Mouse metrics (movement entropy)
        self._mouse_moves = []  # list of (timestamp, x, y)

        # Idle
        self._last_input_time = time.time()

        # Thread lock
        import threading
        self._lock = threading.Lock()

    def start(self):
        if not _HAVE_PYNPUT:
            return False
        if self._running:
            return True
        self._running = True

        def on_press(key):
            with self._lock:
                t = time.time()
                self._keypress_times.append(t)
                self._char_count += 1
                self._last_input_time = t
                try:
                    if key == keyboard.Key.backspace:
                        self._backspace_count += 1
                except Exception:
                    pass

        def on_move(x, y):
            with self._lock:
                t = time.time()
                self._mouse_moves.append((t, x, y))
                # Keep last 60s
                self._mouse_moves = [(tt, xx, yy) for tt, xx, yy in self._mouse_moves if t - tt < 60.0]
                self._last_input_time = t

        self._kb_listener = keyboard.Listener(on_press=on_press)
        self._mouse_listener = mouse.Listener(on_move=on_move)
        self._kb_listener.start()
        self._mouse_listener.start()
        return True

    def stop(self):
        if not _HAVE_PYNPUT:
            return
        if self._kb_listener:
            self._kb_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
        self._running = False

    def get_metrics(self) -> Dict[str, float]:
        """Return current metrics: typing_speed (chars/min), typing_errors (backspaces/min),
        mouse_entropy (0-1), idle_seconds."""
        with self._lock:
            now = time.time()
            # typing speed: count keypresses in last 60s
            window = 60.0
            recent_keys = [t for t in self._keypress_times if now - t < window]
            typing_speed = (len(recent_keys) / window) * 60.0  # chars per minute

            recent_backspaces = [t for t in [t for t in self._keypress_times if now - t < window] if True]
            # backspace count is global, so approximate rate
            typing_errors = (self._backspace_count / max(1.0, max(1.0, len(self._keypress_times)))) * typing_speed

            # mouse movement entropy: compute directional changes histogram
            entropy = 0.0
            moves = [(x, y) for t, x, y in self._mouse_moves]
            if len(moves) >= 5:
                # compute movement vectors and bucket angles
                vecs = []
                for i in range(1, len(moves)):
                    dx = moves[i][0] - moves[i-1][0]
                    dy = moves[i][1] - moves[i-1][1]
                    ang = math.atan2(dy, dx)
                    vecs.append(ang)
                # histogram into 8 bins
                bins = [0]*8
                for a in vecs:
                    idx = int(((a + math.pi) / (2*math.pi)) * 8) % 8
                    bins[idx] += 1
                total = sum(bins)
                probs = [b/total for b in bins if total>0]
                import math as _math
                entropy = -sum([p * _math.log(p+1e-9) for p in probs]) / _math.log(8)

            idle_seconds = now - self._last_input_time

            return {
                'typing_speed_cpm': typing_speed,
                'typing_errors_rate': typing_errors,
                'mouse_entropy': entropy,
                'idle_seconds': idle_seconds
            }


if __name__ == '__main__':
    print('InputMonitor module loaded. pynput available:', _HAVE_PYNPUT)