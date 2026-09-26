from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


@dataclass(frozen=True)
class ImportedOperation:
    stable_key: str
    operation_id: str | None
    method: str
    path: str
    summary: str
    parameters: tuple[dict[str, Any], ...]
    request_body: dict[str, Any] | None
    responses: dict[str, Any]
    security: tuple[dict[str, Any], ...]
    classification: str = "UNKNOWN"
    enabled: bool = False


@dataclass(frozen=True)
class ImportedContract:
    source_hash: str
    title: str
    version: str
    base_url: str
    operations: tuple[ImportedOperation, ...]


def _validate_refs(value: Any, document: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str):
                if not item.startswith("#/"):
                    raise ValueError(f"Remote reference is not allowed: {item}")
                target: Any = document
                try:
                    for token in item[2:].split("/"):
                        target = target[token.replace("~1", "/").replace("~0", "~")]
                except (KeyError, TypeError):
                    raise ValueError(f"Unresolved local reference: {item}") from None
            _validate_refs(item, document)
    elif isinstance(value, list):
        for item in value:
            _validate_refs(item, document)


def _merge_parameters(
    path_parameters: list[dict[str, Any]], operation_parameters: list[dict[str, Any]]
) -> tuple[dict[str, Any], ...]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    for parameter in [*path_parameters, *operation_parameters]:
        if "$ref" in parameter:
            unresolved.append(parameter)
            continue
        key = (str(parameter.get("name", "")), str(parameter.get("in", "")))
        merged[key] = parameter
    return tuple([*merged.values(), *unresolved])


def load_contract(path: Path) -> ImportedContract:
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8"))
    if document.get("openapi") != "3.0.0":
        raise ValueError("The pinned contract must be OpenAPI 3.0.0")
    if not isinstance(document.get("paths"), dict):
        raise ValueError("The contract has no paths object")
    _validate_refs(document, document)
    source_hash = hashlib.sha256(raw).hexdigest()
    operations: list[ImportedOperation] = []
    default_security = tuple(document.get("security", []))
    for route, path_item in document["paths"].items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = list(path_item.get("parameters", []))
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            normalized_method = method.upper()
            identity = f"{source_hash}:{normalized_method}:{route}".encode("utf-8")
            operations.append(
                ImportedOperation(
                    stable_key=hashlib.sha256(identity).hexdigest(),
                    operation_id=operation.get("operationId"),
                    method=normalized_method,
                    path=route,
                    summary=str(operation.get("summary", "")),
                    parameters=_merge_parameters(
                        path_parameters, list(operation.get("parameters", []))
                    ),
                    request_body=operation.get("requestBody"),
                    responses=dict(operation.get("responses", {})),
                    security=tuple(operation.get("security", default_security)),
                )
            )
    return ImportedContract(
        source_hash=source_hash,
        title=str(document.get("info", {}).get("title", "")),
        version=str(document.get("info", {}).get("version", "")),
        base_url=str((document.get("servers") or [{}])[0].get("url", "")),
        operations=tuple(operations),
    )
