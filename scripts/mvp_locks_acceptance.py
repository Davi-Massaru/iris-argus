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
agent = request('POST', '/api/mvp/agents', dict(
    name='__MVP_LOCKS_ACCEPTANCE__', prompt='Você é um DBA. Use ferramentas para produzir relatório curto e factual em português.',
    task='Consulte get_v2_locks. Se houver pelo menos 50 registros, consulte get_v2_process para cada PID distinto observado (não por lock) e registre um relatório de erro. Se houver menos de 50, registre que a condição não ocorreu. Cite os IDs das evidências. Não altere nada.',
    model='qwen2.5:3b', provider='ollama', enabled=True, interval_seconds=0,
    tools=[{'key':'get_v2_locks','fixed':{'filter':'AgenticMVPTest','maxRows':100}},
           {'key':'get_v2_process','fixed':{}}]), status=201)
Path('/usr/irissys/mgr/agentic/mvp-locks-test.json').write_text(json.dumps({'agent_id':agent['id']}))
try:
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
    request('PUT', '/api/mvp/agents/' + agent['id'], {**agent,'enabled':False})
