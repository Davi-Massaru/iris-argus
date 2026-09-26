from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


CANONICALIZATION_VERSION = "agentic-json-v1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def action_hash(envelope: dict[str, Any]) -> str:
    material = {**envelope, "canonicalization_version": CANONICALIZATION_VERSION}
    return hashlib.sha256(canonical_json(material)).hexdigest()


@dataclass(frozen=True)
class ProposalDecision:
    proposal_id: str
    revision: int
    action_hash: str
    actor: str
    decision: str
    decided_at: str
    reason: str

    @classmethod
    def create(cls, *, proposal_id: str, revision: int, expected_hash: str, actor: str, decision: str, reason: str = ""):
        if decision not in {"APPROVED", "REJECTED"}:
            raise ValueError("Unsupported decision")
        return cls(
            proposal_id=proposal_id,
            revision=revision,
            action_hash=expected_hash,
            actor=actor,
            decision=decision,
            decided_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
        )
