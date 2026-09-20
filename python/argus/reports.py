"""Deterministic, bounded operational reports in HTML, JSON and CSV."""
import csv
import io
import json
import time
from datetime import datetime,timezone
from flask import Blueprint, g, request, render_template, Response, abort, url_for
from argus import store
from argus.domain import growth
from argus.storage import size_history
from argus.history import authorize

bp=Blueprint('reports',__name__)
bp.before_request(authorize)


def csv_cell(value):
    value=json.dumps(value) if isinstance(value,(list,dict)) else str(value if value is not None else '')
    return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value


def dataset(kind):
    if kind=='locks':
        return [row for row in store.incidents() if row['type']=='LOCK'],['id','resource','namespace','severity','status','impact','confidence','reasons']
    if kind=='behavior':
        data=[dict(json.loads(p),captured_at=float(t)) for t,p in store.rows('SELECT TOP 200 CapturedAt,Payload FROM Argus.BehaviorBaseline ORDER BY CapturedAt DESC')]
        return data,['kind','resource','namespace','bucket','sample_count','median','p95','confidence','captured_at']
    if kind=='growth':
        data=[]
        for table in ('Database','Global'):
            for (key,) in store.rows('SELECT DISTINCT %EXACT(EntityKey) FROM Argus.'+table+'Snapshot'):
                samples=size_history(table,key)
                field='Size' if table=='Database' else 'allocated_mb'
                sizes=[(t,float(p[field])) for t,p in samples if p.get(field) is not None]
                if not sizes:
                    continue
                row={'kind':table,'resource':key,'allocated_mb':sizes[0][1],'captured_at':sizes[0][0]}
                for days in (1,7,30):
                    change=growth(sizes,time.time(),days)
                    row[str(days)+'d_change_mb']=change['change_mb'] if change else None
                data.append(row)
        return data,['kind','resource','allocated_mb','1d_change_mb','7d_change_mb','30d_change_mb','captured_at']
    abort(404)


@bp.get('/reports')
def index():
    return render_template('page.html',title='Operational reports',section='reports',mode='HISTORICAL REPORTS',
        notice='Reports use preserved observations and deterministic rules. No LLM is required.',
        links=[(name.title()+' report',url_for('reports.report',kind=name)) for name in ('locks','growth','behavior')])


@bp.get('/reports/<kind>')
def report(kind):
    fmt=request.args.get('format','html')
    if fmt not in ('html','json','csv'):
        abort(400)
    data,columns=dataset(kind)
    report={'kind':kind,'generated_at':datetime.now(timezone.utc).isoformat(),
            'scope':'Latest 100 incidents / 200 baselines / 1500 measurements per resource',
            'rows':data,'note':'Missing growth is insufficient history. Global sizes are estimates, not a complete inventory of database contributors.'}
    if kind=='growth':
        report['collection']=store.collection_status('storage')
        report['note']+=' Storage collection: '+report['collection']['status']+'.'
    store.event('ReportExecution',{'kind':kind,'format':fmt,'user':g.identity['username'],'row_count':len(data)})
    if fmt=='json':
        return Response(json.dumps(report,indent=2),mimetype='application/json')
    if fmt=='csv':
        out=io.StringIO();writer=csv.writer(out);writer.writerow(columns)
        writer.writerows([[csv_cell(row.get(col)) for col in columns] for row in data])
        return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="argus-'+kind+'.csv"'})
    return render_template('page.html',title=kind.title()+' report',section='reports',mode='HISTORICAL REPORT',
        rows=data,columns=columns,total=len(data),notice=report['scope']+'. '+report['note'],
        links=[('Export '+fmt.upper(),url_for('reports.report',kind=kind,format=fmt)) for fmt in ('json','csv')])
