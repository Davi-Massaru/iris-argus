"""Create only temporary test data. Run from container with explicit test credentials."""
import json
import os
import time
from pathlib import Path
import requests

base = 'http://127.0.0.1:52773/agentic'
session = requests.Session()
session.auth = (os.environ['AGENTIC_SMOKE_USER'], os.environ['AGENTIC_SMOKE_PASSWORD'])


def call(method, path, payload=None, status=200):
    r = session.request(method, base + path, json=payload, timeout=20)
    assert r.status_code == status, (path, r.status_code, r.text[:300])
    return r.json()


token = call('GET', '/api/v1/session')['csrf_token']
session.headers['X-Agentic-CSRF'] = token
locks_tool = next(tool for tool in call('GET', '/api/mvp/catalog')['items'] if tool['key'] == 'get_v2_locks')
fixture_path = Path('/usr/irissys/mgr/agentic/mvp-smoke.json')
fixture = {'tool_availability': [{
    'stable_key': locks_tool['stable_key'],
    'contract_hash': locks_tool['contract_hash'],
    'available': locks_tool['available'],
}]}
fixture_path.write_text(json.dumps(fixture))
if not locks_tool['available']:
    call('PUT', f"/api/mvp/catalog/{locks_tool['stable_key']}/availability", {
        'enabled': True,
        'acknowledge_sensitive_data': locks_tool['sensitive'],
        'reason': 'Enabled by the authenticated smoke-test DBA.',
    })
config = dict(name='__MVP_SMOKE__', prompt='You are a DBA. Use the tools and report only observed evidence.',
              task='Query get_v2_locks and report how many rows were returned. Keep the report brief and in English.',
              model=os.environ.get('AGENTIC_MODEL', 'qwen2.5:3b'), provider=os.environ.get('AGENTIC_PROVIDER', 'ollama'), enabled=True, interval_seconds=0,
              tools=[{'key':'get_v2_locks', 'fixed':{'maxRows':100}}])
agent = call('POST', '/api/mvp/agents', config, 201)
fixture['agent_id'] = agent['id']
fixture_path.write_text(json.dumps(fixture))
agent = call('PUT', '/api/mvp/agents/' + agent['id'], {**agent, 'prompt': config['prompt'] + ' Cite evidence.'})
call('PUT', '/api/mvp/agents/' + agent['id'], {**agent, 'revision':1}, 409)
run = call('POST', '/api/mvp/agents/' + agent['id'] + '/runs', {}, 202)
call('POST', '/api/mvp/agents/' + agent['id'] + '/runs', {}, 409)
print('MVP_CREATED_ENQUEUED', run['id'], flush=True)
for attempt in range(130):
    result = call('GET', '/api/mvp/runs/' + run['id'])
    if result['state'] not in ('QUEUED', 'RUNNING'):
        break
    time.sleep(2)
print('MVP_RUN_RESULT', result['state'], result['error'], [(c['tool'], c['outcome']) for c in result['calls']], flush=True)
assert result['state'] == 'SUCCEEDED', result['error']
assert result['report'] and any(c['tool']=='get_v2_locks' and c['outcome']=='SUCCEEDED' for c in result['calls'])
paused = call('PUT', '/api/mvp/agents/' + agent['id'], {**agent, 'enabled':False})
call('POST', '/api/mvp/agents/' + agent['id'] + '/runs', {}, 409)
fixture['run_id'] = run['id']
fixture_path.write_text(json.dumps(fixture))
print('MVP_HTTP_OK create, edit, revision conflict, queue dedup, provider, SysAdmin, report, pause', flush=True)
