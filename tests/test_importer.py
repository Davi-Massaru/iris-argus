from pathlib import Path

import pytest

from app.tools.importer import load_contract


def test_imports_pinned_contract_without_enabling_operations():
    contract = load_contract(Path("specification/mainspec_v2.json"))
    assert contract.source_hash == "1ab154c7c5d9b25e6b227944a44a120c670686f876c2e14abfb9ee5898596650"
    assert contract.base_url == "/api/admin"
    assert len(contract.operations) > 100
    assert all(operation.classification == "UNKNOWN" and not operation.enabled for operation in contract.operations)
    assert any(operation.method == "GET" and operation.path == "/info" for operation in contract.operations)


def test_rejects_remote_refs(tmp_path):
    path = tmp_path / "contract.json"
    path.write_text('{"openapi":"3.0.0","info":{},"paths":{"/x":{"get":{"responses":{"200":{"$ref":"https://example.test/schema"}}}}}}')
    with pytest.raises(ValueError, match="Remote reference"):
        load_contract(path)


def test_rejects_unresolved_local_refs(tmp_path):
    path = tmp_path / "contract.json"
    path.write_text('{"openapi":"3.0.0","info":{},"paths":{"/x":{"get":{"responses":{"200":{"$ref":"#/components/schemas/Missing"}}}}}}')
    with pytest.raises(ValueError, match="Unresolved local reference"):
        load_contract(path)
