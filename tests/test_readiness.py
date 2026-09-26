import os
import time

from scripts import readiness


def test_requires_both_startup_and_fresh_worker_heartbeat(tmp_path, monkeypatch):
    original = readiness.Path
    monkeypatch.setattr(readiness, 'Path', lambda path: original(tmp_path / original(path).name))
    assert not readiness.ready()
    (tmp_path / 'agentic-ready').touch()
    assert not readiness.ready()
    heartbeat = tmp_path / 'agentic-worker-heartbeat'
    heartbeat.touch()
    assert readiness.ready()
    old = time.time() - 60
    os.utime(heartbeat, (old, old))
    assert not readiness.ready()
