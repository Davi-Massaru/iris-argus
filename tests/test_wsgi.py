from unittest.mock import Mock
import pytest
import requests
from argus.sysadmin import SysAdminClient, SysAdminError
from argus.app import create_app

@pytest.mark.parametrize('status',[400,401,403,404,409,500])
def test_errors(status):
    transport=Mock();transport.request.return_value.status_code=status
    with pytest.raises(SysAdminError) as caught:
        SysAdminClient('Basic test',transport).get('/v2/processes')
    assert caught.value.status==status

def test_timeout():
    transport=Mock();transport.request.side_effect=requests.Timeout()
    with pytest.raises(SysAdminError,match='timed out'):
        SysAdminClient('Basic test',transport).get('/v2/locks')

def test_result_and_bounded_transport():
    transport=Mock();response=transport.request.return_value
    response.status_code=200;response.json.return_value={'status':{'errors':[]},'result':[{'Pid':1}]}
    assert SysAdminClient('Basic test',transport).get('/v2/processes')==[{'Pid':1}]
    assert transport.request.call_args.kwargs['allow_redirects'] is False

def test_missing_auth():
    assert create_app().test_client().get('/').status_code==401

def test_landing_and_unconfirmed_action():
    client=Mock();client.get.return_value={'username':'operator'}
    app=create_app(lambda auth:client); browser=app.test_client()
    assert browser.get('/',headers={'Authorization':'Basic test'}).status_code==200
    assert browser.post('/actions/task/run',data={'id':'1'},headers={'Authorization':'Basic test'}).status_code==400
    client.request.assert_not_called()
