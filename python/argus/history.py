"""Historical evidence UI. All readings explicitly retain their capture time."""
import csv
import io
import json
import time
from flask import Blueprint, g, render_template, request, url_for, abort, Response
from argus import store
from argus.sysadmin import SysAdminError

bp=Blueprint('history',__name__)


@bp.before_request
def authorize():
    if not g.identity.get('privileges',{}).get('Operate',{}).get('use'):
        raise SysAdminError(403,'Permission denied: %Admin_Operate required')


@bp.get('/incidents')
def incidents():
    data=store.incidents()
    for row in data:
        row['_url']=url_for('history.incident_detail',identifier=row['id'])
    return render_template('page.html',title='Incidents',section='incidents',mode='HISTORICAL EVIDENCE',
                           rows=data,columns=['title','severity','status','namespace','impact'],total=len(data),
                           notice='An observation becomes an incident through deterministic persistence or impact rules. A high value alone is not an incident.')


@bp.get('/incident/<identifier>')
def incident_detail(identifier):
    data=store.incident(identifier)
    if not data:
        abort(404)
    return render_template('incident.html',title=data['title'],section='incidents',mode='HISTORICAL EVIDENCE',incident=data)


@bp.get('/behavior')
def behavior():
    data=[json.loads(row[0]) for row in store.rows('SELECT TOP 200 Payload FROM Argus.BehaviorBaseline ORDER BY CapturedAt DESC')]
    return render_template('page.html',title='What is normal?',section='behavior',mode='HISTORICAL BASELINES',
                           rows=data,columns=['resource','namespace','bucket','sample_count','median','p95','confidence'],total=len(data),
                           notice='Baselines use the same local weekday and 15-minute bucket over the previous 30 days, excluding the current day. Fewer than five samples means learning mode.')


@bp.get('/task-snapshots')
def task_snapshots():
    data=[dict(json.loads(p),captured_at=float(t)) for t,p in store.rows('SELECT TOP 100 CapturedAt,Payload FROM Argus.TaskSnapshot ORDER BY CapturedAt DESC')]
    return render_template('page.html',title='Task snapshots',section='tasks',mode='HISTORICAL SNAPSHOTS',
        rows=data,columns=['Id','Name','Namespace','Suspended','LastFinished','NextScheduled','captured_at'],total=len(data),
        notice='Most recent task configuration snapshots. A scheduled time does not prove execution or success.',
        links=[('Live task history',url_for('section_view',section='task-history'))])


@bp.get('/report/incident/<identifier>')
def report(identifier):
    data=store.incident(identifier)
    if not data:
        abort(404)
    fmt=request.args.get('format','html')
    if fmt not in ('html','json','csv'):
        abort(400)
    store.event('ReportExecution',{'incident_id':identifier,'format':fmt,'user':g.identity['username']})
    if fmt=='json':
        return Response(json.dumps(data,indent=2),mimetype='application/json',headers={'Content-Disposition':'attachment; filename="argus-incident.json"'})
    if fmt=='csv':
        out=io.StringIO();writer=csv.writer(out);writer.writerow(['captured_at','decision','reasons'])
        for item in data['timeline']:
            writer.writerow([item['captured_at'],item['decision'],'; '.join(item['reasons'])])
        return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename="argus-incident.csv"'})
    return render_template('incident.html',title='Incident report',section='incidents',mode='HISTORICAL REPORT',incident=data)
