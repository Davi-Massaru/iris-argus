from unittest.mock import Mock
from argus import store
from argus.storage_collection import collect_storage


def test_empty_iris_aggregate_starts_collection(monkeypatch):
    monkeypatch.setattr(store,'rows',lambda query,params=():[('',)] if 'MAX(' in query else [])
    save=Mock();monkeypatch.setattr(store,'snapshot',save)
    client=Mock();client.get.side_effect=[[{'Directory':'/data/','Name':'ARGUS'}],[{'Directory':'/data/','Size':32}]]
    collect_storage(client,{},1000)
    save.assert_called_once_with('Database','ARGUS',{'Directory':'/data/','Size':32},1000)
