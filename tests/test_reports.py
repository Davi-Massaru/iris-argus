from unittest.mock import Mock
from argus.app import create_app
from argus import store
from argus.reports import csv_cell


def test_csv_formula_is_text():
    assert csv_cell('=HYPERLINK("bad")').startswith("'")
    assert csv_cell(' @SUM(1)').startswith("'")
    assert csv_cell('normal')=='normal'


def test_reports_require_operate():
    client=Mock();client.get.return_value={'username':'limited'}
    response=create_app(lambda auth:client).test_client().get('/reports',headers={'Authorization':'Basic test'})
    assert response.status_code==403


def test_historical_report_export(monkeypatch):
    monkeypatch.setattr(store,'incidents',lambda:[{'id':'evidence-id','type':'LOCK','status':'RESOLVED','resource':'^Test'}])
    events=[]
    monkeypatch.setattr(store,'event',lambda kind,data:events.append((kind,data)))
    client=Mock();client.get.return_value={'username':'operator','privileges':{'Operate':{'use':True}}}
    browser=create_app(lambda auth:client).test_client()
    for fmt in ('html','json','csv'):
        response=browser.get('/reports/locks?format='+fmt,headers={'Authorization':'Basic test'})
        assert response.status_code==200
        assert b'evidence-id' in response.data
    assert len(events)==3
