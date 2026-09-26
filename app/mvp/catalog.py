"""Reviewed read operations derived from the pinned SysAdmin contract."""

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_METHODS = {"GET", "POST", "PUT", "DELETE", "HEAD"}
CONTRACT_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
SENSITIVE_FIELD = re.compile(
    r"password|secret|token|credential|authorization|api.?key", re.IGNORECASE
)


def _contains_sensitive_fields(value):
    if isinstance(value, dict):
        if value.get("format") == "password":
            return True
        return any(
            SENSITIVE_FIELD.search(str(key)) or _contains_sensitive_fields(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_fields(item) for item in value)
    return False


def _remove_examples(value):
    if isinstance(value, dict):
        return {
            key: _remove_examples(item)
            for key, item in value.items()
            if key not in {"example", "default"}
        }
    if isinstance(value, list):
        return [_remove_examples(item) for item in value]
    return value


def load_reviewed_read_operations(path, contract_hash, operations):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise RuntimeError("Unsupported reviewed-read manifest schema.")
    if (
        manifest.get("source_contract") != "mainspec_v2.json"
        or manifest.get("source_sha256") != contract_hash
    ):
        raise RuntimeError("Reviewed-read manifest does not match the pinned SysAdmin contract.")
    entries = manifest.get("operations")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("Reviewed-read manifest must contain operations.")

    operation_index = {(item["method"], item["path"]): item for item in operations}
    reviewed = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Invalid reviewed-read manifest entry.")
        method = entry.get("method")
        route = entry.get("path")
        reason = entry.get("reason")
        if (
            method != "GET"
            or entry.get("classification") != "READ_ONLY"
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise RuntimeError("Reviewed-read entries must be justified READ_ONLY GET operations.")
        identity = (method, route)
        if identity in reviewed:
            raise RuntimeError(f"Duplicate reviewed-read operation: {method} {route}")
        operation = operation_index.get(identity)
        if operation is None:
            raise RuntimeError(
                f"Reviewed-read operation is absent from the pinned contract: {method} {route}"
            )
        if not operation["supported"] or operation["sensitive"]:
            raise RuntimeError(
                f"Reviewed-read operation is unsupported or sensitive: {method} {route}"
            )
        reviewed[identity] = reason.strip()
    return reviewed


def resolve(value, document, seen=()):
    if isinstance(value, dict):
        if "$ref" in value:
            ref = value["$ref"]
            if not ref.startswith("#/") or ref in seen:
                raise ValueError("Unsupported reference")
            target = document
            for token in ref[2:].split("/"):
                target = target[token.replace("~1", "/").replace("~0", "~")]
            return resolve(target, document, (*seen, ref))
        return {k: resolve(v, document, seen) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, document, seen) for v in value]
    return value


def _input_schema(path, method, path_item, operation, document):
    supported = method in SUPPORTED_METHODS and "{" not in path and "}" not in path
    parameters = {}
    for raw_parameter in [*path_item.get("parameters", []), *operation.get("parameters", [])]:
        parameter = resolve(raw_parameter, document)
        if not isinstance(parameter, dict) or "in" not in parameter or "name" not in parameter:
            supported = False
            continue
        parameters[(parameter["in"], parameter["name"])] = parameter

    schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    for parameter in parameters.values():
        if parameter["in"] != "query":
            supported = False
            continue
        parameter_schema = resolve(parameter.get("schema", {}), document)
        if not isinstance(parameter_schema, dict):
            supported = False
            continue
        schema["properties"][parameter["name"]] = {
            **parameter_schema,
            "description": parameter.get("description", ""),
        }
        if parameter.get("required"):
            schema["required"].append(parameter["name"])

    request_body = operation.get("requestBody")
    if request_body:
        request_body = resolve(request_body, document)
        content = request_body.get("content", {})
        json_body = content.get("application/json") if isinstance(content, dict) else None
        body_schema = (
            resolve(json_body.get("schema"), document)
            if isinstance(json_body, dict) and json_body.get("schema")
            else None
        )
        if not isinstance(body_schema, dict):
            supported = False
        else:
            schema["properties"]["body"] = body_schema
            if request_body.get("required"):
                schema["required"].append("body")
    return schema, supported


def _catalog_entry(path, raw_method, path_item, operation, digest, document):
    method = raw_method.upper()
    schema, supported = _input_schema(path, method, path_item, operation, document)
    stable_key = hashlib.sha256(f"{digest}:{method}:{path}".encode("utf-8")).hexdigest()
    key = method.lower() + "_" + path.strip("/").replace("/", "_").replace("-", "_")
    if len(key) > 64:
        key = f"{method.lower()}_{hashlib.sha256(f'{method}:{path}'.encode('utf-8')).hexdigest()[:32]}"
    responses = resolve(operation.get("responses", {}), document)
    sensitive = _contains_sensitive_fields({"request": schema, "responses": responses})
    return dict(
        key=key,
        method=method,
        path=path,
        description=operation.get("summary", ""),
        schema=_remove_examples(schema),
        stable_key=stable_key,
        supported=supported,
        allowed=False,
        default_read_only=False,
        review_reason=None,
        sensitive=sensitive,
        contract_hash=digest,
    )


def _path_operations(path, path_item, digest, document):
    if not isinstance(path_item, dict):
        return []
    return [
        _catalog_entry(path, method, path_item, operation, digest, document)
        for method, operation in path_item.items()
        if method.lower() in CONTRACT_METHODS and isinstance(operation, dict)
    ]


@lru_cache(maxsize=1)
def catalog():
    source_path = ROOT / "specification/mainspec_v2.json"
    raw = source_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != "1ab154c7c5d9b25e6b227944a44a120c670686f876c2e14abfb9ee5898596650":
        raise RuntimeError("Contract checksum mismatch")
    document = json.loads(raw)
    result = [
        entry
        for path, path_item in document["paths"].items()
        for entry in _path_operations(path, path_item, digest, document)
    ]
    reviewed = load_reviewed_read_operations(
        ROOT / "specification/reviewed_read_operations.json",
        digest,
        result,
    )
    for item in result:
        reason = reviewed.get((item["method"], item["path"]))
        item["default_read_only"] = reason is not None
        item["review_reason"] = reason
    return result


def tool_by_key(key):
    for item in catalog():
        if item["key"] == key:
            if item["supported"]:
                return item
            raise ValueError("Operation uses unsupported OpenAPI parameters or body content.")
    raise ValueError("Unknown operation in the pinned API contract.")
