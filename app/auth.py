from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import hashlib
import hmac
import os
from pathlib import Path

from flask import current_app, g, jsonify, request


ROLE_PERMISSIONS = {
    "Viewer": {"view"},
    "Operator": {"view", "run_read", "ack_alert"},
    "AgentDesigner": {"view", "run_read", "design"},
    "DBAApprover": {"view", "approve"},
    "PlatformAdministrator": {"view", "run_read", "ack_alert", "design", "approve", "admin"},
}


@dataclass(frozen=True)
class Principal:
    name: str
    roles: frozenset[str]

    def permits(self, permission: str) -> bool:
        return any(permission in ROLE_PERMISSIONS.get(role, set()) for role in self.roles)


def current_principal() -> Principal:
    if hasattr(g, "agentic_principal"):
        return g.agentic_principal
    name = ""
    native_roles = set()
    if current_app.testing:
        name = request.environ.get("REMOTE_USER", "")
        native_roles = set(request.environ.get("agentic.test.roles", "").split(","))
    else:
        try:
            import iris
            # WSGI runs in the authenticated IRIS context. Process.UserName()
            # reports the OS account in this release, not the browser principal.
            name = str(iris.execute('return $username'))
            native_roles = set(str(iris.execute('return $roles')).split(','))
        except Exception:
            pass  # Fail closed when the IRIS security context cannot be read.
    if name.upper() == "UNKNOWNUSER":
        name = ""
    roles = {role for role in ROLE_PERMISSIONS if f"Agentic{role}" in native_roles}
    if "%All" in native_roles:
        roles.add("PlatformAdministrator")
    principal = Principal(name=name, roles=frozenset(roles))
    g.agentic_principal = principal
    return principal


def require_permission(permission: str):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            principal = current_principal()
            if not principal.name:
                return jsonify(error={"code": "AUTHENTICATION_REQUIRED", "message": "Authentication is required."}), 401
            if not principal.permits(permission):
                return jsonify(error={"code": "FORBIDDEN", "message": "The authenticated user lacks this permission."}), 403
            return function(*args, **kwargs)

        return wrapped

    return decorator


def csrf_token(principal: Principal) -> str:
    secret = current_app.config.get("AGENTIC_CSRF_SECRET")
    if secret is None:
        secret = os.environ.get("AGENTIC_CSRF_SECRET", "").encode("utf-8")
    if not secret:
        secret = Path("/usr/irissys/mgr/agentic/csrf.key").read_bytes()
    return hmac.new(secret, principal.name.encode("utf-8"), hashlib.sha256).hexdigest()


def require_csrf(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        supplied = request.headers.get("X-Agentic-CSRF", "")
        expected = csrf_token(current_principal())
        if not hmac.compare_digest(supplied, expected):
            return jsonify(error={"code": "CSRF_REJECTED", "message": "A valid same-origin decision token is required."}), 403
        return function(*args, **kwargs)

    return wrapped
