ARG IMAGE=intersystems/iris-community:2026.2@sha256:cd2ebcab02d1ef80ec155def4418399f353d867162688c36a3705760e750bdaa
FROM ${IMAGE} AS dependencies

USER root
RUN mkdir -p /opt/agentic /usr/irissys/mgr/agentic && \
    chown -R irisowner:irisowner /opt/agentic /usr/irissys/mgr/agentic

USER irisowner
WORKDIR /opt/agentic
COPY --chown=irisowner:irisowner requirements.txt ./
RUN python3 -m pip install --target /usr/irissys/mgr/python -r requirements.txt

FROM dependencies AS test
COPY --chown=irisowner:irisowner requirements-dev.txt ./
RUN python3 -m pip install --target /usr/irissys/mgr/python -r requirements-dev.txt
COPY --chown=irisowner:irisowner . .
ENV PYTHONPATH=/opt/agentic:/usr/irissys/mgr/python
RUN python3 -m pytest -q

FROM dependencies AS runtime
COPY --chown=irisowner:irisowner . .
RUN chmod +x /opt/agentic/scripts/startup.sh

ENV PYTHONPATH=/opt/agentic:/usr/irissys/mgr/python
RUN iris start IRIS && \
    iris merge IRIS /opt/agentic/merge.cpf && \
    iris session IRIS < /opt/agentic/iris.script > /tmp/agentic-build.log && \
    cat /tmp/agentic-build.log && \
    grep -q '^AGENTIC_EMBEDDED_PYTHON_OK' /tmp/agentic-build.log && \
    iris stop IRIS quietly
