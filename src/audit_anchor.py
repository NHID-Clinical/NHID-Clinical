"""An audit anchor kept outside the database it describes.

Why this exists
---------------
`AuditStore.verify_chain` catches a deletion from the end of a session only by
comparing against `audit_sessions.event_count`. That counter lives in the same
SQLite file as the events, so anyone who can write the file can delete the last
events *and* lower the counter, and the trail verifies clean. Two coordinated
edits in one file.

`FileAuditAnchor` moves the witness out of that file. After every write the
store appends a checkpoint here (the session's event count plus the id and
evidence hash of the event just written). Each checkpoint is HMAC-signed with a
key the database does not hold, and chained to the checkpoint before it.
`verify_chain` then checks the database against the latest checkpoint:

* fewer events readable than anchored: events were removed;
* more events readable than anchored: events were added that the anchor never
  saw (or a tail of this file was cut off, which reads the same way);
* the anchored head event missing or with a different evidence hash: the
  trail was rewritten.

What it raises and what it does not
-----------------------------------
Tampering now needs write access to **two places** and the **anchor key**, not
two rows in one file. That is the whole claim. It is still not a guarantee:

* An attacker who can rewrite this file *and* holds the anchor key can forge
  checkpoints. Keep `AUDIT_ANCHOR_KEY_B64` out of reach of whatever can write
  the database.
* Cutting checkpoints off the end of this file is only detected while the
  database still holds the events they covered. Truncating both, consistently,
  is not detected here. Putting this file on append-only storage (``chattr +a``,
  S3 Object Lock, a WORM volume) is what closes that, and is the deployment's
  job; ``head()`` returns a digest an operator can copy somewhere else on a
  schedule to witness the file itself.
* One writer process per anchor file. The lock here is per process.

Format: one JSON object per line, in order, ``seq`` starting at 1. ``prev`` is
the SHA-256 of the previous line's text (empty for the first); ``mac`` is
HMAC-SHA256 over every other field.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

#: The anchor file failed its own check: a line was edited, removed from the
#: middle, reordered, or signed with another key.
ERR_AUDIT_ANCHOR_INVALID = "ERR_AUDIT_ANCHOR_INVALID"

KIND_APPEND = "append"
KIND_PRUNE = "prune"


class AnchorInvalid(Exception):
    """The anchor file cannot be trusted, so nothing it says is used."""


def _canonical(fields: dict) -> bytes:
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FileAuditAnchor:
    """Append-only, signed, hash-chained checkpoints in a file of their own."""

    def __init__(self, path: str, key: bytes):
        if len(key) != 32:
            raise ValueError(f"anchor key must be 32 bytes, got {len(key)}")
        self.path = path
        self._key = key
        self._lock = threading.Lock()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    # ── reading ──────────────────────────────────────────────────────────

    def _verified_lines(self):
        """Every checkpoint, checked in order. Raises AnchorInvalid on any break."""
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw_lines = fh.read().splitlines()
        except FileNotFoundError:
            return [], ""
        except OSError as exc:
            raise AnchorInvalid(f"{ERR_AUDIT_ANCHOR_INVALID}: cannot read {self.path}: {exc}") from exc

        records, prev_hash = [], ""
        for n, line in enumerate(raw_lines, start=1):
            try:
                rec = json.loads(line)
                mac = rec.pop("mac")
            except (ValueError, KeyError, AttributeError) as exc:
                raise AnchorInvalid(f"{ERR_AUDIT_ANCHOR_INVALID}: line {n} is not a checkpoint") from exc
            expected = hmac.new(self._key, _canonical(rec), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, str(mac)):
                raise AnchorInvalid(f"{ERR_AUDIT_ANCHOR_INVALID}: line {n} signature does not verify")
            if rec.get("seq") != n:
                raise AnchorInvalid(f"{ERR_AUDIT_ANCHOR_INVALID}: line {n} has seq {rec.get('seq')!r}")
            if rec.get("prev") != prev_hash:
                raise AnchorInvalid(f"{ERR_AUDIT_ANCHOR_INVALID}: line {n} does not chain to line {n - 1}")
            records.append(rec)
            prev_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()
        return records, prev_hash

    def latest(self, session_id: str) -> Optional[dict]:
        """The most recent checkpoint for a session, or None if it was never anchored."""
        records, _ = self._verified_lines()
        found = None
        for rec in records:
            if rec["session_id"] == session_id:
                found = rec
        return found

    def head(self) -> Dict[str, object]:
        """``{"seq", "line_hash"}`` of the last checkpoint, for out-of-band witnessing."""
        records, line_hash = self._verified_lines()
        return {"seq": len(records), "line_hash": line_hash}

    def verify(self) -> tuple[bool, Optional[str]]:
        try:
            self._verified_lines()
        except AnchorInvalid as exc:
            return False, str(exc)
        return True, None

    # ── writing ──────────────────────────────────────────────────────────

    def record(
        self,
        session_id: str,
        event_count: int,
        head_event_id: Optional[str],
        head_evidence_hash: Optional[str],
        kind: str = KIND_APPEND,
    ) -> dict:
        """Append one checkpoint and fsync it. Raises on any failure."""
        with self._lock:
            records, prev_hash = self._verified_lines()
            rec = {
                "seq": len(records) + 1,
                "prev": prev_hash,
                "kind": kind,
                "session_id": session_id,
                "event_count": int(event_count),
                "head_event_id": head_event_id,
                "head_evidence_hash": head_evidence_hash,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            rec["mac"] = hmac.new(self._key, _canonical(rec), hashlib.sha256).hexdigest()
            line = json.dumps(rec, sort_keys=True, separators=(",", ":"))
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            return rec
