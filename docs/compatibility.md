# Compatibility inventory

## Pinned platform

- InterSystems IRIS Community Edition: `2026.2`
- Container digest: `sha256:cd2ebcab02d1ef80ec155def4418399f353d867162688c36a3705760e750bdaa`
- WSGI application: `/agentic`, namespace `AGENTIC`, callable `app.wsgi:application`
- Authentication: IRIS password authentication; unauthenticated access is not enabled
- Application persistence: IRIS SQL schema `Agentic`
- Worker: `irispython` in the IRIS container and `AGENTIC` namespace
- Default host port: `52774` (container port `52773`)

## SysAdmin contract

The application vendors `specification/mainspec_v2.json` from commit `f764aea427e5c0b1dd08a4c18a0457e0ff7b3b34`. Its SHA-256 is `1ab154c7c5d9b25e6b227944a44a120c670686f876c2e14abfb9ee5898596650` and its declared base URL is `/api/admin`.

The importer checks OpenAPI 3.0.0, rejects remote references and checks local reference existence. Parameter-reference resolution and override semantics remain incomplete. Its current key includes contract hash, method and path, so stable operation identity across contract updates still needs implementation. Every operation begins `UNKNOWN`, disabled, so an HTTP verb or summary cannot authorize execution.

## Verified foundation capabilities

Container build/startup is the evidence gate for:

1. `import iris` in Embedded Python;
2. a parameterized-capable `iris.sql` session in namespace `AGENTIC`;
3. Flask callable import by IRIS WSGI;
4. contract parsing and operation inventory;
5. worker SQL connectivity.

Vector types, HNSW behavior, monitoring adapters, SysAdmin target authentication, mutation dispatch and conditional concurrency support remain disabled until their dedicated integration gates are implemented and recorded.

## Security boundary in this slice

The browser receives application APIs only. It receives no SysAdmin credentials and cannot submit arbitrary URLs, SQL or Python. No imported administrative operation is enabled automatically. Preliminary proposal decisions compare proposal ID, revision and action hash, but transactional concurrency, expiry and scoped authority are still incomplete. Execution is absent until the P3 dispatch and recovery tests pass.
