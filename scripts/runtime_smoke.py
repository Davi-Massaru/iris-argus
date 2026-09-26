"""Read-only HTTP acceptance checks; provide test credentials via environment."""
import os
import json
from pathlib import Path

import requests


def main():
    base = os.environ.get('AGENTIC_SMOKE_URL', 'http://127.0.0.1:52773/agentic')
    admin = (os.environ['AGENTIC_SMOKE_USER'], os.environ['AGENTIC_SMOKE_PASSWORD'])
    worker = json.loads(Path('/usr/irissys/mgr/agentic/worker-credential.json').read_text())

    def get(path, auth=None):
        return requests.get(base + path, auth=auth, timeout=10, allow_redirects=False)

    for path in ('/api/v1/session', '/api/v1/overview', '/api/v1/tools', '/health'):
        assert get(path).status_code == 401, path
    session = get('/api/v1/session', admin)
    assert session.status_code == 200
    data = session.json()
    assert data['principal'].upper() == admin[0].upper()
    assert 'PlatformAdministrator' in data['roles']
    assert len(data['csrf_token']) == 64
    assert get('/api/v1/session', (worker['username'], worker['password'])).status_code == 403
    assert get('/api/v1/session', admin).json()['principal'] == data['principal']
    assert get('/health', admin).json()['ready']
    assert get('/api/v1/overview', admin).status_code == 200
    first = get('/api/v1/tools?limit=5', admin).json()['items']
    second = get('/api/v1/tools?limit=5&offset=5', admin).json()['items']
    assert len(first) == len(second) == 5
    assert {t['stable_key'] for t in first}.isdisjoint(t['stable_key'] for t in second)
    assert all(not t['enabled'] and t['classification'] == 'UNKNOWN' for t in first + second)
    assert get('/', admin).status_code == 200
    for path in ('/assets/style', '/assets/script'):
        assert get(path, admin).status_code == 200, path
    csrf = requests.post(base + '/api/v1/proposals/nonexistent/approve', auth=admin,
                         json={'revision': 1, 'action_hash': 'a' * 64}, timeout=10)
    assert csrf.status_code == 403
    print('HTTP_SMOKE_OK identity, anonymous/unauthorized denial, SQL pages, assets, CSRF, worker readiness')


if __name__ == '__main__':
    main()
