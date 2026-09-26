import json
import re
from jsonschema import Draft7Validator
from app.mvp.catalog import tool_by_key


def validate_agent(data):
    if not isinstance(data, dict):
        raise ValueError('Envie um objeto JSON.')
    clean = {}
    for field, maximum in [('name', 120), ('prompt', 6000), ('task', 6000), ('model', 100)]:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError(f'{field}: obrigatório, máximo {maximum} caracteres.')
        clean[field] = value.strip()
    if not re.fullmatch(r'[a-zA-Z0-9_.:/-]+', clean['model']):
        raise ValueError('Identificador de modelo inválido.')
    clean['provider'] = data.get('provider', 'ollama')
    if clean['provider'] != 'ollama':
        raise ValueError('Provedor não instalado. O MVP inclui Ollama.')
    interval = data.get('interval_seconds', 0)
    if type(interval) is not int or (interval != 0 and not 60 <= interval <= 86400):
        raise ValueError('Intervalo: 0 (manual) ou 60–86400 segundos.')
    clean['interval_seconds'] = interval
    if type(data.get('enabled', True)) is not bool:
        raise ValueError('enabled deve ser booleano.')
    clean['enabled'] = data.get('enabled', True)
    bindings = data.get('tools')
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= 12:
        raise ValueError('Selecione entre 1 e 12 ferramentas.')
    clean['tools'] = []
    seen = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError('Configuração de ferramenta inválida.')
        item = tool_by_key(binding.get('key'))
        if item['key'] in seen:
            raise ValueError('Ferramenta duplicada.')
        seen.add(item['key'])
        fixed = binding.get('fixed', {})
        if not isinstance(fixed, dict):
            raise ValueError('Parâmetros fixos devem ser um objeto.')
        schema = {**item['schema'], 'required': []}
        if list(Draft7Validator(schema).iter_errors(fixed)):
            raise ValueError('Parâmetros fixos incompatíveis com o contrato.')
        clean['tools'].append({'key': item['key'], 'fixed': fixed})
    if len(json.dumps(clean)) > 28000:
        raise ValueError('Configuração excede o limite de armazenamento.')
    return clean
