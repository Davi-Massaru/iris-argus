import sys
from types import SimpleNamespace

from app import create_app
from app.repositories.iris_repository import MemoryRepository


def test_admin_name_does_not_grant_privilege():
    client = create_app(MemoryRepository(), testing=True).test_client()
    assert client.get('/api/v1/overview', environ_base={'REMOTE_USER': '_SYSTEM'}).status_code == 403


def test_runtime_uses_native_security_context_not_http_headers(monkeypatch):
    def execute(expression):
        return {'return $username': 'native-reader', 'return $roles': 'AgenticViewer'}[expression]
    monkeypatch.setitem(sys.modules, 'iris', SimpleNamespace(execute=execute))
    app = create_app(MemoryRepository())
    app.config['AGENTIC_CSRF_SECRET'] = b'test-secret'
    response = app.test_client().get('/api/v1/session', environ_base={'REMOTE_USER': '_SYSTEM'}, headers={'X-Test-User': '_SYSTEM'})
    assert response.get_json()['principal'] == 'native-reader'
    assert response.get_json()['roles'] == ['Viewer']


def test_security_context_failure_denies_access(monkeypatch):
    def execute(_):
        raise RuntimeError('Unavailable')
    monkeypatch.setitem(sys.modules, 'iris', SimpleNamespace(execute=execute))
    client = create_app(MemoryRepository()).test_client()
    assert client.get('/api/v1/overview', environ_base={'REMOTE_USER': '_SYSTEM'}).status_code == 401


def test_unknown_user_denied_even_with_roles(monkeypatch):
    monkeypatch.setitem(sys.modules, 'iris', SimpleNamespace(execute=lambda q: 'UnknownUser' if 'username' in q else '%All'))
    assert create_app(MemoryRepository()).test_client().get('/api/v1/overview').status_code == 401
