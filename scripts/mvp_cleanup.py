"""Remove only agents identified by test fixture files or exact UI test identity."""

import json
from pathlib import Path
import iris
from app.mvp.repository import AgentRepository, transaction
from app.repositories.iris_repository import IRISRepository, _rows, _sql

iris.system.Process.SetNamespace("AGENTIC")
ids = []
availability_restores = []
fixture_paths = []
for filename in ("mvp-smoke.json", "mvp-locks-test.json"):
    path = Path("/usr/irissys/mgr/agentic") / filename
    if path.exists():
        fixture = json.loads(path.read_text())
        if fixture.get("agent_id"):
            ids.append(fixture["agent_id"])
        availability_restores.extend(fixture.get("tool_availability", []))
        fixture_paths.append(path)
# The browser test creates this exact disposable record with the deployment identity.
for name in ("__MVP_UI_TEST__", "__MVP_SMOKE__", "__MVP_LOCKS_ACCEPTANCE__"):
    ids.extend(
        r[0]
        for r in _rows(
            "SELECT ID FROM Agentic.MVP_AGENT WHERE Name=? AND UpdatedBy=?", (name, "_SYSTEM")
        )
    )
for identifier in set(ids):
    if not _rows("SELECT ID FROM Agentic.MVP_AGENT WHERE ID=?", (identifier,)):
        continue
    with transaction():
        agent = AgentRepository().get_agent(identifier)
        assert agent["name"] in {"__MVP_SMOKE__", "__MVP_UI_TEST__", "__MVP_LOCKS_ACCEPTANCE__"}
        assert not agent["active_run"], "Refuse to delete an active test run"
        _sql(
            "DELETE FROM Agentic.MVP_CALL WHERE RunID IN (SELECT ID FROM Agentic.MVP_RUN WHERE AgentID=?)",
            (identifier,),
        )
        _sql("DELETE FROM Agentic.MVP_RUN WHERE AgentID=?", (identifier,))
        _sql("DELETE FROM Agentic.MVP_AGENT WHERE ID=?", (identifier,))
registry = IRISRepository()
for tool in availability_restores:
    try:
        registry.set_tool_availability(
            stable_key=tool["stable_key"],
            contract_hash=tool["contract_hash"],
            enabled=tool["available"],
            actor="mvp-cleanup",
            reason="Restore tool availability after the disposable acceptance test.",
        )
    except LookupError:
        print(
            "MVP_TOOL_RESTORE_SKIPPED", tool["stable_key"], "contract version no longer installed"
        )
for path in fixture_paths:
    path.unlink(missing_ok=True)
print("MVP_TEST_DATA_REMOVED", len(ids))
