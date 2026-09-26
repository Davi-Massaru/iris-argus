import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from app.repositories.iris_repository import _rows, _sql
from app.mvp.catalog import tool_by_key


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def transaction():
    _sql('START TRANSACTION')
    try:
        yield
        _sql('COMMIT')
    except BaseException:
        _sql('ROLLBACK')
        raise


class Conflict(ValueError):
    pass


class AgentRepository:
    def list_agents(self):
        rows = _rows('SELECT TOP 200 ID,ConfigJSON,Revision,ActiveRun,UpdatedAt FROM Agentic.MVP_AGENT ORDER BY Name,ID')
        return [dict(json.loads(r[1]), id=r[0], revision=r[2], active_run=r[3], updated_at=r[4]) for r in rows]

    def get_agent(self, identifier):
        rows = _rows('SELECT ConfigJSON,Revision,ActiveRun,UpdatedAt FROM Agentic.MVP_AGENT WHERE ID=?', (identifier,))
        if not rows:
            raise LookupError('Agent not found.')
        r = rows[0]
        config = json.loads(r[0])
        for binding in config.get('tools', []):
            if not binding.get('stable_key') and not binding.get('contract_hash'):
                item = tool_by_key(binding['key'])
                binding['stable_key'] = item['stable_key']
                binding['contract_hash'] = item['contract_hash']
        return dict(config, id=identifier, revision=r[1], active_run=r[2], updated_at=r[3])

    def save_agent(self, config, actor, identifier=None, revision=None):
        with transaction():
            if identifier:
                # Take a write lock before reading; edits and enqueue serialize on this row.
                _sql('UPDATE Agentic.MVP_AGENT SET Revision=Revision WHERE ID=?', (identifier,))
                old = self.get_agent(identifier)
                if type(revision) is not int or old['revision'] != revision:
                    raise Conflict('Agent changed. Reload before saving.')
                _sql('UPDATE Agentic.MVP_AGENT SET Name=?,ConfigJSON=?,Revision=Revision+1,Enabled=?,IntervalSeconds=?,NextDue=?,UpdatedBy=?,UpdatedAt=? WHERE ID=?',
                     (config['name'], json.dumps(config), int(config['enabled']), config['interval_seconds'], time.time() + config['interval_seconds'], actor, now(), identifier))
            else:
                identifier = str(uuid4())
                _sql('INSERT INTO Agentic.MVP_AGENT (ID,Name,ConfigJSON,Revision,Enabled,IntervalSeconds,NextDue,UpdatedBy,UpdatedAt) VALUES (?,?,?,?,?,?,?,?,?)',
                     (identifier, config['name'], json.dumps(config), 1, int(config['enabled']), config['interval_seconds'], time.time() + config['interval_seconds'], actor, now()))
        return self.get_agent(identifier)

    def enqueue(self, identifier, actor, trigger='MANUAL'):
        with transaction():
            _sql('UPDATE Agentic.MVP_AGENT SET Revision=Revision WHERE ID=?', (identifier,))
            agent = self.get_agent(identifier)
            if not agent['enabled']:
                raise Conflict('Agent is paused.')
            if agent['active_run']:
                raise Conflict('A run is already pending for this agent.')
            if trigger == 'SCHEDULE':
                due = _rows('SELECT NextDue,IntervalSeconds FROM Agentic.MVP_AGENT WHERE ID=?', (identifier,))[0]
                if not due[1] or due[0] > time.time():
                    return None
            run_id = str(uuid4())
            _sql('INSERT INTO Agentic.MVP_RUN (ID,AgentID,SnapshotJSON,State,TriggerKind,Actor,CreatedAt) VALUES (?,?,?,?,?,?,?)',
                 (run_id, identifier, json.dumps(agent), 'QUEUED', trigger, actor, now()))
            _sql('UPDATE Agentic.MVP_AGENT SET ActiveRun=?,NextDue=? WHERE ID=?',
                 (run_id, time.time() + agent['interval_seconds'], identifier))
        return run_id

    def schedule(self):
        rows = _rows('SELECT TOP 20 ID FROM Agentic.MVP_AGENT WHERE Enabled=1 AND IntervalSeconds>0 AND NextDue<=? AND ActiveRun IS NULL ORDER BY NextDue', (time.time(),))
        for row in rows:
            try:
                self.enqueue(row[0], 'scheduler', 'SCHEDULE')
            except Conflict:
                pass

    def claim(self):
        with transaction():
            rows = _rows("SELECT TOP 1 ID,AgentID FROM Agentic.MVP_RUN WHERE State='QUEUED' ORDER BY CreatedAt")
            if not rows:
                return None
            identifier, agent_id = rows[0]
            _sql('UPDATE Agentic.MVP_AGENT SET Revision=Revision WHERE ID=?', (agent_id,))
            state = _rows('SELECT State FROM Agentic.MVP_RUN WHERE ID=?', (identifier,))[0][0]
            if state != 'QUEUED':
                return None
            agent = self.get_agent(agent_id)
            if not agent['enabled']:
                _sql("UPDATE Agentic.MVP_RUN SET State='CANCELLED',FinishedAt=? WHERE ID=?", (now(), identifier))
                _sql('UPDATE Agentic.MVP_AGENT SET ActiveRun=NULL WHERE ID=? AND ActiveRun=?', (agent_id, identifier))
                return None
            _sql("UPDATE Agentic.MVP_RUN SET State='RUNNING',StartedEpoch=? WHERE ID=?", (time.time(), identifier))
        return identifier

    def get_run(self, identifier):
        rows = _rows('SELECT AgentID,SnapshotJSON,State,TriggerKind,Actor,CreatedAt,FinishedAt,Report,ErrorCode FROM Agentic.MVP_RUN WHERE ID=?', (identifier,))
        if not rows:
            raise LookupError('Run not found.')
        r = rows[0]
        result = dict(zip(('agent_id','snapshot','state','trigger','actor','created_at','finished_at','report','error'), r))
        result.update(id=identifier, snapshot=json.loads(r[1]))
        result['calls'] = [dict(id=c[0], tool=c[1], arguments=json.loads(c[2]), result=json.loads(c[3]), outcome=c[4], created_at=c[5]) for c in _rows('SELECT ID,ToolKey,ArgumentsJSON,ResultJSON,Outcome,CreatedAt FROM Agentic.MVP_CALL WHERE RunID=? ORDER BY CreatedAt,ID', (identifier,))]
        return result

    def list_runs(self):
        return [dict(zip(('id','agent_id','state','created_at','finished_at','error','agent_name'), r)) for r in _rows('SELECT TOP 100 r.ID,r.AgentID,r.State,r.CreatedAt,r.FinishedAt,r.ErrorCode,a.Name FROM Agentic.MVP_RUN r JOIN Agentic.MVP_AGENT a ON a.ID=r.AgentID ORDER BY r.CreatedAt DESC')]

    def record_call(self, run_id, key, arguments, result, outcome):
        identifier = str(uuid4())
        _sql('INSERT INTO Agentic.MVP_CALL (ID,RunID,ToolKey,ArgumentsJSON,ResultJSON,Outcome,CreatedAt) VALUES (?,?,?,?,?,?,?)',
             (identifier, run_id, key, json.dumps(arguments), json.dumps(result), outcome, now()))
        return identifier

    def finish(self, identifier, state, report='', error=None):
        with transaction():
            run = self.get_run(identifier)
            _sql('UPDATE Agentic.MVP_AGENT SET Revision=Revision WHERE ID=?', (run['agent_id'],))
            _sql("UPDATE Agentic.MVP_RUN SET State=?,Report=?,ErrorCode=?,FinishedAt=? WHERE ID=? AND State='RUNNING'", (state, report[:30000], error, now(), identifier))
            _sql('UPDATE Agentic.MVP_AGENT SET ActiveRun=NULL WHERE ID=? AND ActiveRun=?', (run['agent_id'], identifier))

    def recover(self):
        # One scheduler per deployment. Runs are never replayed after a crash.
        for row in _rows("SELECT ID FROM Agentic.MVP_RUN WHERE State='RUNNING'"):
            self.finish(row[0], 'FAILED', error='WORKER_RESTARTED')
