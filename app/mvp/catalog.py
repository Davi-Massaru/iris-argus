"""Reviewed read operations derived from the pinned SysAdmin contract."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'HEAD'}
SENSITIVE_FIELD = re.compile(r'password|secret|token|credential|authorization|api.?key', re.IGNORECASE)


def _contains_sensitive_fields(value):
    if isinstance(value, dict):
        if value.get('format') == 'password':
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
        return {key: _remove_examples(item) for key, item in value.items() if key not in {'example', 'default'}}
    if isinstance(value, list):
        return [_remove_examples(item) for item in value]
    return value


def resolve(value, document, seen=()):
    if isinstance(value, dict):
        if '$ref' in value:
            ref = value['$ref']
            if not ref.startswith('#/') or ref in seen:
                raise ValueError('Unsupported reference')
            target = document
            for token in ref[2:].split('/'):
                target = target[token.replace('~1', '/').replace('~0', '~')]
            return resolve(target, document, (*seen, ref))
        return {k: resolve(v, document, seen) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, document, seen) for v in value]
    return value


@lru_cache(maxsize=1)
def catalog():
    source_path = ROOT / 'specification/mainspec_v2.json'
    raw = source_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != '1ab154c7c5d9b25e6b227944a44a120c670686f876c2e14abfb9ee5898596650':
        raise RuntimeError('Contract checksum mismatch')
    document = json.loads(raw)
    result = []
    for path, item in document['paths'].items():
        if not isinstance(item, dict):
            continue
        path_parameters = item.get('parameters', [])
        for raw_method, operation in item.items():
            method = raw_method.upper()
            if raw_method.lower() not in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'} or not isinstance(operation, dict):
                continue
            parameters = {}
            supported = method in SUPPORTED_METHODS and '{' not in path and '}' not in path
            for raw_parameter in [*path_parameters, *operation.get('parameters', [])]:
                p = resolve(raw_parameter, document)
                if not isinstance(p, dict) or 'in' not in p or 'name' not in p:
                    supported = False
                    continue
                parameters[(p['in'], p['name'])] = p
            schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
            for p in parameters.values():
                if p['in'] != 'query':
                    supported = False
                    continue
                parameter_schema = resolve(p.get('schema', {}), document)
                schema['properties'][p['name']] = {**parameter_schema, 'description': p.get('description', '')}
                if p.get('required'):
                    schema['required'].append(p['name'])

            request_body = resolve(operation.get('requestBody'), document) if operation.get('requestBody') else None
            if request_body:
                json_body = request_body.get('content', {}).get('application/json')
                body_schema = resolve(json_body.get('schema'), document) if isinstance(json_body, dict) and json_body.get('schema') else None
                if not isinstance(body_schema, dict):
                    supported = False
                else:
                    schema['properties']['body'] = body_schema
                    if request_body.get('required'):
                        schema['required'].append('body')

            key = method.lower() + '_' + path.strip('/').replace('/', '_').replace('-', '_')
            if len(key) > 64:
                key = f'{method.lower()}_{hashlib.sha256(f"{method}:{path}".encode("utf-8")).hexdigest()[:32]}'
            stable_key = hashlib.sha256(f'{digest}:{method}:{path}'.encode('utf-8')).hexdigest()
            responses = resolve(operation.get('responses', {}), document)
            sensitive = _contains_sensitive_fields({'request': schema, 'responses': responses})
            result.append(dict(key=key, method=method.upper(), path=path,
                               description=operation.get('summary', ''), schema=_remove_examples(schema),
                               stable_key=stable_key, supported=supported, allowed=False,
                               sensitive=sensitive,
                               contract_hash=digest))
    return result


def tool_by_key(key):
    for item in catalog():
        if item['key'] == key:
            if item['supported']:
                return item
            raise ValueError('Operation uses unsupported OpenAPI parameters or body content.')
    raise ValueError('Unknown operation in the pinned API contract.')
