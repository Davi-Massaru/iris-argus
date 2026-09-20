"""Read-only runtime checks plus one explicitly simulated explanation."""
import os
import re
import requests

base=os.getenv('ARGUS_TEST_URL','http://127.0.0.1:52773/argus')
session=requests.Session()
session.auth=(os.getenv('ARGUS_TEST_USER','_SYSTEM'),os.getenv('ARGUS_TEST_PASSWORD','SYS'))
paths=['/','/health','/view/applications','/view/users','/view/roles','/view/resources',
       '/view/wallet','/view/tasks','/view/system','/view/logs','/view/processes','/view/locks',
       '/incidents','/behavior','/task-snapshots','/storage/growth','/storage/iristemp','/detail/namespace?name=ARGUS',
       '/storage/global?namespace=ARGUS&global=ArgusDemo','/reports']
paths += ['/reports/'+kind+'?format='+fmt for kind in ('locks','growth','behavior') for fmt in ('html','json','csv')]
for path in paths:
    response=session.get(base+path,timeout=30)
    assert response.status_code==200,(path,response.status_code)
    print('PASS',path)
assert session.get(base+'/health',timeout=30).json()['runtime']=='IRIS Embedded Python'
locks=session.get(base+'/reports/locks?format=json',timeout=30).json()['rows']
if locks:
    identifier=locks[0]['id']
    for fmt in ('html','json','csv'):
        assert session.get(base+'/report/incident/'+identifier+'?format='+fmt,timeout=30).status_code==200
    form=session.get(base+'/explain/'+identifier,timeout=30)
    # Hard stop before submitting if a real provider is configured.
    assert 'Simulated mode.' in form.text,'Refusing live LLM validation'
    token=re.search(r'name="token" value="([^"]+)"',form.text).group(1)
    response=session.post(base+'/explain/'+identifier,data={'token':token,'confirm':'yes'},timeout=30)
    assert response.status_code==200 and 'Simulated explanation' in response.text
    print('PASS preserved incident exports and simulated explanation')
print('ARGUS_HTTP_SMOKE_OK')
