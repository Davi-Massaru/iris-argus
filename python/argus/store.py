"""IRIS SQL persistence; imports IRIS only inside Embedded Python calls."""
import json
import time
from uuid import uuid4
from dataclasses import asdict
from argus.domain import Condition, evaluate, fingerprint, statistics, time_bucket

SNAPSHOT_KINDS=('Process','Lock','Task','Database','Global')


def sql(statement, params=()):
    import iris
    try:
        return iris.sql.exec(statement, *params)
    except Exception as error:
        if getattr(error,'sqlcode',None)==100:
            return []  # IRIS reports no rows affected as SQLCODE 100.
        raise


def rows(statement, params=()):
    return [tuple(row) for row in sql(statement,params)]


def initialize():
    definitions={
      'Configuration':'Name VARCHAR(100) PRIMARY KEY, Payload VARCHAR(32000)',
      'Observation':'ID VARCHAR(36) PRIMARY KEY, Fingerprint VARCHAR(64), CapturedAt DOUBLE, BucketKey VARCHAR(32), Value DOUBLE',
      'BehaviorBaseline':'Fingerprint VARCHAR(100) PRIMARY KEY, CapturedAt DOUBLE, Payload VARCHAR(32000)',
      'Condition':'Fingerprint VARCHAR(64) PRIMARY KEY, Payload VARCHAR(32000)',
      'Incident':'ID VARCHAR(36) PRIMARY KEY, Fingerprint VARCHAR(64), StartedAt DOUBLE, LastSeenAt DOUBLE, ResolvedAt DOUBLE, Status VARCHAR(20), Payload VARCHAR(32000)',
      'IncidentEvidence':'ID VARCHAR(36) PRIMARY KEY, IncidentID VARCHAR(36), CapturedAt DOUBLE, Payload VARCHAR(32000)',
      'ReportExecution':'ID VARCHAR(36) PRIMARY KEY, CapturedAt DOUBLE, Payload VARCHAR(32000)',
      'ActionEvent':'ID VARCHAR(36) PRIMARY KEY, CapturedAt DOUBLE, Payload VARCHAR(32000)',
    }
    definitions.update({kind+'Snapshot':'ID VARCHAR(36) PRIMARY KEY, EntityKey VARCHAR(512), CapturedAt DOUBLE, Payload VARCHAR(32000)' for kind in SNAPSHOT_KINDS})
    for name,definition in definitions.items():
        if not rows('SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?',('Argus',name)):
            sql('CREATE TABLE Argus.'+name+' ('+definition+')')
    if not rows('SELECT Name FROM Argus.Configuration WHERE Name = ?',('collector',)):
        sql('INSERT INTO Argus.Configuration (Name,Payload) VALUES (?,?)',('collector',json.dumps({'enabled':True,'persistence_seconds':60,'grace_seconds':60,'bucket_minutes':15,'history_days':30,
            'retention_days':{'Process':7,'Lock':30,'Task':30,'Database':365,'Global':365,'Evidence':90,'Incident':365,'Baseline':365}})))
        sql('CREATE INDEX ArgusObservationLookup ON Argus.Observation (Fingerprint,BucketKey,CapturedAt)')
        sql('CREATE INDEX ArgusEvidenceLookup ON Argus.IncidentEvidence (IncidentID,CapturedAt)')


def config():
    return json.loads(rows('SELECT Payload FROM Argus.Configuration WHERE Name = ?',('collector',))[0][0])


def collection_status(name, payload=None):
    key='status:'+name
    found=rows('SELECT Payload FROM Argus.Configuration WHERE Name = ?',(key,))
    if payload is None:
        return json.loads(found[0][0]) if found else {'status':'not collected'}
    if found:
        sql('UPDATE Argus.Configuration SET Payload = ? WHERE Name = ?',(json.dumps(payload),key))
    else:
        sql('INSERT INTO Argus.Configuration (Name,Payload) VALUES (?,?)',(key,json.dumps(payload)))


def event(kind,payload):
    if kind not in ('ActionEvent','ReportExecution'):
        raise ValueError(kind)
    sql('INSERT INTO Argus.'+kind+' (ID,CapturedAt,Payload) VALUES (?,?,?)',(str(uuid4()),time.time(),json.dumps(payload)))


def snapshot(kind,key,data,now):
    if kind not in SNAPSHOT_KINDS:
        raise ValueError(kind)
    sql('INSERT INTO Argus.'+kind+'Snapshot (ID,EntityKey,CapturedAt,Payload) VALUES (?,?,?,?)',
        (str(uuid4()),key,now,json.dumps(data,default=str)))


def incidents(limit=100):
    return [dict(json.loads(p),id=i,status=s,started_at=t,last_seen_at=l,resolved_at=r)
            for i,s,t,l,r,p in rows('SELECT TOP 100 ID,Status,StartedAt,LastSeenAt,ResolvedAt,Payload FROM Argus.Incident ORDER BY StartedAt DESC')][:limit]


def active_incidents():
    return [dict(json.loads(p),id=i,status=s,started_at=t,last_seen_at=l,resolved_at=r)
            for i,s,t,l,r,p in rows("SELECT ID,Status,StartedAt,LastSeenAt,ResolvedAt,Payload FROM Argus.Incident WHERE Status <> 'RESOLVED' ORDER BY StartedAt DESC")]


def incident(identifier):
    found=rows('SELECT Status,StartedAt,LastSeenAt,ResolvedAt,Payload FROM Argus.Incident WHERE ID = ?',(identifier,))
    if not found:
        return None
    s,t,l,r,p=found[0]
    item=dict(json.loads(p),id=identifier,status=s,started_at=t,last_seen_at=l,resolved_at=r)
    item['timeline']=[{'captured_at':t,**json.loads(p)} for t,p in rows(
        'SELECT TOP 500 CapturedAt,Payload FROM Argus.IncidentEvidence WHERE IncidentID = ? ORDER BY CapturedAt',(identifier,))]
    return item


def observe(kind,namespace,resource,value,impact,evidence,now,tz,settings):
    key=fingerprint(kind,namespace,resource)
    bucket=':'.join(map(str,time_bucket(now,tz,settings.get('bucket_minutes',15))))
    history=rows('SELECT Value FROM Argus.Observation WHERE Fingerprint = ? AND BucketKey = ? AND CapturedAt >= ? AND CapturedAt < ?',
                 (key,bucket,now-settings.get('history_days',30)*86400,now-86400))
    baseline=statistics([r[0] for r in history])
    old=rows('SELECT Payload FROM Argus.Condition WHERE Fingerprint = ?',(key,))
    state=Condition(**json.loads(old[0][0])) if old else Condition()
    decision,reasons=evaluate(state,now=now,value=value,baseline=baseline,impacted=impact,
                             persistence=settings.get('persistence_seconds',60),grace=settings.get('grace_seconds',60),
                             max_gap=settings.get('max_sample_gap_seconds',150))
    payload={'type':kind,'namespace':namespace,'resource':resource,'title':kind+' · '+resource,
             'severity':'HIGH' if impact else 'MEDIUM','confidence':baseline['confidence'],
             'reasons':reasons,'baseline':baseline,'impact':impact,'value':value}
    if decision=='OPEN':
        state.incident_id=str(uuid4())
        sql('INSERT INTO Argus.Incident (ID,Fingerprint,StartedAt,LastSeenAt,Status,Payload) VALUES (?,?,?,?,?,?)',
            (state.incident_id,key,state.first_seen,now,'OPEN',json.dumps(payload)))
    elif decision=='UPDATE':
        sql('UPDATE Argus.Incident SET LastSeenAt = ?, Payload = ? WHERE ID = ?', (now,json.dumps(payload),state.incident_id))
    elif decision=='RESOLVE':
        sql('UPDATE Argus.Incident SET ResolvedAt = ?, Status = ? WHERE ID = ?', (now,'RESOLVED',state.incident_id))
    if decision in ('OPEN','UPDATE','RESOLVE'):
        sql('INSERT INTO Argus.IncidentEvidence (ID,IncidentID,CapturedAt,Payload) VALUES (?,?,?,?)',
            (str(uuid4()),state.incident_id,now,json.dumps({'decision':decision,'reasons':reasons,'evidence':evidence},default=str)))
    if decision=='RESOLVE':
        state.incident_id=None
    if old:
        sql('UPDATE Argus.Condition SET Payload = ? WHERE Fingerprint = ?', (json.dumps(asdict(state)),key))
    else:
        sql('INSERT INTO Argus.Condition (Fingerprint,Payload) VALUES (?,?)',(key,json.dumps(asdict(state))))
    # Aggregate is queryable independently of the live resource.
    baseline_key=key+':'+bucket
    sql('DELETE FROM Argus.BehaviorBaseline WHERE Fingerprint = ?', (baseline_key,))
    sql('INSERT INTO Argus.BehaviorBaseline (Fingerprint,CapturedAt,Payload) VALUES (?,?,?)',
        (baseline_key,now,json.dumps(dict(baseline,kind=kind,namespace=namespace,resource=resource,bucket=bucket))))
    sql('INSERT INTO Argus.Observation (ID,Fingerprint,CapturedAt,BucketKey,Value) VALUES (?,?,?,?,?)',
        (str(uuid4()),key,now,bucket,value))
    return decision


def retention(now, settings=None):
    retention_days=(settings or {}).get('retention_days',{})
    for kind,days in [('Process',7),('Lock',30),('Task',30),('Database',365),('Global',365)]:
        days=max(1,int(retention_days.get(kind,days)))
        sql('DELETE FROM Argus.'+kind+'Snapshot WHERE CapturedAt < ?', (now-days*86400,))
    sql('DELETE FROM Argus.Observation WHERE CapturedAt < ?', (now-max(1,int((settings or {}).get('history_days',30)))*86400,))
    sql('DELETE FROM Argus.BehaviorBaseline WHERE CapturedAt < ?', (now-max(1,int(retention_days.get('Baseline',365)))*86400,))
    sql("DELETE FROM Argus.IncidentEvidence WHERE CapturedAt < ? AND IncidentID IN (SELECT ID FROM Argus.Incident WHERE Status = 'RESOLVED')",(now-max(1,int(retention_days.get('Evidence',90)))*86400,))
    sql("DELETE FROM Argus.Incident WHERE Status = 'RESOLVED' AND ResolvedAt < ?",(now-max(1,int(retention_days.get('Incident',365)))*86400,))
