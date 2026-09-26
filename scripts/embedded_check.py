from pathlib import Path

import iris

from app.tools.importer import load_contract
from app.wsgi import application


version = str(iris.system.Version.GetVersion())
row = next(iter(iris.sql.exec("SELECT 1 AS Value")))
contract = load_contract(Path("/opt/agentic/specification/mainspec_v2.json"))
assert int(row[0]) == 1
assert contract.operations
assert application is not None
print(f"AGENTIC_EMBEDDED_PYTHON_OK {version} operations={len(contract.operations)}")
