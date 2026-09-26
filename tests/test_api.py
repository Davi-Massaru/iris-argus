from app import create_app
from app.repositories.iris_repository import MemoryRepository


def test_assets_require_role_and_only_serve_bundled_files():
    client = create_app(MemoryRepository(), testing=True).test_client()
    environment = {"REMOTE_USER": "reader", "agentic.test.roles": "AgenticViewer"}
    for name, content_type in (("style", "text/css"), ("script", "javascript")):
        assert client.get(f"/assets/{name}").status_code == 401
        response = client.get(f"/assets/{name}", environ_base=environment)
        assert response.status_code == 200
        assert content_type in response.content_type
    for name in ("app.css", "csrf.key", "../app/auth.py"):
        assert client.get(f"/assets/{name}", environ_base=environment).status_code == 404


def test_api_requires_authentication():
    client = create_app(MemoryRepository(), testing=True).test_client()
    assert client.get("/api/v1/overview").status_code == 401


def test_authenticated_overview_is_bounded():
    client = create_app(MemoryRepository(), testing=True).test_client()
    response = client.get("/api/v1/overview", environ_base={"REMOTE_USER": "reader", "agentic.test.roles": "AgenticViewer"})
    assert response.status_code == 200
    assert response.get_json()["pending_approvals"] == 0


def test_approval_requires_csrf_and_exact_revision_hash():
    repository = MemoryRepository()
    repository.proposals.append({"id": "p1", "revision": 1, "action_hash": "abc", "state": "PENDING_APPROVAL"})
    client = create_app(repository, testing=True).test_client()
    environment = {"REMOTE_USER": "_SYSTEM", "agentic.test.roles": "%All"}
    rejected = client.post("/api/v1/proposals/p1/approve", json={"revision": 1, "action_hash": "abc"}, environ_base=environment)
    assert rejected.status_code == 403
    token = client.get("/api/v1/session", environ_base=environment).get_json()["csrf_token"]
    stale = client.post("/api/v1/proposals/p1/approve", json={"revision": 2, "action_hash": "abc"}, headers={"X-Agentic-CSRF": token}, environ_base=environment)
    assert stale.status_code == 409
    accepted = client.post("/api/v1/proposals/p1/approve", json={"revision": 1, "action_hash": "abc"}, headers={"X-Agentic-CSRF": token}, environ_base=environment)
    assert accepted.status_code == 200
    assert accepted.get_json()["state"] == "APPROVED"
