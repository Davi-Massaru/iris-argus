"""Reviewed read operations derived from the pinned SysAdmin contract."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Explicit review, not an inference that every GET is safe.
READ_PATHS = {
    '/info', '/v2/locks', '/v2/process', '/v2/processes',
    '/v2/monitor/dashboard/main', '/v2/monitor/dashboard/ecp',
    '/v2/monitor/dashboard/globals-and-routines',
    '/v2/monitor/dashboard/system-resources', '/v2/monitor/license-usage',
    '/v2/monitor/system-usage', '/v2/monitor/system-usage/shared-memory',
    '/v2/task', '/v2/task/info', '/v2/task/history', '/v2/tasks',
    '/v2/task/manager', '/v2/task/upcoming', '/v2/journal/files',
}


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
    raw = (ROOT / 'specification/mainspec_v2.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    # This reviewed set is valid only for this exact contract.
    if digest != '1ab154c7c5d9b25e6b227944a44a120c670686f876c2e14abfb9ee5898596650':
        raise RuntimeError('Contract checksum mismatch')
    document = json.loads(raw)
    result = []
    for path, item in document['paths'].items():
        for method, operation in item.items():
            if method not in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'}:
                continue
            allowed = method == 'get' and path in READ_PATHS
            parameters = {}
            for p in [*item.get('parameters', []), *operation.get('parameters', [])]:
                p = resolve(p, document)
                parameters[(p['in'], p['name'])] = p
            schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
            for p in parameters.values():
                if p['in'] != 'query':
                    allowed = False
                schema['properties'][p['name']] = {**p.get('schema', {}), 'description': p.get('description', '')}
                if p.get('required'):
                    schema['required'].append(p['name'])
            key = method + '_' + path.strip('/').replace('/', '_').replace('-', '_')
            result.append(dict(key=key, method=method.upper(), path=path,
                               description=operation.get('summary', ''), schema=schema,
                               allowed=allowed, contract_hash=digest))
    return result


def tool_by_key(key):
    for item in catalog():
        if item['key'] == key and item['allowed']:
            return item
    raise ValueError('Ferramenta não autorizada no MVP.')
