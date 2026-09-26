import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from jsonschema import Draft7Validator
from app.mvp.catalog import tool_by_key
from app.repositories.iris_repository import _rows


class ToolError(ValueError):
    pass


def _enabled_in_registry(item):
    rows = _rows(
        "SELECT Enabled FROM Agentic.AI_TOOL_VERSION WHERE StableKey = ? AND ContractHash = ?",
        (item["stable_key"], item["contract_hash"]),
    )
    return bool(rows and rows[0][0])


def _request_parameters(item, fixed, arguments):
    if not isinstance(arguments, dict):
        raise ToolError("INVALID_ARGUMENTS")
    if any(key in arguments and arguments[key] != value for key, value in fixed.items()):
        raise ToolError("FIXED_PARAMETER_OVERRIDE")
    params = {**arguments, **fixed}
    if list(Draft7Validator(item["schema"]).iter_errors(params)):
        raise ToolError("INVALID_ARGUMENTS")
    if len(json.dumps(params)) > 3500:
        raise ToolError("ARGUMENTS_TOO_LARGE")
    if item["method"] == "GET" and "maxRows" in item["schema"]["properties"]:
        value = params.setdefault("maxRows", 200)
        if not 1 <= value <= 500:
            raise ToolError("MAX_ROWS_RANGE_1_500")
    return params


def _target_base_url():
    base = os.environ.get("AGENTIC_SYSADMIN_URL", "http://127.0.0.1:52773/api/admin").rstrip("/")
    parsed = urlparse(base)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ToolError("INVALID_TARGET_CONFIGURATION")
    return base


def _target_credentials(base):
    username = os.environ.get("AGENTIC_SYSADMIN_USER")
    password = os.environ.get("AGENTIC_SYSADMIN_PASSWORD")
    if username:
        return username, password
    if base != "http://127.0.0.1:52773/api/admin":
        raise ToolError("TARGET_CREDENTIALS_REQUIRED")
    credential = json.loads(Path("/usr/irissys/mgr/agentic/sysadmin-credential.json").read_text())
    return credential["username"], credential["password"]


def _decode_response(data, status_code):
    if not data:
        return {"status_code": status_code}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"status_code": status_code, "unparsed_body_bytes": len(data)}


def _dispatch_request(transport, item, base, params, credentials):
    query_params = {name: value for name, value in params.items() if name != "body"}
    try:
        with transport.request(
            item["method"],
            base + item["path"],
            params=query_params,
            json=params.get("body"),
            auth=credentials,
            timeout=(5, 20),
            allow_redirects=False,
            stream=True,
        ) as response:
            if not 200 <= response.status_code < 300:
                raise ToolError(f"SYSADMIN_HTTP_{response.status_code}")
            data = bytearray()
            if item["method"] != "HEAD":
                for chunk in response.iter_content(4096):
                    data.extend(chunk)
                    if len(data) > 24000:
                        raise ToolError("RESPONSE_TOO_LARGE_USE_FILTER_OR_MAXROWS")
            result = _decode_response(data, response.status_code)
    except requests.RequestException:
        raise ToolError("SYSADMIN_UNAVAILABLE_OR_INVALID_JSON") from None
    if isinstance(result, dict) and result.get("status", {}).get("errors"):
        raise ToolError("SYSADMIN_REPORTED_ERRORS")
    if len(json.dumps(result)) > 30000:
        raise ToolError("RESPONSE_TOO_LARGE_USE_FILTER_OR_MAXROWS")
    return result


class Gateway:
    def __init__(self, bindings, transport=None, availability_lookup=None):
        self.bindings = {
            binding["key"]: {
                "fixed": binding.get("fixed", {}),
                "stable_key": binding.get("stable_key"),
                "contract_hash": binding.get("contract_hash"),
            }
            for binding in bindings
        }
        self.transport = transport or requests.Session()
        self.transport.trust_env = False
        self.availability_lookup = availability_lookup or _enabled_in_registry
        for key in self.bindings:
            item = tool_by_key(key)
            binding = self.bindings[key]
            if (
                binding["stable_key"] != item["stable_key"]
                or binding["contract_hash"] != item["contract_hash"]
            ):
                raise ToolError("TOOL_VERSION_MISMATCH")
            if not self.availability_lookup(item):
                raise ToolError("TOOL_BLOCKED")

    def execute(self, key, arguments):
        binding = self.bindings.get(key)
        if binding is None:
            raise ToolError("TOOL_NOT_ASSIGNED")
        item = tool_by_key(key)
        if not self.availability_lookup(item):
            raise ToolError("TOOL_BLOCKED")
        params = _request_parameters(item, binding["fixed"], arguments)
        base = _target_base_url()
        credentials = _target_credentials(base)
        if not self.availability_lookup(item):
            raise ToolError("TOOL_BLOCKED")
        return _dispatch_request(self.transport, item, base, params, credentials)
