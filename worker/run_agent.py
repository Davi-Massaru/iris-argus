import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import iris
from app.mvp.repository import AgentRepository
from app.mvp.runtime import execute
from app.mvp.gateway import ToolError

iris.system.Process.SetNamespace('AGENTIC')
repository = AgentRepository()
identifier = sys.argv[1]
try:
    execute(identifier, repository)
except Exception as error:
    # Provider exceptions can contain credentials/URLs. Persist only safe codes.
    code = str(error) if isinstance(error, ToolError) else type(error).__name__
    if getattr(error, 'status_code', None) == 404:
        code = 'MODEL_NOT_AVAILABLE'
    elif type(error).__name__ in ('ConnectError', 'ConnectTimeout'):
        code = 'MODEL_UNAVAILABLE'
    elif type(error).__name__ in ('ReadTimeout', 'TimeoutException'):
        code = 'MODEL_TIMEOUT'
    repository.finish(identifier, 'FAILED', error=code[:100])
