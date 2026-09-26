import json
import os
import re
from jsonschema import Draft7Validator
from app.mvp.catalog import tool_by_key


def validate_agent(data, *, enabled_keys=()):
    if not isinstance(data, dict):
        raise ValueError('Request must be a JSON object.')
    clean = {}
    for field, maximum in [('name', 120), ('prompt', 6000), ('task', 6000), ('model', 100)]:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError(f'{field} is required and must be at most {maximum} characters.')
        clean[field] = value.strip()
    if not re.fullmatch(r'[a-zA-Z0-9_.:/-]+', clean['model']):
        raise ValueError('Invalid model identifier.')
    provider = os.environ.get('AGENTIC_PROVIDER', 'ollama').strip().lower()
    if provider not in {'ollama', 'openai'}:
        raise ValueError('AGENTIC_PROVIDER must be ollama or openai.')
    if provider == 'openai' and not os.environ.get('AGENTIC_OPENAI_API_KEY', '').strip():
        raise ValueError('Set AGENTIC_OPENAI_API_KEY before creating an OpenAI agent.')
    if data.get('provider', provider) != provider:
        raise ValueError('Agent provider must match the configured deployment provider.')
    clean['provider'] = provider
    interval = data.get('interval_seconds', 0)
    if type(interval) is not int or (interval != 0 and not 60 <= interval <= 86400):
        raise ValueError('Interval must be 0 (manual) or between 60 and 86400 seconds.')
    clean['interval_seconds'] = interval
    if type(data.get('enabled', True)) is not bool:
        raise ValueError('enabled must be a boolean.')
    clean['enabled'] = data.get('enabled', True)
    bindings = data.get('tools')
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= 12:
        raise ValueError('Select between 1 and 12 tools.')
    clean['tools'] = []
    seen = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError('Invalid tool configuration.')
        item = tool_by_key(binding.get('key'))
        if item['key'] not in enabled_keys:
            raise ValueError('Tool is blocked or has not been enabled by a DBA.')
        if item['key'] in seen:
            raise ValueError('Duplicate tool assignment.')
        seen.add(item['key'])
        fixed = binding.get('fixed', {})
        if not isinstance(fixed, dict):
            raise ValueError('Fixed parameters must be a JSON object.')
        schema = {**item['schema'], 'required': []}
        if list(Draft7Validator(schema).iter_errors(fixed)):
            raise ValueError('Fixed parameters do not match the operation schema.')
        clean['tools'].append({
            'key': item['key'],
            'stable_key': item['stable_key'],
            'contract_hash': item['contract_hash'],
            'fixed': fixed,
        })
    if len(json.dumps(clean)) > 28000:
        raise ValueError('Agent configuration exceeds the storage limit.')
    return clean
