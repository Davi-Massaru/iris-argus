"""Bounded storage collection on logical intervals inside the IRIS task."""
import json
import os
from argus import store
from argus.native import estimate_global


def due(kind,key,now,interval):
    found=store.rows('SELECT TOP 1 CapturedAt,Payload FROM Argus.'+kind+'Snapshot WHERE %EXACT(EntityKey) = ? ORDER BY CapturedAt DESC',(key,))
    previous=(float(found[0][0]),json.loads(found[0][1])) if found else None
    return (previous is None or now-previous[0]>=interval),previous


def collect_storage(client,settings,now):
    interval=max(300,int(settings.get('database_interval_seconds',3600)))
    last=store.rows('SELECT MAX(CapturedAt) FROM Argus.DatabaseSnapshot')
    if not last or last[0][0] in (None,'') or now-float(last[0][0])>=interval:
        databases=client.get('/v2/databases')
        names={d['Directory']:d['Name'] for d in databases if not d.get('Server')}
        for data in client.get('/v2/database-dirs',maxRows=100):
            name=names.get(data['Directory'],data['Directory'])
            should_collect,previous=due('Database',name,now,interval)
            if should_collect:
                store.snapshot('Database',name,data,now)
                if previous and now>previous[0]:
                    rate=max(0,(float(data['Size'])-float(previous[1]['Size']))*86400/(now-previous[0]))
                    store.observe('DATABASE_GROWTH','',name,rate,0,{'current':data,'previous':previous[1]},now,
                                  os.getenv('ARGUS_TIMEZONE','UTC'),dict(settings,max_sample_gap_seconds=interval*3))
    for watch in settings.get('global_watchlist',[])[:20]:
        namespace=watch['namespace'];name=watch['global']
        key=namespace+'|^'+name.lstrip('^')
        interval=max(3600,int(settings.get('global_interval_seconds',86400)))
        should_collect,previous=due('Global',key,now,interval)
        if should_collect:
            data=estimate_global(namespace,name)
            store.snapshot('Global',key,data,now)
            # The time-specific size baseline also detects failure to recover after a normal peak.
            store.observe('GLOBAL_SIZE',namespace,key,data['allocated_mb'],0,{'current':data},now,
                          os.getenv('ARGUS_TIMEZONE','UTC'),dict(settings,max_sample_gap_seconds=interval*3))
