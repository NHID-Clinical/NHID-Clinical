"""Verifier challenges for the pre-utterance gate: the payer side of proof of possession.

A passport is a static artifact: whoever captured its bytes can present it. The
gate therefore issues a fresh, unpredictable nonce for each call
(`POST /v1/gate/challenge`), and the agent must sign that nonce with the key its
delegation names (`src.agent_identity.PresentationProof`). The engine checks the
answer inside DLG-01 (`DelegationContext.require_possession_proof`).

The nonce is issued by the verifier and held here, never taken from the caller,
because a caller-chosen nonce proves nothing about freshness.

One challenge serves one call (keyed by its call id) until it expires, so the
agent does not need a round trip before every utterance. A new challenge for the
same call replaces the old one.

Reference scope: an in-process store with a time-to-live. Instances behind a
load balancer would each hold their own challenges, so a deployment that scales
out needs a shared store (the same requirement `src/call_verification.py`
documents for its token store).
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Optional, Tuple

from src.agent_identity import new_verifier_nonce

#: How long a call's challenge stays valid. Longer than a typical eligibility
#: call; a call that outlives it asks for a new one.
CHALLENGE_TTL_SECONDS = 15 * 60
#: Bound on outstanding challenges, so the store cannot be grown without limit.
MAX_OUTSTANDING = 10_000


class ChallengeStore:
    def __init__(self, ttl_seconds: int = CHALLENGE_TTL_SECONDS,
                 clock: Callable[[], float] = time.time) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._items: Dict[str, Tuple[str, float]] = {}

    def issue(self, call_id: str) -> Tuple[str, int]:
        """A new challenge for `call_id`, and when it expires (unix seconds)."""
        now = self._clock()
        with self._lock:
            self._expire(now)
            if len(self._items) >= MAX_OUTSTANDING and call_id not in self._items:
                raise OverflowError("too many outstanding gate challenges")
            nonce = new_verifier_nonce()
            expires = now + self._ttl
            self._items[call_id] = (nonce, expires)
        return nonce, int(expires)

    def current(self, call_id: str) -> Optional[str]:
        """The live challenge for `call_id`, or None if none was issued or it expired."""
        now = self._clock()
        with self._lock:
            item = self._items.get(call_id)
            if item is None or item[1] <= now:
                self._items.pop(call_id, None)
                return None
            return item[0]

    def _expire(self, now: float) -> None:
        for key in [k for k, (_, exp) in self._items.items() if exp <= now]:
            del self._items[key]


#: The gate's store. Module-level so the Lambda route and in-process callers share it.
CHALLENGES = ChallengeStore()
