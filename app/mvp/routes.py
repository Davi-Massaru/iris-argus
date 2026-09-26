import os
from flask import Blueprint, current_app, jsonify, request
from app.auth import current_principal, require_permission, require_csrf
from app.mvp.catalog import catalog
from app.mvp.domain import validate_agent
from app.mvp.repository import AgentRepository, Conflict

bp = Blueprint('mvp', __name__, url_prefix='/api/mvp')


def repository():
    return current_app.extensions.get('mvp_repository') or AgentRepository()


@bp.errorhandler(ValueError)
def invalid(error):
    return jsonify(error={'message': str(error)}), 409 if isinstance(error, Conflict) else 400


@bp.errorhandler(LookupError)
def missing(error):
    return jsonify(error={'message': str(error)}), 404


@bp.get('/catalog')
@require_permission('view')
def tools():
    return jsonify(items=catalog(), default_model=os.environ.get('AGENTIC_MODEL', 'qwen2.5:3b'), provider='ollama')


@bp.get('/agents')
@require_permission('view')
def agents():
    return jsonify(items=repository().list_agents())


@bp.post('/agents')
@require_permission('design')
@require_csrf
def create():
    config = validate_agent(request.get_json(silent=True))
    return jsonify(repository().save_agent(config, current_principal().name)), 201


@bp.put('/agents/<identifier>')
@require_permission('design')
@require_csrf
def update(identifier):
    payload = request.get_json(silent=True)
    config = validate_agent(payload)
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
