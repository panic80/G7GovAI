"""
Adaptive Rate Limiter for Gemini API calls.

Automatically adjusts concurrency and delay based on API response:
- Backs off on rate limit errors (429)
- Gradually ramps back up after successful requests
"""

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that backs off on 429s and ramps up on success.

    Strategy:
    - Start at max_concurrent with no delay
    - On 429: cut concurrency by 50%, add exponential delay
    - On success streak: gradually increase concurrency, decrease delay
    """

    max_concurrent: int = 20
    min_concurrent: int = 2
    initial_delay: float = 0.0
    max_delay: float = 30.0

    # Tuning parameters
    backoff_factor: float = 0.5  # Cut to 50% on rate limit
    recovery_factor: float = 1.2  # Increase by 20% on success streak
    success_streak_threshold: int = 5  # Successes before ramping up

    # Internal state (initialized in __post_init__)
    _current_concurrent: int = field(init=False, repr=False)
    _current_delay: float = field(init=False, repr=False)
    _semaphore: threading.Semaphore = field(init=False, repr=False)
    _lock: threading.Lock = field(init=False, repr=False)
    _success_streak: int = field(init=False, repr=False)
    _total_requests: int = field(init=False, repr=False)
    _total_rate_limits: int = field(init=False, repr=False)

    def __post_init__(self):
        self._current_concurrent = self.max_concurrent
        self._current_delay = self.initial_delay
        self._semaphore = threading.Semaphore(self._current_concurrent)
        self._lock = threading.Lock()
        self._success_streak = 0
        self._total_requests = 0
        self._total_rate_limits = 0

    def acquire(self):
        """Acquire a slot, blocking if at capacity."""
        self._semaphore.acquire()
        if self._current_delay > 0:
            time.sleep(self._current_delay)

    def release(self, success: bool = True, was_rate_limited: bool = False):
        """Release slot and adjust limits based on outcome."""
        with self._lock:
            self._total_requests += 1
            if was_rate_limited:
                self._total_rate_limits += 1
                self._handle_rate_limit()
            elif success:
                self._handle_success()
        self._semaphore.release()

    def _handle_rate_limit(self):
        """Back off: reduce concurrency, increase delay."""
        self._success_streak = 0
        old_concurrent = self._current_concurrent

        # Reduce concurrency by backoff_factor
        new_concurrent = max(
            self.min_concurrent, int(self._current_concurrent * self.backoff_factor)
        )

        # Increase delay exponentially
        if self._current_delay > 0:
            new_delay = min(self.max_delay, self._current_delay * 2)
        else:
            new_delay = 1.0

        self._current_delay = new_delay

        # Adjust semaphore (reduce available slots)
        slots_to_remove = old_concurrent - new_concurrent
        removed = 0
        for _ in range(slots_to_remove):
            # Try to acquire without blocking - only removes if slot is available
            if self._semaphore.acquire(blocking=False):
                removed += 1

        self._current_concurrent = new_concurrent

        logger.warning(
            f"Rate limited! Reducing concurrency: {old_concurrent} -> {self._current_concurrent}, "
            f"delay: {self._current_delay:.1f}s (removed {removed} slots)"
        )

    def _handle_success(self):
        """On success streak, gradually ramp back up."""
        self._success_streak += 1

        if self._success_streak >= self.success_streak_threshold:
            self._success_streak = 0

            # Increase concurrency if below max
            if self._current_concurrent < self.max_concurrent:
                old_concurrent = self._current_concurrent
                new_concurrent = min(
                    self.max_concurrent,
                    int(self._current_concurrent * self.recovery_factor),
                )
                # Ensure we increase by at least 1
                if new_concurrent == old_concurrent:
                    new_concurrent = min(self.max_concurrent, old_concurrent + 1)

                slots_to_add = new_concurrent - self._current_concurrent
                self._current_concurrent = new_concurrent

                # Add slots to semaphore
                for _ in range(slots_to_add):
                    self._semaphore.release()

                logger.info(
                    f"Ramping up concurrency: {old_concurrent} -> {self._current_concurrent}"
                )

            # Decrease delay
            if self._current_delay > 0:
                old_delay = self._current_delay
                self._current_delay = self._current_delay * 0.5
                if self._current_delay < 0.1:
                    self._current_delay = 0

                if old_delay != self._current_delay:
                    logger.info(f"Reduced delay: {old_delay:.1f}s -> {self._current_delay:.1f}s")

    def reset(self):
        """Reset limiter to initial state."""
        with self._lock:
            # Release all held semaphore slots
            slots_to_release = self.max_concurrent - self._current_concurrent
            for _ in range(slots_to_release):
                self._semaphore.release()

            self._current_concurrent = self.max_concurrent
            self._current_delay = self.initial_delay
            self._success_streak = 0
            logger.info("Rate limiter reset to initial state")

    @property
    def stats(self) -> dict:
        """Current limiter stats for logging/monitoring."""
        return {
            "current_concurrent": self._current_concurrent,
            "max_concurrent": self.max_concurrent,
            "current_delay_s": self._current_delay,
            "success_streak": self._success_streak,
            "total_requests": self._total_requests,
            "total_rate_limits": self._total_rate_limits,
            "rate_limit_pct": (
                round(self._total_rate_limits / self._total_requests * 100, 1)
                if self._total_requests > 0
                else 0
            ),
        }

    def __str__(self) -> str:
        return (
            f"AdaptiveRateLimiter(concurrent={self._current_concurrent}/{self.max_concurrent}, "
            f"delay={self._current_delay:.1f}s, streak={self._success_streak})"
        )


# Global instance for Gemini API calls
# Import and use: from core.adaptive_rate_limiter import gemini_limiter
gemini_limiter = AdaptiveRateLimiter(max_concurrent=100, min_concurrent=5)
