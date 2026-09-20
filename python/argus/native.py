"""Verified native enrichment. Called only after SysAdmin authorizes the view."""
import re


def lock_waiters():
    import iris
    result=iris.cls('%ResultSet')._New('%SYS.LockQuery:Detail')
    status=result.Execute()
    if status!=1:
        raise RuntimeError('Lock detail query unavailable')
    rows=[]
    while result._Next():
        rows.append({k:str(result.Get(k)) for k in
                     ['Owner','FullReference','WaiterPID','WaiterType','RemoteOwner']})
    return rows


def related_waiters(lock, detail_rows):
    if lock.get('RemoteOwner'):
        return []
    reference='^["^^'+lock['Directory']+'"]'+lock['Reference'].lstrip('^')
    result=set()
    for row in detail_rows:
        if row['RemoteOwner']=='0' and row['FullReference']==reference and str(lock['Pid']) in row['Owner'].split(','):
            result.update(int(pid) for pid in row['WaiterPID'].split(',') if pid.isdecimal())
    return sorted(result)


def resolve_global(namespace, name):
    import iris
    # Root globals only; avoid silently misrepresenting subscript mappings.
    if not re.fullmatch(r'\^?[%A-Za-z][\w.]*',name):
        raise ValueError('Enter a root global name without subscripts')
    dest=str(iris.cls('%SYS.Namespace').GetGlobalDest(namespace,name.lstrip('^')))
    system,_,directory=dest.partition('^')
    return {'Namespace':namespace,'Global':'^'+name.lstrip('^'),'System':system,
            'Directory':directory,'Resolution':'Root mapping; subscript mappings may differ'}


def global_mappings(namespace):
    import iris
    old=iris.system.Process.NameSpace()
    try:
        iris.system.Process.SetNamespace('%SYS')
        query=iris.cls('%ResultSet')._New('Config.MapGlobals:List')
        iris.check_status(query.Execute(namespace))
        result=[]
        while query._Next():
            result.append({k:str(query.Get(k)) for k in ['Name','Global','Subscript','Database','LockDatabase']})
        return result
    finally:
        iris.system.Process.SetNamespace(old)


def estimate_global(namespace,name):
    import iris
    resolved=resolve_global(namespace,name)
    if resolved['System']:
        raise ValueError('Remote global sizing is not supported in Community scope')
    allocated=iris.ref(0); used=iris.ref(0)
    iris.check_status(iris.cls('%Library.GlobalEdit').GetGlobalSize(
        resolved['Directory'],name.lstrip('^'),allocated,used,2))
    return dict(resolved,allocated_mb=float(allocated.value),used_mb=float(used.value),measurement='stochastic estimate (fast=2)')
