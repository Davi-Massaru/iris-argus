"""Run through scripts/embedded_tests.py, never against an external database."""
import importlib.util
import pytest

pytestmark=pytest.mark.skipif(importlib.util.find_spec('iris') is None,reason='Requires Embedded Python')


def test_persisted_incident_lifecycle():
    import iris
    from argus import store
    iris.tstart()
    try:
        settings={'persistence_seconds':60,'grace_seconds':60}
        evidence={'test_only':True,'waiter_pids':[123]}
        count=len(store.incidents())
        for now in (1000,1060,1090):
            store.observe('LOCK','ARGUS','test-rollback-only',1,1,evidence,now,'UTC',settings)
        found=[i for i in store.incidents() if i['resource']=='test-rollback-only']
        assert len(found)==1 and found[0]['status']=='OPEN'
        key=found[0]['id']
        store.observe('LOCK','ARGUS','test-rollback-only',0,0,{},1100,'UTC',settings)
        assert store.incident(key)['status']=='OPEN'
        store.observe('LOCK','ARGUS','test-rollback-only',0,0,{},1160,'UTC',settings)
        saved=store.incident(key)
        assert saved['status']=='RESOLVED'
        assert saved['timeline'][0]['evidence']['waiter_pids']==[123]
        assert len(saved['timeline'])==3
    finally:
        iris.trollback()


def test_global_history_preserves_case():
    import iris
    from argus import store
    from argus.storage import size_history
    iris.tstart()
    try:
        store.snapshot('Global','ARGUS|^CaseSensitiveDemo',{'allocated_mb':1},1000)
        store.snapshot('Global','ARGUS|^CASESENSITIVEDEMO',{'allocated_mb':2},1000)
        assert size_history('Global','ARGUS|^CaseSensitiveDemo')==[(1000,{'allocated_mb':1})]
        keys=[row[0] for row in store.rows('SELECT DISTINCT %EXACT(EntityKey) FROM Argus.GlobalSnapshot')]
        assert 'ARGUS|^CaseSensitiveDemo' in keys
    finally:
        iris.trollback()
