import json
import sys
from types import SimpleNamespace
import pytest
from langchain_core.messages import AIMessage
from app import create_app
from app.repositories.iris_repository import MemoryRepository
from app.mvp.catalog import catalog, load_reviewed_read_operations, tool_by_key
from app.mvp.domain import validate_agent
from app.mvp.gateway import Gateway, ToolError
from app.mvp.runtime import execute, model_evidence, redact_sensitive, _remove_schema_examples
from app.mvp.providers import chat_model, default_model


def config():
    tool = tool_by_key("get_v2_locks")
    return dict(
        name="DBA test",
        prompt="Inspect the environment.",
        task="Query locks and report the findings.",
        model="qwen3:4b",
        provider="ollama",
        enabled=True,
        interval_seconds=0,
        tools=[
            {
                "key": tool["key"],
                "stable_key": tool["stable_key"],
                "contract_hash": tool["contract_hash"],
                "fixed": {"maxRows": 100},
            }
        ],
    )


def test_openai_provider_uses_server_config_without_network(monkeypatch):
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(sys.modules, "langchain_openai", SimpleNamespace(ChatOpenAI=FakeChatOpenAI))
    monkeypatch.setenv("AGENTIC_OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("AGENTIC_OPENAI_BASE_URL", "https://openai.example.test/v1")
    chat_model("openai", "gpt-4o-mini")
    assert captured == {
        "model": "gpt-4o-mini",
        "api_key": "test-only-key",
        "temperature": 0,
        "max_tokens": 1000,
        "base_url": "https://openai.example.test/v1",
    }


def test_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("AGENTIC_OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="AGENTIC_OPENAI_API_KEY"):
        chat_model("openai", "gpt-4o-mini")


def test_default_model_follows_configured_provider(monkeypatch):
    monkeypatch.delenv("AGENTIC_MODEL", raising=False)
    assert default_model("ollama") == "qwen2.5:3b"
    assert default_model("openai") == "gpt-4o-mini"


def test_contract_read_review_and_reference_resolution():
    items = catalog()
    assert len(items) == 276
    assert all(item["supported"] for item in items)
    reviewed_reads = [item for item in items if item["default_read_only"]]
    assert len(reviewed_reads) == 18
    assert all(item["method"] == "GET" and not item["sensitive"] for item in reviewed_reads)
    assert (
        sum(item["method"] == "POST" and "body" in item["schema"]["properties"] for item in items)
        > 0
    )
    assert tool_by_key("get_v2_process")["schema"]["required"] == ["id"]
    assert tool_by_key("get_v2_locks")["schema"]["properties"]["maxRows"]["type"] == "number"
    assert tool_by_key("post_v2_process_terminate")["method"] == "POST"


def test_external_read_manifest_is_pinned_and_rejects_mutating_or_sensitive_tools(tmp_path):
    contract_hash = "pinned-contract"
    operation = {"method": "GET", "path": "/safe", "supported": True, "sensitive": False}
    manifest_path = tmp_path / "reviewed.json"

    def write_manifest(entry, source_hash=contract_hash):
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_contract": "mainspec_v2.json",
                    "source_sha256": source_hash,
                    "operations": [entry],
                }
            ),
            encoding="utf-8",
        )

    valid_entry = {
        "method": "GET",
        "path": "/safe",
        "classification": "READ_ONLY",
        "reason": "Reviewed read.",
    }
    write_manifest(valid_entry)
    assert load_reviewed_read_operations(manifest_path, contract_hash, [operation]) == {
        ("GET", "/safe"): "Reviewed read."
    }

    write_manifest(valid_entry, source_hash="stale-contract")
    with pytest.raises(RuntimeError, match="does not match"):
        load_reviewed_read_operations(manifest_path, contract_hash, [operation])

    write_manifest({**valid_entry, "method": "POST"})
    with pytest.raises(RuntimeError, match="READ_ONLY GET"):
        load_reviewed_read_operations(manifest_path, contract_hash, [operation])

    write_manifest(valid_entry)
    with pytest.raises(RuntimeError, match="unsupported or sensitive"):
        load_reviewed_read_operations(
            manifest_path, contract_hash, [{**operation, "sensitive": True}]
        )


def test_evidence_compaction_preserves_count_and_processes_without_altering_original():
    original = {"result": [{"Pid": 123, "Reference": str(i)} for i in range(50)]}
    compact = model_evidence(original)
    assert compact["returned_row_count"] == 50
    assert compact["rows_by_process_id"] == {"123": 50}
    assert len(compact["result"]) == 8
    assert len(original["result"]) == 50


def test_sensitive_values_are_redacted_and_schema_examples_removed():
    assert redact_sensitive(
        {"user": "dba", "nested": [{"password": "secret", "apiToken": "token"}]}
    ) == {"user": "dba", "nested": [{"password": "[REDACTED]", "apiToken": "[REDACTED]"}]}
    assert _remove_schema_examples({"type": "string", "example": "SYS", "default": "secret"}) == {
        "type": "string"
    }


@pytest.mark.parametrize(
    "change",
    [
        dict(tools=[]),
        dict(interval_seconds=5),
        dict(enabled="yes"),
        dict(provider="unknown"),
        dict(prompt=""),
        dict(tools=[{"key": "delete_v2_lock"}]),
        dict(tools=[{"key": "get_v2_locks", "fixed": {"arbitrary": "x"}}]),
    ],
)
def test_invalid_agent_rejected(change):
    with pytest.raises(ValueError):
        validate_agent({**config(), **change}, enabled_keys={"get_v2_locks"})


def test_agent_validation_rejects_tools_blocked_by_dba():
    with pytest.raises(ValueError, match="blocked"):
        validate_agent(config(), enabled_keys=set())


def test_agent_validation_pins_enabled_tool_version():
    validated = validate_agent(config(), enabled_keys={"get_v2_locks"})
    binding = validated["tools"][0]
    item = tool_by_key("get_v2_locks")
    assert binding["stable_key"] == item["stable_key"]
    assert binding["contract_hash"] == item["contract_hash"]


def test_agent_validation_uses_deployment_provider(monkeypatch):
    monkeypatch.setenv("AGENTIC_PROVIDER", "openai")
    monkeypatch.setenv("AGENTIC_OPENAI_API_KEY", "test-only-key")
    payload = {**config(), "provider": "openai", "model": "gpt-4o-mini"}
    validated = validate_agent(payload, enabled_keys={"get_v2_locks"})
    assert validated["provider"] == "openai"
    assert validated["model"] == "gpt-4o-mini"


def test_gateway_rejects_unassigned_and_fixed_override_before_network():
    gateway = Gateway(config()["tools"], availability_lookup=lambda _item: True)
    for key, args in [
        ("get_info", {}),
        ("get_v2_locks", {"maxRows": 500}),
        ("get_v2_locks", {"url": "https://example.test"}),
    ]:
        with pytest.raises(ToolError):
            gateway.execute(key, args)


def test_gateway_uses_fixed_target_denies_redirect_and_limits_payload(monkeypatch):
    monkeypatch.setenv("AGENTIC_SYSADMIN_USER", "test")
    monkeypatch.setenv("AGENTIC_SYSADMIN_PASSWORD", "test-only")

    class Response:
        status_code = 200
        payload = b'{"result": []}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_content(self, size):
            yield self.payload

    class Transport:
        def request(self, method, url, **kwargs):
            assert method == "GET"
            assert url == "http://127.0.0.1:52773/api/admin/v2/locks"
            assert kwargs["allow_redirects"] is False
            assert kwargs["params"] == {"maxRows": 100}
            return Response()

    gateway = Gateway(config()["tools"], Transport(), availability_lookup=lambda _item: True)
    assert gateway.execute("get_v2_locks", {}) == {"result": []}
    Response.status_code = 302
    with pytest.raises(ToolError, match="HTTP_302"):
        gateway.execute("get_v2_locks", {})
    Response.status_code = 200
    Response.payload = b"x" * 24001
    with pytest.raises(ToolError, match="RESPONSE_TOO_LARGE"):
        gateway.execute("get_v2_locks", {})


def test_gateway_dispatches_json_body_and_accepts_created_response(monkeypatch):
    monkeypatch.setenv("AGENTIC_SYSADMIN_USER", "test")
    monkeypatch.setenv("AGENTIC_SYSADMIN_PASSWORD", "test-only")
    operation = next(
        item
        for item in catalog()
        if item["method"] == "POST"
        and item["schema"]["properties"].get("body", {}).get("type") == "object"
        and not item["schema"]["properties"]["body"].get("required")
    )
    arguments = {"body": {}}

    class Response:
        status_code = 201

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_content(self, size):
            yield b'{"created": true}'

    class Transport:
        def request(self, method, url, **kwargs):
            assert method == "POST"
            assert url == "http://127.0.0.1:52773/api/admin" + operation["path"]
            assert kwargs["json"] == arguments["body"]
            assert kwargs["allow_redirects"] is False
            return Response()

    gateway = Gateway(
        [
            {
                "key": operation["key"],
                "stable_key": operation["stable_key"],
                "contract_hash": operation["contract_hash"],
                "fixed": {},
            }
        ],
        Transport(),
        availability_lookup=lambda _item: True,
    )
    assert gateway.execute(operation["key"], arguments) == {"created": True}


def test_gateway_rechecks_availability_before_each_call():
    status = {"enabled": True}
    gateway = Gateway(config()["tools"], availability_lookup=lambda _item: status["enabled"])
    status["enabled"] = False
    with pytest.raises(ToolError, match="TOOL_BLOCKED"):
        gateway.execute("get_v2_locks", {})


def test_gateway_rejects_stale_tool_contract_pin():
    binding = config()["tools"][0]
    binding["contract_hash"] = "stale-contract"
    with pytest.raises(ToolError, match="TOOL_VERSION_MISMATCH"):
        Gateway([binding], availability_lookup=lambda _item: True)


class FakeRepo:
    def __init__(self):
        self.calls = []
        self.finished = None

    def get_run(self, identifier):
        return {"snapshot": config()}

    def record_call(self, *args):
        self.calls.append(args)
        return "evidence-1"

    def finish(self, *args):
        self.finished = args


class Model:
    def __init__(self, responses):
        self.responses = iter(responses)

    def bind_tools(self, tools):
        assert tools[0]["function"]["name"] == "get_v2_locks"
        assert "maxRows" not in tools[0]["function"]["parameters"]["properties"]
        return self

    def invoke(self, messages):
        return next(self.responses)


def test_runtime_records_evidence_and_uses_saved_prompt():
    repo = FakeRepo()
    model = Model(
        [
            AIMessage(content="", tool_calls=[{"id": "c1", "name": "get_v2_locks", "args": {}}]),
            AIMessage(content="No locks."),
        ]
    )

    class ReadGateway:
        def __init__(self, bindings):
            pass

        def execute(self, key, args):
            return {"result": []}

    execute("run-1", repo, lambda *_: model, ReadGateway)
    assert repo.calls[0][1] == "get_v2_locks"
    assert repo.finished[1] == "SUCCEEDED"
    assert repo.finished[2].endswith("Evidence IDs: evidence-1")


def test_runtime_does_not_duplicate_evidence_id_already_in_report():
    repo = FakeRepo()
    model = Model(
        [
            AIMessage(content="", tool_calls=[{"id": "c1", "name": "get_v2_locks", "args": {}}]),
            AIMessage(content="No locks. Evidence evidence-1."),
        ]
    )

    class ReadGateway:
        def __init__(self, bindings):
            pass

        def execute(self, key, args):
            return {"result": []}

    execute("run-1", repo, lambda *_: model, ReadGateway)
    assert repo.finished[2].count("evidence-1") == 1


def test_runtime_rebinds_legacy_agent_to_deployment_provider(monkeypatch):
    monkeypatch.setenv("AGENTIC_PROVIDER", "openai")
    monkeypatch.setenv("AGENTIC_MODEL", "gpt-4o-mini")
    repo = FakeRepo()
    selected = []

    class NoEvidenceModel:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return AIMessage(content="No evidence yet.")

    with pytest.raises(ToolError, match="NO_SUCCESSFUL_TOOL_EVIDENCE"):
        execute(
            "run-1",
            repo,
            lambda provider, model: selected.append((provider, model)) or NoEvidenceModel(),
            lambda _bindings: None,
        )
    assert selected == [("openai", "gpt-4o-mini")]


def test_runtime_never_accepts_report_without_tool_evidence():
    repo = FakeRepo()
    with pytest.raises(ToolError, match="NO_SUCCESSFUL_TOOL_EVIDENCE"):
        execute(
            "run-1", repo, lambda *_: Model([AIMessage(content="Invented report")]), lambda *_: None
        )
    assert repo.finished is None


def test_api_denies_viewer_writes_and_requires_csrf():
    client = create_app(MemoryRepository(), testing=True).test_client()
    viewer = {"REMOTE_USER": "reader", "agentic.test.roles": "AgenticViewer"}
    designer = {"REMOTE_USER": "designer", "agentic.test.roles": "AgenticAgentDesigner"}
    assert client.post("/api/mvp/agents", json=config(), environ_base=viewer).status_code == 403
    assert client.post("/api/mvp/agents", json=config(), environ_base=designer).status_code == 403
    assert client.get("/api/mvp/catalog").status_code == 401
    assert client.get("/api/mvp/catalog", environ_base=viewer).status_code == 200


def test_tool_availability_toggle_requires_dba_csrf_and_acknowledgment():
    operation = next(item for item in catalog() if item["method"] == "POST" and item["supported"])
    repository = MemoryRepository()
    repository.tools = [
        {
            "stable_key": operation["stable_key"],
            "contract_hash": operation["contract_hash"],
            "enabled": False,
        }
    ]
    client = create_app(repository, testing=True).test_client()
    viewer = {"REMOTE_USER": "reader", "agentic.test.roles": "AgenticViewer"}
    dba = {"REMOTE_USER": "dba", "agentic.test.roles": "AgenticDBAApprover"}
    path = f"/api/mvp/catalog/{operation['stable_key']}/availability"

    assert client.put(path, json={"enabled": True}, environ_base=viewer).status_code == 403
    csrf = client.get("/api/v1/session", environ_base=dba).get_json()["csrf_token"]
    headers = {"X-Agentic-CSRF": csrf}
    missing_ack = client.put(path, json={"enabled": True}, headers=headers, environ_base=dba)
    assert missing_ack.status_code == 400
    enabled = client.put(
        path,
        json={
            "enabled": True,
            "acknowledge_auto_execution": True,
            "acknowledge_sensitive_data": True,
        },
        headers=headers,
        environ_base=dba,
    )
    assert enabled.status_code == 200
    item = next(
        item
        for item in client.get("/api/mvp/catalog", environ_base=dba).get_json()["items"]
        if item["stable_key"] == operation["stable_key"]
    )
    assert item["allowed"] is True
    assert repository.tools[0]["updated_by"] == "dba"


def test_reviewed_read_preset_is_dba_only_and_blocks_other_methods():
    items = catalog()
    repository = MemoryRepository()
    repository.tools = [
        {
            "stable_key": item["stable_key"],
            "contract_hash": item["contract_hash"],
            "enabled": False,
        }
        for item in items
    ]
    client = create_app(repository, testing=True).test_client()
    viewer = {"REMOTE_USER": "reader", "agentic.test.roles": "AgenticViewer"}
    dba = {"REMOTE_USER": "dba", "agentic.test.roles": "AgenticDBAApprover"}
    path = "/api/mvp/catalog/presets/reviewed-reads"

    assert client.put(path, json={}, environ_base=viewer).status_code == 403
    csrf = client.get("/api/v1/session", environ_base=dba).get_json()["csrf_token"]
    headers = {"X-Agentic-CSRF": csrf}
    assert client.put(path, json={}, environ_base=dba).status_code == 403
    enabled = client.put(path, json={}, headers=headers, environ_base=dba)
    assert enabled.status_code == 200
    assert enabled.get_json()["changed"] == 18

    catalog_response = client.get("/api/mvp/catalog", environ_base=dba).get_json()["items"]
    assert sum(item["available"] for item in catalog_response) == 18
    assert all(item["available"] for item in catalog_response if item["default_read_only"])
    assert not any(item["available"] for item in catalog_response if item["method"] != "GET")

    blocked = client.put(
        "/api/mvp/catalog/presets/block-all", json={}, headers=headers, environ_base=dba
    )
    assert blocked.status_code == 200
    assert blocked.get_json()["changed"] == 18
    assert not any(tool["enabled"] for tool in repository.tools)
