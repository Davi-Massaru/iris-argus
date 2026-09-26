from __future__ import annotations

import signal
import time
import subprocess
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STOP_FILE = Path("/tmp/agentic-worker-stop")
HEARTBEAT = Path("/tmp/agentic-worker-heartbeat")
running = True


def stop(*_args):
    global running
    running = False


def connectivity_probe() -> str:
    import iris

    iris.system.Process.SetNamespace("AGENTIC")
    row = next(
        iter(
            iris.sql.exec(
                "SELECT COUNT(*) FROM Agentic.AI_SCHEMA_MIGRATION WHERE Outcome = ?", "SUCCEEDED"
            )
        )
    )
    if int(row[0]) < 1:
        raise RuntimeError("Schema is not ready")
    return f"worker_sql_ok migrations={int(row[0])}"


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(connectivity_probe(), flush=True)
    from app.mvp.repository import AgentRepository

    repository = AgentRepository()
    repository.recover()
    child = None
    run_id = None
    started = 0
    try:
        while running and not STOP_FILE.exists():
            connectivity_probe()
            HEARTBEAT.touch()
            if child is not None:
                if time.monotonic() - started > 240:
                    child.kill()
                    child.wait()
                    repository.finish(run_id, "FAILED", error="RUN_TIMEOUT")
                if child.poll() is not None:
                    if repository.get_run(run_id)["state"] == "RUNNING":
                        repository.finish(run_id, "FAILED", error="RUNNER_EXITED")
                    child = None
            repository.schedule()
            if child is None:
                run_id = repository.claim()
                if run_id:
                    child = subprocess.Popen(
                        ["/usr/irissys/bin/irispython", "/opt/agentic/worker/run_agent.py", run_id],
                        env=os.environ.copy(),
                        stdin=subprocess.DEVNULL,
                    )
                    started = time.monotonic()
            time.sleep(2)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            repository.finish(run_id, "FAILED", error="WORKER_STOPPED")
    HEARTBEAT.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
