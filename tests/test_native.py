from argus.native import related_waiters


def test_waiter_requires_physical_reference_and_owner():
    lock={'Pid':42,'Directory':'/db/','Reference':'^G(1)'}
    row={'Owner':'42','FullReference':'^["^^/db/"]G(1)','WaiterPID':'43','WaiterType':'E','RemoteOwner':'0'}
    assert related_waiters(lock,[row])==[43]
    assert related_waiters(dict(lock,Directory='/other/'),[row])==[]
    assert related_waiters(dict(lock,Pid=44),[row])==[]
    assert related_waiters(dict(lock,RemoteOwner=True),[row])==[]
