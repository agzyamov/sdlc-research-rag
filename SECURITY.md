# Security policy

## Reporting a vulnerability
Please report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on this repository ([private advisory form](https://github.com/agzyamov/sdlc-research-rag/security/advisories/new)). Do not open a public issue.

Include what you found, how to reproduce it, and the impact you expect. You should get a first reply within a week.

## Scope
In scope: the Python package (`src/sdlcrag`), the HTTP API (`sdlcrag.api`), the web app (`web/`), and the deployment files (`compose.yaml`, `infra/`).

Worth knowing before you report:
- **The demo user switcher is not authentication.** The `X-Demo-User` header selects one of the principals in `data/corpus.yaml`, so anyone can pick any demo user. A deployment must derive the principal from a verified token (for example an OIDC proxy); see ADR-0019. Reports that only show "I can switch demo users" are expected behaviour.
- **License-aware access is in scope.** If a principal can see a restricted paper's text, facts or title through the API, the chat or the graph, that is a vulnerability: access checks run server-side (OpenFGA) and must hold on every endpoint.
- The local service defaults in `compose.yaml` (ports, no auth on Qdrant and Neo4j) are for local development only.

## Supported versions
Only the latest commit on `main` gets fixes.
