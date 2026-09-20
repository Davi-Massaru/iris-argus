from argus.domain import *
import pytest

def test_statistics():
    b=statistics(range(1,101))
    assert b['median']==50.5 and b['p90']==pytest.approx(90.1) and b['p95']==pytest.approx(95.05)
    assert b['confidence']=='HIGH'

def test_confidence():
    assert [statistics(range(n))['confidence'] for n in [0,4,5,10,11,20,21]]==['INSUFFICIENT','INSUFFICIENT','LOW','LOW','MEDIUM','MEDIUM','HIGH']

def test_bucket_timezone():
    t=datetime(2026,9,19,2,7,tzinfo=timezone.utc).timestamp()
    assert time_bucket(t,'America/Sao_Paulo')==(4,92)

def test_noon_normal_and_night_abnormal():
    assert classify(544,{'sample_count':26,'p95':621})=='NORMAL'
    assert classify(481,{'sample_count':26,'p95':31})=='ANOMALY'
    assert classify(999,statistics([]))=='LEARNING'

def test_persistence_dedup_and_resolution():
    s=Condition();b={'sample_count':26,'p95':31}
    def tick(t,value,impact=0):
        return evaluate(s,now=t,value=value,baseline=b,impacted=impact)[0]
    assert tick(0,481)=='OBSERVATION'
    assert tick(59,481)=='OBSERVATION'
    assert tick(60,481)=='OPEN'
    s.incident_id='one'
    assert tick(90,481)=='UPDATE'
    assert tick(100,0)=='OBSERVATION'
    assert tick(159,0)=='OBSERVATION'
    assert tick(160,0)=='RESOLVE'

def test_normal_volume_impact():
    s=Condition(); b={'sample_count':26,'p95':621}
    evaluate(s,now=0,value=510,baseline=b,impacted=23)
    decision,reasons=evaluate(s,now=108,value=510,baseline=b,impacted=23)
    assert decision=='OPEN' and '23 verified' in ' '.join(reasons)

def test_gap_never_counts_as_persistence_or_recovery():
    s=Condition(0,None,0,'incident')
    assert evaluate(s,now=500,value=0,baseline=statistics([]))[0]=='OBSERVATION'
    assert s.absent_since==500

def test_fingerprint_and_growth():
    assert fingerprint('lock','A','x')==fingerprint('lock','A','x')
    assert fingerprint('lock','A','x')!=fingerprint('lock','B','x')
    assert growth([(0,10),(86400,20)],86400,1)['change_mb']==10
    assert growth([(0,10),(20,20)],20,1) is None
