"""Explicit, user-triggered explanations of authorized historical evidence."""
from flask import Blueprint, g, request, render_template, abort
from itsdangerous import TimestampSigner, BadSignature
from argus import store
from argus.llm import provider_name, explain, ExplanationError
from argus.history import authorize

bp=Blueprint('intelligence',__name__)
bp.before_request(authorize)


def signer():
    return TimestampSigner(request.headers['Authorization'],salt='argus-explanation')


@bp.route('/explain/<identifier>',methods=['GET','POST'])
def incident_explanation(identifier):
    incident=store.incident(identifier)
    if not incident:
        abort(404)
    result=None
    error=None
    try:
        provider=provider_name()
        if request.method=='POST':
            if request.headers.get('Sec-Fetch-Site')=='cross-site' or request.form.get('confirm')!='yes':
                abort(400)
            try:
                if signer().unsign(request.form.get('token',''),max_age=300).decode()!=identifier+':'+provider:
                    abort(400)
            except BadSignature:
                abort(400)
            result=explain(incident)
            store.event('ReportExecution',{'type':'explanation','incident_id':identifier,
                                         'provider':provider,'user':g.identity['username']})
    except ExplanationError as failure:
        provider='unavailable'
        error=str(failure)
    return render_template('explanation.html',title='Explain this incident',section='incidents',
                           mode='OPTIONAL EXPLANATION',incident=incident,provider=provider,result=result,
                           error=error,token=signer().sign(identifier+':'+provider).decode())
