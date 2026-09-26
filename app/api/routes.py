from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    send_from_directory,
    abort,
)

from app.auth import csrf_token, current_principal, require_csrf, require_permission


api = Blueprint("agentic", __name__)


def repository():
    return current_app.extensions["agentic_repository"]


@api.get("/")
@require_permission("view")
def home():
    return render_template("index.html", principal=current_principal())


@api.get("/assets/<name>")
@require_permission("view")
def asset(name):
    # IRIS reserves /static for its StreamServer. Route bundled assets through
    # the authenticated WSGI layer using a fixed filename allowlist.
    filename = {"style": "app.css", "script": "app.js"}.get(name)
    if filename is None:
        abort(404)
    return send_from_directory(current_app.static_folder, filename)


@api.get("/health")
@require_permission("view")
def health():
    state = repository().health()
    return jsonify(state), 200 if state.get("ready") else 503


@api.get("/api/v1/overview")
@require_permission("view")
def overview():
    return jsonify(repository().overview())


@api.get("/api/v1/session")
@require_permission("view")
def session_context():
    principal = current_principal()
    return jsonify(
        {
            "principal": principal.name,
            "roles": sorted(principal.roles),
            "csrf_token": csrf_token(principal),
        }
    )


@api.get("/api/v1/tools")
@require_permission("view")
def tools():
    limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    return jsonify(
        {
            "items": repository().list_tools(limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }
    )


@api.get("/api/v1/proposals")
@require_permission("view")
def proposals():
    limit = min(max(int(request.args.get("limit", 50)), 1), 100)
    return jsonify({"items": repository().list_proposals(limit=limit)})


@api.post("/api/v1/proposals/<proposal_id>/approve")
@require_permission("approve")
@require_csrf
def approve(proposal_id: str):
    payload = request.get_json(silent=True) or {}
    revision = payload.get("revision")
    action_hash = payload.get("action_hash")
    if not isinstance(revision, int) or not isinstance(action_hash, str):
        return jsonify(
            error={"code": "INVALID_DECISION", "message": "revision and action_hash are required."}
        ), 400
    result = repository().decide_proposal(
        proposal_id=proposal_id,
        revision=revision,
        action_hash=action_hash,
        actor=current_principal().name,
        decision="APPROVED",
        reason=str(payload.get("reason", ""))[:1000],
    )
    if result is None:
        return jsonify(
            error={
                "code": "STALE_PROPOSAL",
                "message": "Proposal revision or hash no longer matches.",
            }
        ), 409
    return jsonify(result)


@api.post("/api/v1/proposals/<proposal_id>/reject")
@require_permission("approve")
@require_csrf
def reject(proposal_id: str):
    payload = request.get_json(silent=True) or {}
    revision = payload.get("revision")
    action_hash = payload.get("action_hash")
    if not isinstance(revision, int) or not isinstance(action_hash, str):
        return jsonify(
            error={"code": "INVALID_DECISION", "message": "revision and action_hash are required."}
        ), 400
    result = repository().decide_proposal(
        proposal_id=proposal_id,
        revision=revision,
        action_hash=action_hash,
        actor=current_principal().name,
        decision="REJECTED",
        reason=str(payload.get("reason", ""))[:1000],
    )
    if result is None:
        return jsonify(
            error={
                "code": "STALE_PROPOSAL",
                "message": "Proposal revision or hash no longer matches.",
            }
        ), 409
    return jsonify(result)
