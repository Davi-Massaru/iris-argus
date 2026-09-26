from flask import Blueprint, current_app, jsonify, request
from app.auth import current_principal, require_permission, require_csrf
from app.mvp.catalog import catalog
from app.mvp.domain import validate_agent
from app.mvp.providers import configured_provider, default_model
from app.mvp.repository import AgentRepository, Conflict

bp = Blueprint('mvp', __name__, url_prefix='/api/mvp')


def repository():
    return current_app.extensions.get('mvp_repository') or AgentRepository()


def tool_catalog():
    items = [dict(item) for item in catalog()]
    if not items:
        return items
    availability = current_app.extensions['agentic_repository'].list_tool_availability(items[0]['contract_hash'])
    for item in items:
        item['available'] = item['supported'] and availability.get(item['stable_key'], False)
        item['allowed'] = item['available']
    return items


@bp.errorhandler(ValueError)
def invalid(error):
    return jsonify(error={'message': str(error)}), 409 if isinstance(error, Conflict) else 400


@bp.errorhandler(LookupError)
def missing(error):
    return jsonify(error={'message': str(error)}), 404


@bp.get('/catalog')
@require_permission('view')
def tools():
    provider = configured_provider()
    return jsonify(items=tool_catalog(), default_model=default_model(provider), provider=provider)


@bp.put('/catalog/<stable_key>/availability')
@require_permission('approve')
@require_csrf
def set_tool_availability(stable_key):
    payload = request.get_json(silent=True) or {}
    enabled = payload.get('enabled')
    if type(enabled) is not bool:
        return jsonify(error={'message': 'enabled must be a boolean.'}), 400
    item = next((tool for tool in catalog() if tool['stable_key'] == stable_key), None)
    if item is None:
        return jsonify(error={'message': 'Tool not found in the pinned contract.'}), 404
    if not item['supported']:
        return jsonify(error={'message': 'This operation uses an unsupported OpenAPI request shape.'}), 409
    if enabled and item['method'] in {'POST', 'PUT', 'PATCH', 'DELETE'} and payload.get('acknowledge_auto_execution') is not True:
        return jsonify(error={'message': 'Explicitly acknowledge automatic execution for mutating operations.'}), 400
    if enabled and item['sensitive'] and payload.get('acknowledge_sensitive_data') is not True:
        return jsonify(error={'message': 'Explicitly acknowledge sensitive data handling for this operation.'}), 400
    result = current_app.extensions['agentic_repository'].set_tool_availability(
        stable_key=stable_key,
        contract_hash=item['contract_hash'],
        enabled=enabled,
        actor=current_principal().name,
        reason=str(payload.get('reason', ''))[:4000],
    )
    if result is None:
        return jsonify(error={'message': 'Tool version not found in the database.'}), 404
    return jsonify(result)


@bp.get('/agents')
@require_permission('view')
def agents():
    return jsonify(items=repository().list_agents())


@bp.post('/agents')
@require_permission('design')
@require_csrf
def create():
    available_keys = {item['key'] for item in tool_catalog() if item['allowed']}
    config = validate_agent(request.get_json(silent=True), enabled_keys=available_keys)
    return jsonify(repository().save_agent(config, current_principal().name)), 201


@bp.put('/agents/<identifier>')
@require_permission('design')
@require_csrf
def update(identifier):
    payload = request.get_json(silent=True)
    available_keys = {item['key'] for item in tool_catalog() if item['allowed']}
    config = validate_agent(payload, enabled_keys=available_keys)
    return jsonify(repository().save_agent(config, current_principal().name, identifier, payload.get('revision')))


@bp.post('/agents/<identifier>/runs')
@require_permission('run_read')
@require_csrf
def run(identifier):
    return jsonify(id=repository().enqueue(identifier, current_principal().name)), 202


@bp.get('/runs')
@require_permission('view')
def runs():
    return jsonify(items=repository().list_runs())


@bp.get('/runs/<identifier>')
@require_permission('view')
def detail(identifier):
    return jsonify(repository().get_run(identifier))
