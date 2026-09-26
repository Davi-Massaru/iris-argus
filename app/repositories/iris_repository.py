from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _sql(statement: str, params: tuple[Any, ...] = ()):
    import iris

    try:
        return iris.sql.exec(statement, *params)
    except Exception as error:
        if getattr(error, "sqlcode", None) == 100:
            return []
        raise


def _rows(statement: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in _sql(statement, params)]


class IRISRepository:
    def health(self) -> dict[str, Any]:
        try:
            import iris
            from scripts.readiness import ready
            return {"ready": ready(), "database": "IRIS", "version": str(iris.system.Version.GetVersion())}
        except Exception as error:
            return {"ready": False, "database": "IRIS", "error": type(error).__name__}

    def overview(self) -> dict[str, Any]:
        counts = {}
        statements = {
            "active_agents": "SELECT COUNT(*) FROM Agentic.AI_AGENT WHERE Status = 'ACTIVE'",
            "current_runs": "SELECT COUNT(*) FROM Agentic.AI_RUN WHERE State IN ('QUEUED','RUNNING','WAITING_APPROVAL')",
            "pending_approvals": "SELECT COUNT(*) FROM Agentic.AI_ACTION_PROPOSAL WHERE State = 'PENDING_APPROVAL'",
            "open_alerts": "SELECT COUNT(*) FROM Agentic.AI_ALERT_EVENT WHERE Lifecycle IN ('OPEN','ACKNOWLEDGED')",
        }
        for name, statement in statements.items():
            result = _rows(statement)
            counts[name] = int(result[0][0]) if result else 0
        counts["monitoring_freshness"] = "Not configured"
        return counts

    def list_tools(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        rows = _rows(
            "SELECT TOP ? StableKey,Method,PathTemplate,Summary,Classification,Enabled,ContractHash "
            "FROM Agentic.AI_TOOL_VERSION WHERE ID NOT IN (SELECT TOP ? ID FROM Agentic.AI_TOOL_VERSION ORDER BY PathTemplate,Method) "
            "ORDER BY PathTemplate,Method",
            (limit, offset),
        ) if offset else _rows(
            "SELECT TOP ? StableKey,Method,PathTemplate,Summary,Classification,Enabled,ContractHash "
            "FROM Agentic.AI_TOOL_VERSION ORDER BY PathTemplate,Method",
            (limit,),
        )
        return [
            {"stable_key": row[0], "method": row[1], "path": row[2], "summary": row[3], "classification": row[4], "enabled": bool(row[5]), "contract_hash": row[6]}
            for row in rows
        ]

    def list_proposals(self, *, limit: int) -> list[dict[str, Any]]:
        rows = _rows(
            "SELECT TOP ? ID,Revision,ActionHash,TargetInstanceID,Environment,Namespace,Method,ResolvedPath,Risk,State,CreatedAt,ExpiresAt "
            "FROM Agentic.AI_ACTION_PROPOSAL ORDER BY CreatedAt DESC",
            (limit,),
        )
        keys = ("id", "revision", "action_hash", "target_instance_id", "environment", "namespace", "method", "resolved_path", "risk", "state", "created_at", "expires_at")
        return [dict(zip(keys, row)) for row in rows]

    def decide_proposal(self, **decision):
        found = _rows(
            "SELECT State FROM Agentic.AI_ACTION_PROPOSAL WHERE ID = ? AND Revision = ? AND ActionHash = ?",
            (decision["proposal_id"], decision["revision"], decision["action_hash"]),
        )
        if not found or found[0][0] != "PENDING_APPROVAL":
            return None
        decided_at = datetime.now(timezone.utc).isoformat()
        _sql(
            "INSERT INTO Agentic.AI_APPROVAL (ID,ProposalID,ProposalRevision,ActionHash,Actor,Decision,DecidedAt,Reason) VALUES (?,?,?,?,?,?,?,?)",
            (f"{decision['proposal_id']}:{decision['revision']}:{decision['decision']}", decision["proposal_id"], decision["revision"], decision["action_hash"], decision["actor"], decision["decision"], decided_at, decision["reason"]),
        )
        state = "APPROVED" if decision["decision"] == "APPROVED" else "REJECTED"
        _sql(
            "UPDATE Agentic.AI_ACTION_PROPOSAL SET State = ? WHERE ID = ? AND Revision = ? AND ActionHash = ? AND State = 'PENDING_APPROVAL'",
            (state, decision["proposal_id"], decision["revision"], decision["action_hash"]),
        )
        return {"proposal_id": decision["proposal_id"], "revision": decision["revision"], "state": state, "decided_at": decided_at}


class MemoryRepository:
    """Test-only repository. Runtime persistence always uses IRISRepository."""

    def __init__(self):
        self.tools: list[dict[str, Any]] = []
        self.proposals: list[dict[str, Any]] = []

    def health(self):
        return {"ready": True, "database": "test-memory"}

    def overview(self):
        return {"active_agents": 0, "current_runs": 0, "pending_approvals": len(self.proposals), "open_alerts": 0, "monitoring_freshness": "Not configured"}

    def list_tools(self, *, limit, offset):
        return self.tools[offset : offset + limit]

    def list_proposals(self, *, limit):
        return self.proposals[:limit]

    def decide_proposal(self, **decision):
        for proposal in self.proposals:
            if proposal["id"] == decision["proposal_id"] and proposal["revision"] == decision["revision"] and proposal["action_hash"] == decision["action_hash"] and proposal["state"] == "PENDING_APPROVAL":
                proposal["state"] = "APPROVED" if decision["decision"] == "APPROVED" else "REJECTED"
                return proposal
        return None
