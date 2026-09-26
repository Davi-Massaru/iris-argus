import copy
import pytest
from langchain_core.messages import AIMessage
from app import create_app
from app.repositories.iris_repository import MemoryRepository
from app.mvp.catalog import catalog, tool_by_key
from app.mvp.domain import validate_agent
from app.mvp.gateway import Gateway, ToolError
from app.mvp.runtime import execute, model_evidence


def config():
    return dict(name='DBA test', prompt='Inspecione o ambiente.', task='Consulte locks e relate.',
                model='qwen3:4b', provider='ollama', enabled=True, interval_seconds=0,
                tools=[{'key': 'get_v2_locks', 'fixed': {'maxRows': 100}}])


def test_contract_read_review_and_reference_resolution():
    assert len(catalog()) == 276
    assert tool_by_key('get_v2_process')['schema']['required'] == ['id']
    assert tool_by_key('get_v2_locks')['schema']['properties']['maxRows']['type'] == 'number'
    with pytest.raises(ValueError):
        tool_by_key('post_v2_process_terminate')


def test_evidence_compaction_preserves_count_and_processes_without_altering_original():
    original = {'result':[{'Pid':123, 'Reference':str(i)} for i in range(50)]}
    compact = model_evidence(original)
    assert compact['returned_row_count'] == 50
    assert compact['rows_by_process_id'] == {'123':50}
    assert len(compact['result']) == 8
    assert len(original['result']) == 50


@pytest.mark.parametrize('change', [dict(tools=[]), dict(interval_seconds=5), dict(enabled='yes'),
    dict(provider='unknown'), dict(prompt=''), dict(tools=[{'key':'delete_v2_lock'}]),
    dict(tools=[{'key':'get_v2_locks','fixed':{'arbitrary':'x'}}])])
def test_invalid_agent_rejected(change):
    with pytest.raises(ValueError):
        validate_agent({**config(), **change})


def test_gateway_rejects_unassigned_and_fixed_override_before_network():
    gateway = Gateway(config()['tools'])
    for key, args in [('get_info', {}), ('get_v2_locks', {'maxRows': 500}), ('get_v2_locks', {'url':'https://example.test'})]:
        with pytest.raises(ToolError):
            gateway.execute(key, args)


def test_gateway_uses_fixed_target_denies_redirect_and_limits_payload(monkeypatch):
    monkeypatch.setenv('AGENTIC_SYSADMIN_USER', 'test')
    monkeypatch.setenv('AGENTIC_SYSADMIN_PASSWORD', 'test-only')
    class Response:
        status_code = 200
        payload = b'{"result": []}'
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, size): yield self.payload
    class Transport:
        def get(self, url, **kwargs):
            assert url == 'http://127.0.0.1:52773/api/admin/v2/locks'
            assert kwargs['allow_redirects'] is False
            assert kwargs['params'] == {'maxRows':100}
            return Response()
    gateway = Gateway(config()['tools'], Transport())
    assert gateway.execute('get_v2_locks', {}) == {'result':[]}
    Response.status_code = 302
    with pytest.raises(ToolError, match='HTTP_302'):
        gateway.execute('get_v2_locks', {})
    Response.status_code = 200
    Response.payload = b'x' * 24001
    with pytest.raises(ToolError, match='RESPONSE_TOO_LARGE'):
        gateway.execute('get_v2_locks', {})


class FakeRepo:
    def __init__(self):
        self.calls = []
        self.finished = None
    def get_run(self, identifier):
        return {'snapshot': config()}
    def record_call(self, *args):
        self.calls.append(args)
        return 'evidence-1'
    def finish(self, *args):
        self.finished = args


class Model:
    def __init__(self, responses):
        self.responses = iter(responses)
    def bind_tools(self, tools):
        assert tools[0]['function']['name'] == 'get_v2_locks'
        assert 'maxRows' not in tools[0]['function']['parameters']['properties']
        return self
    def invoke(self, messages):
        return next(self.responses)


def test_runtime_records_evidence_and_uses_saved_prompt():
    repo = FakeRepo()
    model = Model([AIMessage(content='', tool_calls=[{'id':'c1','name':'get_v2_locks','args':{}}]), AIMessage(content='Sem locks. Evidência evidence-1.')])
    class ReadGateway:
        def __init__(self, bindings): pass
        def execute(self, key, args): return {'result': []}
    execute('run-1', repo, lambda *_:model, ReadGateway)
    assert repo.calls[0][1] == 'get_v2_locks'
    assert repo.finished[1] == 'SUCCEEDED'


def test_runtime_never_accepts_report_without_tool_evidence():
    repo = FakeRepo()
    with pytest.raises(ToolError, match='NO_SUCCESSFUL_TOOL_EVIDENCE'):
        execute('run-1', repo, lambda *_:Model([AIMessage(content='Invented report')]))
    assert repo.finished is None


def test_api_denies_viewer_writes_and_requires_csrf():
    client = create_app(MemoryRepository(), testing=True).test_client()
    viewer = {'REMOTE_USER':'reader', 'agentic.test.roles':'AgenticViewer'}
    designer = {'REMOTE_USER':'designer', 'agentic.test.roles':'AgenticAgentDesigner'}
    assert client.post('/api/mvp/agents', json=config(), environ_base=viewer).status_code == 403
    assert client.post('/api/mvp/agents', json=config(), environ_base=designer).status_code == 403
    assert client.get('/api/mvp/catalog').status_code == 401
    assert client.get('/api/mvp/catalog', environ_base=viewer).status_code == 200
