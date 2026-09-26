from __future__ import annotations

import hashlib
import json
import re
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.mvp.catalog import catalog
from app.repositories.iris_repository import _rows, _sql
from app.tools.importer import load_contract


ROOT = Path("/opt/agentic")
CSRF_KEY = Path("/usr/irissys/mgr/agentic/csrf.key")
WORKER_CREDENTIAL = CSRF_KEY.with_name("worker-credential.json")


def _configure_worker():
    import iris
    if not WORKER_CREDENTIAL.exists():
        descriptor = os.open(str(WORKER_CREDENTIAL), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump({"username": "AgenticWorker", "password": secrets.token_urlsafe(18)}, output)
    credential = json.loads(WORKER_CREDENTIAL.read_text())
    rotate = len(credential["password"]) > 24
    if rotate:
        credential["password"] = secrets.token_urlsafe(18)
    previous = iris.system.Process.NameSpace()
    try:
        iris.system.Process.SetNamespace("%SYS")
        user_ref = iris.ref(None)
        exists = iris.cls("Security.Users").Exists(credential["username"], user_ref)
        if rotate and exists:
            user = user_ref.value
            user.PasswordExternal = credential["password"]
            if user._Save() != 1:
                raise RuntimeError("Worker credential migration failed")
        if not exists:
            status = iris.cls("Security.Users").Create(
                credential["username"], "%DB_AGENTIC", credential["password"],
                "Agentic foundation worker", "AGENTIC", "", "", 0, 1,
                "Restricted worker SQL connectivity identity")
            if status != 1:
                raise RuntimeError("Worker identity creation failed")
        if rotate:
            with WORKER_CREDENTIAL.open("w") as output:
                json.dump(credential, output)
    finally:
        iris.system.Process.SetNamespace(previous)
    # Static trusted deployment DDL: no caller-selected identity/table.
    _sql("GRANT SELECT ON Agentic.AI_SCHEMA_MIGRATION TO AgenticWorker")
    _sql("GRANT SELECT ON Agentic.AI_TOOL_VERSION TO AgenticWorker")
    for table in ('MVP_AGENT', 'MVP_RUN', 'MVP_CALL'):
        _sql(f"GRANT SELECT,INSERT,UPDATE ON Agentic.{table} TO AgenticWorker")


def _configure_mvp_security():
    import iris
    previous = iris.system.Process.NameSpace()
    try:
        iris.system.Process.SetNamespace('%SYS')
        for name, resource in [('AgenticViewer', '%DB_AGENTIC:R'),
                               ('AgenticAgentDesigner', '%DB_AGENTIC:RW'),
                               ('AgenticOperator', '%DB_AGENTIC:RW'),
                               ('AgenticDBAApprover', '%DB_AGENTIC:RW'),
                               ('AgenticSysAdminReader', '%Admin_Operate:U')]:
            if not iris.cls('Security.Roles').Exists(name, iris.ref(None)):
                status = iris.cls('Security.Roles').Create(name, 'Agentic MVP role', resource, '')
                if status != 1:
                    raise RuntimeError('Cannot create MVP role')
        path = CSRF_KEY.with_name('sysadmin-credential.json')
        if not path.exists():
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as output:
                json.dump({'username': 'AgenticSysAdmin', 'password': secrets.token_urlsafe(18)}, output)
        credential = json.loads(path.read_text())
        if not iris.cls('Security.Users').Exists(credential['username'], iris.ref(None)):
            status = iris.cls('Security.Users').Create(credential['username'], 'AgenticSysAdminReader',
                credential['password'], 'MVP SysAdmin gateway identity', '%SYS', '', '', 0, 1)
            if status != 1:
                raise RuntimeError('Cannot create SysAdmin identity')
    finally:
        iris.system.Process.SetNamespace(previous)
    for role in ('AgenticViewer', 'AgenticAgentDesigner', 'AgenticOperator'):
        for table in ('MVP_AGENT', 'MVP_RUN', 'MVP_CALL'):
            privileges = 'SELECT' if role == 'AgenticViewer' else 'SELECT,INSERT,UPDATE'
            _sql(f'GRANT {privileges} ON Agentic.{table} TO {role}')
    for role in ('AgenticViewer', 'AgenticAgentDesigner', 'AgenticOperator', 'AgenticDBAApprover'):
        _sql(f'GRANT SELECT ON Agentic.AI_TOOL_VERSION TO {role}')
    _sql('GRANT SELECT,UPDATE ON Agentic.AI_TOOL_VERSION TO AgenticDBAApprover')
    _sql('GRANT SELECT,INSERT ON Agentic.AI_TOOL_POLICY_OVERRIDE TO AgenticDBAApprover')


def _split_statements(text: str) -> list[str]:
    return [statement.strip() for statement in text.split(";") if statement.strip()]


def _apply_statement(statement: str) -> None:
    table_match = re.match(r"CREATE\s+TABLE\s+Agentic\.([A-Za-z0-9_]+)", statement, re.IGNORECASE)
    if table_match and _rows(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
        ("Agentic", table_match.group(1)),
    ):
        return
    _sql(statement)


def _migrate() -> None:
    if not _rows("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?", ("Agentic", "AI_SCHEMA_MIGRATION")):
        _sql(
            "CREATE TABLE Agentic.AI_SCHEMA_MIGRATION (Version VARCHAR(50) PRIMARY KEY, Checksum VARCHAR(64), AppliedAt VARCHAR(40), DeploymentIdentity VARCHAR(100), Outcome VARCHAR(20))"
        )
    for migration in sorted((ROOT / "migrations").glob("*.sql")):
        checksum = hashlib.sha256(migration.read_bytes()).hexdigest()
        found = _rows("SELECT Checksum FROM Agentic.AI_SCHEMA_MIGRATION WHERE Version = ?", (migration.name,))
        if found:
            if found[0][0] != checksum:
                raise RuntimeError(f"Migration checksum changed: {migration.name}")
            continue
        for statement in _split_statements(migration.read_text(encoding="utf-8")):
            _apply_statement(statement)
        _sql(
            "INSERT INTO Agentic.AI_SCHEMA_MIGRATION (Version,Checksum,AppliedAt,DeploymentIdentity,Outcome) VALUES (?,?,?,?,?)",
            (migration.name, checksum, datetime.now(timezone.utc).isoformat(), "docker-build", "SUCCEEDED"),
        )


def _import_contract() -> int:
    contract = load_contract(ROOT / "specification" / "mainspec_v2.json")
    for operation in contract.operations:
        if not _rows("SELECT ID FROM Agentic.AI_TOOL WHERE StableKey = ?", (operation.stable_key,)):
            _sql(
                "INSERT INTO Agentic.AI_TOOL (ID,StableKey,Source,CreatedAt) VALUES (?,?,?,?)",
                (str(uuid4()), operation.stable_key, "mainspec_v2.json", datetime.now(timezone.utc).isoformat()),
            )
        if not _rows("SELECT ID FROM Agentic.AI_TOOL_VERSION WHERE StableKey = ? AND ContractHash = ?", (operation.stable_key, contract.source_hash)):
            _sql(
                "INSERT INTO Agentic.AI_TOOL_VERSION (ID,StableKey,ContractHash,Method,PathTemplate,Summary,ParametersJSON,RequestBodyJSON,ResponsesJSON,SecurityJSON,Classification,Risk,Enabled,CreatedAt) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid4()), operation.stable_key, contract.source_hash, operation.method, operation.path, operation.summary,
                    json.dumps(operation.parameters), json.dumps(operation.request_body), json.dumps(operation.responses), json.dumps(operation.security),
                    "UNKNOWN", "UNREVIEWED", 0, datetime.now(timezone.utc).isoformat(),
                ),
            )
    return len(contract.operations)


def _seed_reviewed_read_defaults() -> int:
    version = 'mvp-reviewed-read-defaults-v1'
    if _rows('SELECT Version FROM Agentic.AI_SCHEMA_MIGRATION WHERE Version = ?', (version,)):
        return 0

    defaults = [item for item in catalog() if item['default_read_only']]
    checksum = hashlib.sha256('\n'.join(sorted(item['stable_key'] for item in defaults)).encode('utf-8')).hexdigest()
    _sql('START TRANSACTION')
    try:
        for item in defaults:
            rows = _rows(
                'SELECT ID FROM Agentic.AI_TOOL_VERSION WHERE StableKey = ? AND ContractHash = ?',
                (item['stable_key'], item['contract_hash']),
            )
            if not rows:
                raise RuntimeError(f"Reviewed read tool was not imported: {item['method']} {item['path']}")
            tool_version_id = rows[0][0]
            _sql(
                "UPDATE Agentic.AI_TOOL_VERSION SET Classification = 'READ_ONLY',Risk = 'LOW',Enabled = 1 WHERE ID = ?",
                (tool_version_id,),
            )
            _sql(
                'INSERT INTO Agentic.AI_TOOL_POLICY_OVERRIDE '
                '(ID,ToolVersionID,Classification,PrivilegesJSON,ScopeRulesJSON,Reason,Reviewer,ApprovalReference,CreatedAt) '
                'VALUES (?,?,?,?,?,?,?,?,?)',
                (
                    str(uuid4()), tool_version_id, 'READ_ONLY',
                    json.dumps({'availability': 'AVAILABLE', 'method': 'GET'}),
                    '{}', 'Reviewed read-only operation enabled by the deployment default.',
                    'system-bootstrap', version, datetime.now(timezone.utc).isoformat(),
                ),
            )
        _sql(
            'INSERT INTO Agentic.AI_SCHEMA_MIGRATION (Version,Checksum,AppliedAt,DeploymentIdentity,Outcome) VALUES (?,?,?,?,?)',
            (version, checksum, datetime.now(timezone.utc).isoformat(), 'system-bootstrap', 'SUCCEEDED'),
        )
        _sql('COMMIT')
    except BaseException:
        _sql('ROLLBACK')
        raise
    return len(defaults)


def setup() -> None:
    import iris

    previous = iris.system.Process.NameSpace()
    try:
        iris.system.Process.SetNamespace("AGENTIC")
        if not CSRF_KEY.exists():
            descriptor = os.open(str(CSRF_KEY), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(secrets.token_bytes(32))
        _migrate()
        _configure_worker()
        _configure_mvp_security()
        count = _import_contract()
        enabled_reads = _seed_reviewed_read_defaults()
        print(f"AGENTIC_INSTALL_OK operations={count} default_reads_enabled={enabled_reads}")
    finally:
        iris.system.Process.SetNamespace(previous)
