"""Deterministic temporal statistics and incident state transitions. No IO or AI."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from statistics import mean, median, pstdev
from zoneinfo import ZoneInfo
import json
import math


def fingerprint(kind, namespace, resource, pid=None):
    return sha256(json.dumps([kind,namespace,resource,pid],separators=(',',':')).encode()).hexdigest()


def time_bucket(timestamp, tz='UTC', minutes=15):
    if minutes < 1 or 1440 % minutes:
        raise ValueError('Bucket must divide a day')
    local=datetime.fromtimestamp(timestamp,timezone.utc).astimezone(ZoneInfo(tz))
    return local.weekday(), (local.hour*60+local.minute)//minutes


def statistics(values):
    values=sorted(float(x) for x in values if x is not None and math.isfinite(float(x)))
    n=len(values)
    confidence='INSUFFICIENT' if n<5 else 'LOW' if n<=10 else 'MEDIUM' if n<=20 else 'HIGH'
    if not n:
        return {'sample_count':0,'confidence':confidence}
    def percentile(q):
        position=(n-1)*q; lo=int(position); hi=min(lo+1,n-1)
        return values[lo]+(values[hi]-values[lo])*(position-lo)
    return dict(sample_count=n,minimum=values[0],maximum=values[-1],average=mean(values),
                median=median(values),p90=percentile(.9),p95=percentile(.95),
                standard_deviation=pstdev(values),confidence=confidence)


def classify(value, baseline):
    if baseline.get('sample_count',0)<5:
        return 'LEARNING'
    return 'ANOMALY' if value>baseline['p95'] else 'NORMAL'


@dataclass
class Condition:
    first_seen: float | None = None
    absent_since: float | None = None
    last_sample: float | None = None
    incident_id: str | None = None


def evaluate(state, *, now, value, baseline, impacted=0, correlated=0, critical=False,
             persistence=60, grace=60, max_gap=150):
    """Return decision/reasons. Missing polls cannot count as persistence or recovery."""
    if state.last_sample is not None and now<=state.last_sample:
        return 'UNCHANGED',[]
    if state.last_sample is not None and now-state.last_sample>max_gap:
        state.first_seen=None; state.absent_since=None
    state.last_sample=now
    classification=classify(value,baseline)
    active=classification=='ANOMALY' or impacted>0 or critical or correlated>=2
    if active:
        state.absent_since=None
        if state.first_seen is None:
            state.first_seen=now
        age=now-state.first_seen
        reasons=[]
        if classification=='ANOMALY':
            reasons.append(f'Observed {value:g}; historical p95 {baseline["p95"]:g} for this weekday/time bucket')
        if impacted:
            reasons.append(f'{impacted} verified affected processes')
        if correlated>=2:
            reasons.append(f'{correlated} correlated signals')
        if critical:
            reasons.append('Verified deterministic critical condition')
        if critical or age>=persistence:
            reasons.append(f'Condition observed persistently for {age:g} seconds')
            return ('UPDATE' if state.incident_id else 'OPEN'),reasons
        return 'OBSERVATION',reasons
    state.first_seen=None
    if state.incident_id:
        if state.absent_since is None:
            state.absent_since=now
        if now-state.absent_since>=grace:
            return 'RESOLVE',[f'Condition absent for {now-state.absent_since:g} seconds']
    return 'OBSERVATION',[]


def growth(samples, now, days):
    """Use actual timestamps; never label a short interval as a full day."""
    ordered=sorted((t,float(v)) for t,v in samples if t<=now)
    prior=[row for row in ordered if row[0]<=now-days*86400]
    if not ordered or not prior:
        return None
    start=prior[-1];end=ordered[-1];elapsed=end[0]-start[0]
    return {'change_mb':end[1]-start[1],'elapsed_seconds':elapsed,
            'rate_mb_day':(end[1]-start[1])*86400/elapsed if elapsed else None}
