ARG IMAGE=intersystems/iris-community:2026.2@sha256:cd2ebcab02d1ef80ec155def4418399f353d867162688c36a3705760e750bdaa
FROM ${IMAGE}
USER root
RUN mkdir -p /opt/argus /usr/irissys/mgr/argus && chown -R irisowner:irisowner /opt/argus /usr/irissys/mgr/argus
USER irisowner
WORKDIR /opt/argus
COPY --chown=irisowner:irisowner requirements.txt requirements-dev.txt ./
RUN python3 -m pip install --target /usr/irissys/mgr/python -r requirements-dev.txt
COPY --chown=irisowner:irisowner . .
RUN chmod +x /opt/argus/scripts/startup.sh
ENV PYTHONPATH=/opt/argus/python:/usr/irissys/mgr/python
ENV ARGUS_LLM_MODE=mock
RUN iris start IRIS && iris merge IRIS /opt/argus/merge.cpf && \
    iris session IRIS < /opt/argus/iris.script > /tmp/argus-build.log && \
    cat /tmp/argus-build.log && grep -q '^ARGUS_EMBEDDED_PYTHON_OK' /tmp/argus-build.log && iris stop IRIS quietly
