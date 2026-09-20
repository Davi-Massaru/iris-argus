"""Flask runs exclusively behind %SYS.Python.WSGI in namespace ARGUS."""
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, render_template, request, g, url_for, redirect, abort
from itsdangerous import TimestampSigner, BadSignature
from argus import __version__
from argus.sysadmin import SysAdminClient, SysAdminError
from argus.catalog import SECTIONS, NAV

ROOT = Path(__file__).resolve().parents[2]


def create_app(client_factory=SysAdminClient):
    app = Flask(__name__, template_folder=str(ROOT/'web/templates'), static_folder=str(ROOT/'web/static'))
    app.config.update(MAX_CONTENT_LENGTH=64*1024)
    from argus.history import bp as history
    app.register_blueprint(history)
    from argus.storage import bp as storage
    app.register_blueprint(storage)
    from argus.intelligence import bp as intelligence
    app.register_blueprint(intelligence)
    from argus.reports import bp as reports
    app.register_blueprint(reports)

    @app.template_filter('utc')
    def utc(value):
        return datetime.fromtimestamp(float(value),timezone.utc).isoformat(timespec='seconds') if value else 'Not resolved'

    @app.before_request
    def authenticate():
        if request.endpoint == 'static':
            return
        authorization = request.headers.get('Authorization', '')
        if not authorization.startswith(('Basic ', 'Bearer ')):
            return ('IRIS credentials required', 401, {'WWW-Authenticate': 'Basic realm="Argus IRIS"'})
        g.client = client_factory(authorization)
        g.identity = g.client.get('/info')

    @app.teardown_request
    def close_client(_error):
        if getattr(g, 'client', None):
            g.client.close()

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; form-action 'self'"
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.context_processor
    def context():
        from argus.llm import provider_name, ExplanationError
        try:
            ai_provider=provider_name()
        except ExplanationError:
            ai_provider='unavailable'
        return dict(nav=NAV, ai_provider=ai_provider, username=getattr(g, 'identity', {}).get('username', ''),
                    captured=datetime.now(timezone.utc).isoformat(timespec='seconds'))

    def page(title, section='', **kwargs):
        if 'details' in kwargs and not isinstance(kwargs['details'], dict):
            kwargs['details'] = {'Measurements': kwargs['details']}
        return render_template('page.html', title=title, section=section, **kwargs)

    @app.errorhandler(SysAdminError)
    def management_error(error):
        response = app.make_response((page(str(error), error=str(error)), error.status if error.status < 600 else 502))
        if error.status == 401:
            response.headers['WWW-Authenticate'] = 'Basic realm="Argus IRIS"'
        return response

    def signer():
        # User-bound, expiring confirmation token; credentials never persisted or rendered.
        return TimestampSigner(request.headers['Authorization'], salt='argus-human-confirmation')

    def token(target):
        return signer().sign(target).decode()

    def confirm(target):
        if request.form.get('confirm') != 'yes':
            abort(400, 'Explicit confirmation required')
        try:
            if signer().unsign(request.form.get('token',''), max_age=300).decode() != target:
                abort(400)
        except BadSignature:
            abort(400, 'Confirmation expired; inspect the target again')
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            abort(403)

    @app.get('/health')
    def health():
        import iris
        return jsonify(status='ok', version=__version__, runtime='IRIS Embedded Python',
                       iris=iris.system.Version.GetVersion(), namespace=iris.system.Process.NameSpace())

    @app.get('/')
    def index():
        details = g.client.get('/v2/monitor/dashboard/main')
        from argus import store
        permitted=g.identity.get('privileges',{}).get('Operate',{}).get('use')
        incidents=store.incidents() if permitted else []
        active=store.active_incidents() if permitted else []
        latest=store.rows('SELECT MAX(CapturedAt) FROM Argus.ProcessSnapshot') if permitted else []
        last_capture=latest[0][0] if latest else None
        stale=last_capture in (None,'') or datetime.now(timezone.utc).timestamp()-float(last_capture)>150
        return render_template('overview.html',title='What needs attention now?',section='overview',
                               details=details,active=active,recent=incidents[:5],permitted=permitted,
                               last_capture=last_capture,stale=stale)

    def table(title, section, rows, columns, **kwargs):
        rows = [dict(row) if isinstance(row,dict) else {'Name':row} for row in rows]
        for row in rows:
            name = row.get('Name')
            if section == 'applications':
                row['_url'] = url_for('detail',kind='application',name=name)
            elif section == 'tasks':
                row['_url'] = url_for('detail',kind='task',id=row.get('Id'))
            elif section == 'processes':
                row['_url'] = url_for('process_detail',pid=row['Pid'])
            elif section == 'locks':
                row['_url'] = url_for('lock_detail',id=row.get('DeleteID',''))
            elif section == 'wallet':
                row['_url'] = url_for('section_view',section='secrets',collection=name)
            elif section in ('namespaces','databases'):
                row['_url'] = url_for('detail',kind=section[:-1] if section=='databases' else 'namespace',name=name)
        query=request.args.get('q','').casefold()
        rows=[r for r in rows if query in str(r).casefold()]
        try:
            offset=max(0,int(request.args.get('page',0)))*100
        except ValueError:
            abort(400)
        args=request.args.to_dict();args['page']=offset//100+1
        from urllib.parse import urlencode
        next_page=request.path+'?'+urlencode(args) if len(rows)>offset+100 else None
        return page(title,section,rows=rows[offset:offset+100],columns=columns,total=len(rows),
                    filterable=True,next_page=next_page,**kwargs)

    @app.get('/view/<section>')
    def section_view(section):
        if section in SECTIONS:
            title,path,columns=SECTIONS[section]
            params={'maxRows':100} if section=='task-history' else {}
            return table(title,section,g.client.get(path,**params),columns)
        if section=='system':
            return page('System',section,details=g.client.get('/v2/monitor/dashboard/system-resources'),
                        links=[('Processes',url_for('section_view',section='processes')),('Databases',url_for('section_view',section='databases'))])
        if section=='sql-privileges':
            fields=[('grantee','User or role'),('namespace','Namespace')]
            if not all(request.args.get(k) for k,_ in fields):
                return page('SQL privileges',section,fields=fields)
            return table('SQL privileges',section,g.client.get('/v2/security/sql-privileges',
                         grantee=request.args['grantee'],namespace=request.args['namespace'],maxRows=100),
                         ['Type','Object','Action','GrantedBy','GrantedVia'],fields=fields)
        if section=='secrets':
            collection=request.args.get('collection')
            if not collection:
                return page('Secrets metadata',section,fields=[('collection','Collection')])
            rows=g.client.get('/v2/wallet/secrets',collection=collection,maxRows=100)
            # Metadata endpoint only. Never call /wallet/secret from a browser route.
            safe=[{k:r[k] for k in ('Name','Type') if k in r} for r in rows]
            return table('Secrets metadata',section,safe,['Name','Type'])
        if section=='logs':
            return page('Logs & error investigation',section,notice='Select a verified source. Each source retains its own timestamp and privilege requirements.',
                        links=[('Audit records',url_for('section_view',section='audit')),('Task execution history',url_for('section_view',section='task-history'))])
        if section=='audit':
            task_id=request.args.get('id')
            if not task_id:
                pending=g.client.request('POST','/v2/security/audit/records',params={'maxRows':100})
                return redirect(url_for('section_view',section='audit',id=pending['pending_id']))
            result=g.client.get('/v2/async-result',id=task_id)
            if result.get('State')=='Finished':
                return table('Audit records',section,result.get('Result',[]),['UTCTimeStamp','Event','Username','Pid','Description'])
            return page('Audit query',section,details=result,notice='Refresh to check the bounded asynchronous query. No new query is started on refresh.')
        abort(404)

    @app.get('/detail/<kind>')
    def detail(kind):
        targets={'application':('/v2/web-app','name'),'task':('/v2/task','id'),
                 'database':('/v2/database','name'),'namespace':('/v2/namespace','name')}
        if kind not in targets:
            abort(404)
        path,key=targets[kind]
        value=request.args.get(key)
        if not value:
            abort(400)
        data=g.client.get(path,**{key:value})
        kwargs={}
        if kind=='application':
            kwargs.update(edit_description=data.get('Description',''),action_token=token('application:'+value))
        if kind=='task':
            kwargs.update(task_actions=True,action_token=token('task:'+value))
        if kind=='namespace':
            from argus.native import global_mappings
            data['Global mappings']=global_mappings(value)
            kwargs['links']=[('Resolve a global',url_for('storage.global_view',namespace=value))]
        if kind=='database':
            physical=next((d for d in g.client.get('/v2/database-dirs',maxRows=100) if d['Directory']==data.get('Directory')),None)
            data['Physical status']=physical or 'Unavailable'
            kwargs['links']=[('Growth history',url_for('storage.growth_view'))]
        return page(kind.title()+' · '+value,details=data,**kwargs)

    @app.get('/process/<int:pid>')
    def process_detail(pid):
        data=g.client.get('/v2/process',id=pid)
        keys=['Pid','UserName','NameSpace','State','StartTimeUTC','CurrentLineAndRoutine',
              'CurrentSrcLine','LastGlobalReference','GlobalReferences','GlobalUpdates',
              'PrivateGlobalBlockCount','InTransaction','Routine','CPUTime']
        details={key:data.get(key) for key in keys}
        locks=[r for r in g.client.get('/v2/locks') if str(r.get('Pid'))==str(pid) and not r.get('RemoteOwner')]
        links=[(r['Reference'],url_for('lock_detail',id=r['DeleteID'])) for r in locks]
        ns=data.get('NameSpace')
        if ns:
            links.append(('Namespace '+ns,url_for('detail',kind='namespace',name=ns)))
            global_name=data.get('LastGlobalReference','').split('(')[0]
            if global_name:
                links.append(('Last global',url_for('storage.global_view',namespace=ns,**{'global':global_name})))
        links.append(('Preserved incidents',url_for('history.incidents')))
        return page('Process '+str(pid),'processes',details=details,links=links,
                    notice='Deep inspection captured on demand. InTransaction is a journal offset, not transaction age. Unavailable fields are not inferred.')

    @app.get('/lock')
    def lock_detail():
        target=request.args.get('id','')
        lock=next((r for r in g.client.get('/v2/locks') if r.get('DeleteID')==target),None)
        if lock is None:
            abort(404,'Lock no longer exists')
        links=[]
        if lock.get('Pid') and not lock.get('RemoteOwner'):
            links.append(('Owner process '+str(lock['Pid']),url_for('process_detail',pid=int(lock['Pid']))))
        from argus.native import lock_waiters, related_waiters
        waiters=related_waiters(lock,lock_waiters())
        lock['Verified waiting PIDs']=waiters
        links.extend(('Waiting process '+str(pid),url_for('process_detail',pid=pid)) for pid in waiters)
        links.append(('Historical incidents',url_for('history.incidents')))
        if lock.get('Pid') and not lock.get('RemoteOwner'):
            process=next((p for p in g.client.get('/v2/processes') if str(p['Pid'])==str(lock['Pid'])),{})
            if process.get('Nspace'):
                links.append(('Global data location',url_for('storage.global_view',namespace=process['Nspace'],**{'global':lock['Reference'].split('(')[0]})))
        return page('Lock investigator','locks',details=lock,links=links,
                    notice='Owners come from SysAdmin; waiter PIDs come from native %SYS.LockQuery.Detail, matched by physical reference and owner. Transaction age remains unavailable.')

    @app.post('/actions/application-description')
    def edit_application():
        name=request.form.get('name','')
        confirm('application:'+name)
        value=request.form.get('description','')
        if len(value)>512:
            abort(400)
        g.client.get('/v2/web-app',name=name)
        from argus import store
        store.event('ActionEvent',{'action':'application-description','target':name,'stage':'requested','user':g.identity['username']})
        g.client.request('PUT','/v2/web-app',params={'name':name},data={'Description':value})
        observed=g.client.get('/v2/web-app',name=name)
        if observed.get('Description')!=value:
            raise SysAdminError(502,'Description update could not be verified')
        store.event('ActionEvent',{'action':'application-description','target':name,'stage':'verified','user':g.identity['username']})
        return page('Application updated',details={'Target':name,'Description':value,'Verification':'Read-back matched'})

    @app.post('/actions/task/<action>')
    def task_action(action):
        if action not in ('run','suspend','resume'):
            abort(404)
        target=request.form.get('id','')
        confirm('task:'+target)
        before=g.client.get('/v2/task',id=target)
        from argus import store
        store.event('ActionEvent',{'action':'task-'+action,'target':target,'stage':'requested','user':g.identity['username']})
        data={'RunNow':True} if action=='run' else ({'LeaveInQueue':True} if action=='suspend' else None)
        g.client.request('POST','/v2/task/'+action,params={'id':target},data=data)
        after=g.client.get('/v2/task',id=target)
        store.event('ActionEvent',{'action':'task-'+action,'target':target,'stage':'accepted','user':g.identity['username']})
        return page('Task request accepted',details=after,notice='Target '+before.get('Name',target)+': '+action+' requested. The current task configuration was read back; execution completion is shown in task history.')

    return app


app=create_app()
