"""Remove only agents identified by test fixture files or exact UI test identity."""
import json
from pathlib import Path
import iris
from app.mvp.repository import AgentRepository, transaction
from app.repositories.iris_repository import _rows, _sql

iris.system.Process.SetNamespace('AGENTIC')
ids = []
for filename in ('mvp-smoke.json', 'mvp-locks-test.json'):
    path = Path('/usr/irissys/mgr/agentic') / filename
    if path.exists():
        ids.append(json.loads(path.read_text())['agent_id'])
# The browser test creates this exact disposable record with the deployment identity.
for name in ('__MVP_UI_TEST__', '__MVP_SMOKE__', '__MVP_LOCKS_ACCEPTANCE__'):
    ids.extend(r[0] for r in _rows('SELECT ID FROM Agentic.MVP_AGENT WHERE Name=? AND UpdatedBy=?', (name, '_SYSTEM')))
for identifier in set(ids):
    if not _rows('SELECT ID FROM Agentic.MVP_AGENT WHERE ID=?', (identifier,)):
        continue
    with transaction():
        agent = AgentRepository().get_agent(identifier)
        assert agent['name'] in {'__MVP_SMOKE__', '__MVP_UI_TEST__', '__MVP_LOCKS_ACCEPTANCE__'}
        assert not agent['active_run'], 'Refuse to delete an active test run'
        _sql('DELETE FROM Agentic.MVP_CALL WHERE RunID IN (SELECT ID FROM Agentic.MVP_RUN WHERE AgentID=?)', (identifier,))
        _sql('DELETE FROM Agentic.MVP_RUN WHERE AgentID=?', (identifier,))
        _sql('DELETE FROM Agentic.MVP_AGENT WHERE ID=?', (identifier,))
print('MVP_TEST_DATA_REMOVED', len(ids))
