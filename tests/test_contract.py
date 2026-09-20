import json
from pathlib import Path
from argus.catalog import SECTIONS

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'docs/contracts/mainspec_v2.json').read_text())

def test_catalog_uses_verified_get_endpoints():
    for _,path,_ in SECTIONS.values():
        assert 'get' in CONTRACT['paths'][path]

def test_lock_and_audit_semantics():
    assert 'get' not in CONTRACT['paths']['/v2/lock']
    assert 'post' in CONTRACT['paths']['/v2/security/audit/records']
    assert '202' in CONTRACT['paths']['/v2/security/audit/records']['post']['responses']
