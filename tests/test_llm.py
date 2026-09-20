from unittest.mock import Mock
import pytest
import requests
from argus.llm import explain, ExplanationError

INCIDENT={'id':'test-incident','status':'OPEN','severity':'HIGH','impact':2,
          'reasons':['Verified waiting processes'], 'evidence':{'secret':'never transmit'},
          'resource':'private global reference'}


def test_no_key_auto_never_creates_transport(monkeypatch):
    monkeypatch.setenv('ARGUS_LLM_MODE','auto');monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    session=Mock(side_effect=AssertionError('Network forbidden'))
    monkeypatch.setattr(requests,'Session',session)
    result=explain(INCIDENT)
    assert result['provider']=='mock'
    assert 'Verified waiting processes' in result['text']
    assert result['usage'] is None
    session.assert_not_called()


def test_explicit_mock_ignores_key(monkeypatch):
    monkeypatch.setenv('ARGUS_LLM_MODE','mock');monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    transport=Mock()
    assert explain(INCIDENT,transport)['provider']=='mock'
    transport.post.assert_not_called()


def test_real_adapter_with_fake_transport(monkeypatch):
    monkeypatch.setenv('ARGUS_LLM_MODE','auto');monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    transport=Mock();response=transport.post.return_value
    response.status_code=200
    response.json.return_value={'status':'completed','output':[{'type':'reasoning'},
        {'type':'message','content':[{'type':'output_text','text':'Evidence test-incident.'}]}]}
    assert explain(INCIDENT,transport)['text']=='Evidence test-incident.'
    args=transport.post.call_args.kwargs
    assert args['json']['store'] is False
    assert 'never transmit' not in args['json']['input']
    assert 'private global' not in args['json']['input']
    assert 'tools' not in args['json']
    assert args['allow_redirects'] is False


@pytest.mark.parametrize('status',[401,429,500,302])
def test_provider_failure_preserves_evidence(monkeypatch,status):
    monkeypatch.setenv('ARGUS_LLM_MODE','openai');monkeypatch.setenv('OPENAI_API_KEY','test-only-key')
    transport=Mock();transport.post.return_value.status_code=status
    with pytest.raises(ExplanationError,match='Evidence is still available'):
        explain(INCIDENT,transport)


def test_explanation_requires_confirmation(monkeypatch):
    from argus.app import create_app
    from argus import store
    monkeypatch.setenv('ARGUS_LLM_MODE','mock')
    monkeypatch.setattr(store,'incident',lambda identifier:INCIDENT)
    client=Mock();client.get.return_value={'username':'operator','privileges':{'Operate':{'use':True}}}
    browser=create_app(lambda auth:client).test_client()
    auth={'Authorization':'Basic test'}
    assert browser.get('/explain/test-incident',headers=auth).status_code==200
    assert browser.post('/explain/test-incident',headers=auth).status_code==400
