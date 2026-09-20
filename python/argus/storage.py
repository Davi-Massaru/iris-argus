"""Namespace and physical storage investigation; estimates run only on demand."""
import json
import time
from flask import Blueprint, g, request, render_template, url_for, abort, redirect
from itsdangerous import TimestampSigner, BadSignature
from argus import store
from argus.native import resolve_global, global_mappings, estimate_global
from argus.domain import growth

bp=Blueprint('storage',__name__)


def size_history(kind,key):
    if kind not in ('Database','Global'):
        raise ValueError(kind)
    result=store.rows('SELECT TOP 1500 CapturedAt,Payload FROM Argus.'+kind+'Snapshot WHERE %EXACT(EntityKey) = ? ORDER BY CapturedAt DESC',(key,))
    return [(float(t),json.loads(p)) for t,p in result]


@bp.get('/storage/global')
def global_view():
    namespace=request.args.get('namespace',''); name=request.args.get('global','')
    fields=[('namespace','Namespace'),('global','Root global')]
    kwargs={}
    if namespace and name:
        g.client.get('/v2/namespace',name=namespace)
        try:
            details=resolve_global(namespace,name)
        except ValueError as error:
            abort(400,str(error))
        databases=g.client.get('/v2/databases')
        physical=next((d['Name'] for d in databases if d.get('Directory')==details['Directory']),None)
        details['Database']=physical or 'Unavailable'
        history=size_history('Global',namespace+'|'+details['Global'])
        details['Latest measurement']=dict(history[0][1],captured_at=history[0][0]) if history else 'No size estimate collected'
        samples=[(t,p['allocated_mb']) for t,p in history]
        details['Growth MB']={str(day)+' days':growth(samples,time.time(),day) or 'Insufficient history' for day in (1,7,30)}
        kwargs.update(details=details,measure_token=TimestampSigner(request.headers['Authorization'],salt='argus-global-estimate').sign(namespace+'|'+name).decode())
        if physical:
            kwargs['links']=[('Database '+physical,url_for('detail',kind='database',name=physical))]
    return render_template('global.html',title='Global explorer',section='global',fields=fields,
                           notice='Resolve logical data to physical storage. Estimates are collected only when requested or explicitly configured in the collector watchlist.',**kwargs)


@bp.post('/storage/global/measure')
def measure():
    namespace=request.form.get('namespace','');name=request.form.get('global','')
    try:
        signed=TimestampSigner(request.headers['Authorization'],salt='argus-global-estimate').unsign(request.form.get('token',''),max_age=300).decode()
        if signed!=namespace+'|'+name:
            abort(400)
    except BadSignature:
        abort(400)
    g.client.get('/v2/namespace',name=namespace)
    try:
        data=estimate_global(namespace,name)
    except ValueError as error:
        abort(400,str(error))
    store.snapshot('Global',namespace+'|'+data['Global'],data,time.time())
    return redirect(url_for('storage.global_view',namespace=namespace,**{'global':name}))


@bp.get('/storage/iristemp')
def iristemp():
    processes=g.client.get('/v2/processes')
    data=sorted(processes,key=lambda row:row.get('PrvGblBlkCnt',0),reverse=True)[:100]
    for row in data:
        row['_url']=url_for('process_detail',pid=row['Pid'])
    return render_template('page.html',title='IRISTEMP investigator',section='iristemp',rows=data,
                           columns=['Pid','Nspace','Routine','PrvGblBlkCnt','State'],total=len(data),
                           notice='Private-global block counts are reported by IRIS. They are not converted to bytes or assumed to account for all IRISTEMP usage.')


@bp.get('/storage/growth')
def growth_view():
    g.client.get('/v2/databases')
    data=[]
    for (key,) in store.rows('SELECT DISTINCT %EXACT(EntityKey) FROM Argus.DatabaseSnapshot'):
        history=size_history('Database',key)
        samples=[(t,p['Size']) for t,p in history if isinstance(p.get('Size'),(int,float))]
        row={'Database':key,'Current MB':samples[0][1] if samples else 'Unavailable'}
        for days in (1,7,30):
            change=growth(samples,time.time(),days)
            row[str(days)+'d change MB']=round(change['change_mb'],3) if change else 'Insufficient history'
        data.append(row)
    return render_template('page.html',title='Database growth',section='growth',mode='HISTORICAL SNAPSHOTS',
                           rows=data,columns=['Database','Current MB','1d change MB','7d change MB','30d change MB'],total=len(data),
                           details={'Storage collection':store.collection_status('storage')},
                           notice='Database allocated size comes from SysAdmin /v2/database-dirs. Collection is hourly; growth uses actual capture times. Global estimates are tracked separately.')
