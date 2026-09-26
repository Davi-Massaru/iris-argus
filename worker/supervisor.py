"""Bounded restart supervision for the Embedded Python worker."""
import signal
import subprocess
import time
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HEARTBEAT = Path("/tmp/agentic-worker-heartbeat")
child = None
running = True


def worker_environment():
    credential = json.loads(Path('/usr/irissys/mgr/agentic/worker-credential.json').read_text())
    return dict(os.environ, IRISUSERNAME=credential['username'],
                IRISPASSWORD=credential['password'], IRISNAMESPACE='AGENTIC')


def stop(*_args):
    global running
    running = False
    if child is not None and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)


def main():
    global child
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    failures = 0
    while running and failures < 5:
        HEARTBEAT.unlink(missing_ok=True)
        child = subprocess.Popen(["/usr/irissys/bin/irispython", str(ROOT / "main.py")],
                                 env=worker_environment(), stdin=subprocess.DEVNULL,
                                 start_new_session=True)
        result = child.wait()
        # A crashed worker may have left a model runner behind. Fence it before
        # recovery releases any durable agent execution slot.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        HEARTBEAT.unlink(missing_ok=True)
        if not running or result == 0:
            break
        failures += 1
        print(f"Worker exited; restart attempt {failures}/5", flush=True)
        time.sleep(min(2 ** failures, 30))
    if running and failures == 5:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
