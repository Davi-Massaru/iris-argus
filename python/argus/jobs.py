"""IRIS Task Manager entry point. No Flask threads and no LLM calls."""
import base64
import os
import time
import json
from pathlib import Path
from collections import defaultdict
from argus import store
from argus.native import lock_waiters, related_waiters
from argus.sysadmin import SysAdminClient, SysAdminError

SECRET_FILE=Path('/usr/irissys/mgr/argus-collector.secret')


def collect(client=None):
    import iris
    own_client=client is None
    if own_client:
        auth=base64.b64encode(('ArgusCollector:'+SECRET_FILE.read_text().strip()).encode()).decode()
        client=SysAdminClient('Basic '+auth)
    try:
        settings=store.config()
        if not settings.get('enabled',True):
            return {'disabled':True}
        # All source queries must succeed before absence can be treated as recovery.
        processes=client.get('/v2/processes')
        locks=client.get('/v2/locks')
        native=lock_waiters()
        tasks=client.get('/v2/tasks')
        now=time.time()
        process_by_pid={str(p['Pid']):p for p in processes}
        grouped=defaultdict(list)
        for lock in locks:
            if lock.get('RemoteOwner'):
                continue
            owner=process_by_pid.get(str(lock.get('Pid')), {})
            namespace=owner.get('Nspace') or '%SYS'
            resource=lock['Directory']+'|'+lock['Reference'].split('(')[0]
            grouped[(namespace,resource)].append(lock)
        # Serialize evaluators with a database row lock and atomically preserve evidence.
        iris.tstart()
        try:
            store.sql("UPDATE Argus.Configuration SET Payload = Payload WHERE Name = 'collector'")
            for p in processes:
                store.snapshot('Process',str(p['Pid']),p,now)
            for lock in locks:
                store.snapshot('Lock',lock['Directory']+'|'+lock['Reference'],lock,now)
            for task in tasks:
                store.snapshot('Task',str(task['Id']),task,now)
            for incident in store.active_incidents():
                if incident['status'] in ('OPEN','ACKNOWLEDGED','IGNORED') and incident['type']=='LOCK':
                    grouped.setdefault((incident['namespace'],incident['resource']),[])
            decisions=[]
            for (namespace,resource),items in grouped.items():
                waiters=set(pid for item in items for pid in related_waiters(item,native))
                evidence={'locks':items[:30], 'waiter_pids':sorted(waiters),
                          'processes':[process_by_pid[str(pid)] for pid in waiters if str(pid) in process_by_pid][:30],
                          'source':'SysAdmin /v2/locks + %SYS.LockQuery.Detail',
                          'captured_at':now,'complete_lock_count':len(items)}
                decisions.append(store.observe('LOCK',namespace,resource,len(items),len(waiters),evidence,now,
                                 os.getenv('ARGUS_TIMEZONE','UTC'),settings))
            store.retention(now,settings)
            iris.tcommit()
        except Exception:
            iris.trollback()
            raise
        from argus.storage_collection import collect_storage
        try:
            collect_storage(client,settings,now)
            store.collection_status('storage',{'status':'available','checked_at':now})
        except SysAdminError as error:
            # A failure in storage must not discard successful lock/process evidence.
            store.collection_status('storage',{'status':'unavailable','checked_at':now,
                                    'reason':str(error),'http_status':error.status})
            if error.status!=403:
                raise
        return {'processes':len(processes),'locks':len(locks),'decisions':decisions}
    finally:
        if own_client:
            client.close()
