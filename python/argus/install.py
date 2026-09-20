"""Idempotent schema and scheduler installation inside IRIS."""
import os
import secrets
from datetime import date
from argus import store
from argus.jobs import SECRET_FILE


def check(status):
    import iris
    if status!=1:
        raise RuntimeError(str(iris.system.Status.GetErrorText(status)))


def setup():
    import iris
    previous=iris.system.Process.NameSpace()
    try:
        iris.system.Process.SetNamespace('ARGUS')
        store.initialize()
        check(iris.cls('%SYSTEM.OBJ').Load('/opt/argus/src/Argus/Collector.cls','ck'))
        iris.system.Process.SetNamespace('%SYS')
        if not SECRET_FILE.exists():
            password=secrets.token_urlsafe(36)
            # Credentials generated locally, never committed or exposed to browser.
            descriptor=os.open(str(SECRET_FILE),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'w') as output:
                output.write(password)
        password=SECRET_FILE.read_text().strip()
        if not iris.cls('Security.Users').Exists('ArgusCollector'):
            check(iris.cls('Security.Users').Create('ArgusCollector','%Operator,%DB_ARGUS',password,
                  'Argus scheduled collector','ARGUS','','',0,1,'Argus local collection service'))
        iris.system.Process.SetNamespace('ARGUS')
        for (table,) in store.rows("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Argus'"):
            if str(table).isalnum():
                store.sql('GRANT SELECT, INSERT, UPDATE, DELETE ON Argus.'+table+' TO ArgusCollector')
        iris.system.Process.SetNamespace('%SYS')
        task_ids=store.rows('SELECT ID FROM %SYS.Task WHERE Name = ?',('ArgusCollection',))
        if not task_ids:
            task=iris.cls('%SYS.Task')._New()
            task.Name='ArgusCollection';task.NameSpace='ARGUS';task.TaskClass='Argus.Collector'
            task.RunAsUser='ArgusCollector';task.Description='Collect bounded Argus operational evidence'
            task.TimePeriod=0;task.TimePeriodEvery=1;task.DailyFrequency=1
            task.DailyFrequencyTime=0;task.DailyIncrement=1;task.DailyStartTime=0;task.DailyEndTime=86399
            task.StartDate=(date.today()-date(1840,12,31)).days
            check(task._Save())
        print('ARGUS_INSTALL_OK')
    finally:
        iris.system.Process.SetNamespace(previous)
