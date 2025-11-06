"""
Lightweight tracker for sampling localized entity values (names/organizations)
with reuse control within a generation run.
"""

from __future__ import annotations

import random
from collections import deque, Counter
from typing import Deque, Dict, Iterable, List, Optional, Tuple


class UsedEntityTracker:
    """Tracks recently used entities to limit repetition within a window.

    This class is intentionally lightweight and in-memory; it resets each run.
    """

    def __init__(self, window_size: int = 200):
        self.window_size: int = window_size
        self._recent: Deque[str] = deque(maxlen=window_size)
        self._global_counts: Counter = Counter()

    def note(self, value: str) -> None:
        self._recent.append(value)
        self._global_counts[value] += 1

    def recent_contains(self, value: str) -> bool:
        return value in self._recent

    def frequency(self, value: str) -> int:
        return self._global_counts[value]

    def sample_unique(self, candidates: Iterable[str], k: int = 1) -> List[str]:
        """Sample up to k values preferring ones not in the recent window.

        If unique values are insufficient, fill from remaining candidates.
        """
        pool = list(dict.fromkeys(candidates))  # preserve order, dedupe
        random.shuffle(pool)
        preferred = [v for v in pool if v and not self.recent_contains(v)]
        pick = preferred[:k]
        if len(pick) < k:
            # fill from the rest, still avoiding duplicates in pick
            rest = [v for v in pool if v not in pick]
            pick += rest[: (k - len(pick))]
        for v in pick:
            self.note(v)
        return pick


def sample_names_from_placeholders(
    placeholder_mappings: Dict[str, Dict],
    tracker: UsedEntityTracker,
    count: int = 2,
) -> List[str]:
    """Build a combined name pool from multiple placeholder buckets and sample.

    Buckets considered (if present):
    - <caller_name>, <callee_name>
    - <malay_male_name>, <malay_female_name>
    - <chinese_malay_name>, <indian_malay_name>
    """
    name_keys = [
        "<caller_name>",
        "<callee_name>",
        "<malay_male_name>",
        "<malay_female_name>",
        "<chinese_malay_name>",
        "<indian_malay_name>",
    ]
    pool: List[str] = []
    for key in name_keys:
        if key in placeholder_mappings:
            pool.extend(placeholder_mappings[key].get("substitutions", []))
    return tracker.sample_unique(pool, k=count)


