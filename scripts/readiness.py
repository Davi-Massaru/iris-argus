"""No database login needed: startup marker and recent worker SQL heartbeat."""
import time
from pathlib import Path


def ready():
    try:
        return (Path("/tmp/agentic-ready").exists()
                and 0 <= time.time() - Path("/tmp/agentic-worker-heartbeat").stat().st_mtime < 20)
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(0 if ready() else 1)
