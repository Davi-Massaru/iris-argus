"""Controlled 50-lock test in AGENTIC, never against existing application locks.

Execute through a trusted deployment IRIS session with smoke HTTP credentials.
Temporary agents/runs are tracked for explicit cleanup by mvp_cleanup.py.
"""
import json
import os
import time
from pathlib import Path
import requests
import iris

iris.system.Process.SetNamespace('AGENTIC')
session = requests.Session()
session.auth = (os.environ['AGENTIC_SMOKE_USER'], os.environ['AGENTIC_SMOKE_PASSWORD'])
base = 'http://127.0.0.1:52773/agentic'


def request(method, path, data=None, status=200):
    r = session.request(method, base + path, json=data, timeout=20)
    assert r.status_code == status, (r.status_code, r.text[:300])
    return r.json()


session.headers['X-Agentic-CSRF'] = request('GET', '/api/v1/session')['csrf_token']
catalog = request('GET', '/api/mvp/catalog')['items']
required_tools = [next(tool for tool in catalog if tool['key'] == key) for key in ('get_v2_locks', 'get_v2_process')]
fixture_path = Path('/usr/irissys/mgr/agentic/mvp-locks-test.json')
fixture = {'tool_availability': [{
    'stable_key': tool['stable_key'],
    'contract_hash': tool['contract_hash'],
    'available': tool['available'],
} for tool in required_tools]}
fixture_path.write_text(json.dumps(fixture))
agent = None
try:
    for tool in required_tools:
        if not tool['available']:
            request('PUT', f"/api/mvp/catalog/{tool['stable_key']}/availability", {
                'enabled': True,
                'acknowledge_sensitive_data': tool['sensitive'],
                'reason': 'Enabled by the authenticated 50-lock acceptance DBA.',
            })
    agent = request('POST', '/api/mvp/agents', dict(
        name='__MVP_LOCKS_ACCEPTANCE__', prompt='You are a DBA. Use tools to produce a concise, factual report in English.',
        task='Query get_v2_locks. If at least 50 rows are returned, query get_v2_process for each distinct observed PID (not once per lock) and report the findings. If fewer than 50 rows are returned, state that the condition was not met. Cite evidence IDs. Do not make changes.',
        model=os.environ.get('AGENTIC_MODEL', 'qwen2.5:3b'), provider=os.environ.get('AGENTIC_PROVIDER', 'ollama'), enabled=True, interval_seconds=0,
        tools=[{'key':'get_v2_locks','fixed':{'filter':'AgenticMVPTest','maxRows':100}},
               {'key':'get_v2_process','fixed':{}}]), status=201)
    fixture['agent_id'] = agent['id']
    fixture_path.write_text(json.dumps(fixture))
    iris.execute('for i=1:1:50 lock +^AgenticMVPTest(i):1')
    run = request('POST', '/api/mvp/agents/' + agent['id'] + '/runs', {}, 202)
    print('LOCKS_TEST_QUEUED', run['id'], flush=True)
    for _ in range(130):
        result = request('GET', '/api/mvp/runs/' + run['id'])
        if result['state'] not in ('QUEUED','RUNNING'):
            break
        time.sleep(2)
    assert result['state'] == 'SUCCEEDED', (result['state'], result['error'])
    locks = [c for c in result['calls'] if c['tool']=='get_v2_locks' and c['outcome']=='SUCCEEDED']
    processes = [c for c in result['calls'] if c['tool']=='get_v2_process' and c['outcome']=='SUCCEEDED']
    assert locks and len(locks[0]['result']['result']) == 50
    assert processes, 'Model did not inspect the observed process'
    assert str(processes[0]['arguments']['id']) in {str(r['Pid']) for r in locks[0]['result']['result']}
    assert '50' in result['report']
    print('LOCKS_50_ACCEPTANCE_OK', result['report'][:1200], flush=True)
finally:
    iris.execute('lock')
    if agent:
        request('PUT', '/api/mvp/agents/' + agent['id'], {**agent,'enabled':False})
