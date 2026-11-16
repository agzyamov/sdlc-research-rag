# ADR-0011: Tooling: uv, ruff, pyrefly, pytest, import-linter, Colima

- Status: Accepted (2026-11-15)

## Decision
- **uv**: environments, locking, Python pinning (3.12).
- **ruff**: lint + format.
- **pyrefly 1.x**: type checking (stable since 2026-05, Rust-fast). It is preferred over mypy (slow) and ty (still pre-1.0).
- **pytest**: tests, with markers `integration` and `eval`.
- **import-linter**: makes the Module View executable (layers contract) and serves as the architecture quality gate.
- **pre-commit**: runs all of the above, plus a forbidden-term check.
- **gitleaks**: secret scanning in pre-commit and CI; full-history scan clean (one documented false positive in `.gitleaksignore`).
- **commitizen**: Conventional Commits enforced at commit-msg; `cz bump` produces versions, tags and CHANGELOG at release time.
- **Dependabot**: weekly grouped updates for uv dependencies and GitHub Actions.
- **CI** (GitHub Actions): secrets scan, quality gates (ruff, pyrefly, import-linter, diagram freshness, tests) and Mermaid validation. Releases, branch protection, CodeQL and Scorecard are added when the repository goes public.
- **Colima + docker compose**: local container runtime for Qdrant, OpenFGA and Langfuse.

## Consequences
+ Fast feedback; architecture drift is caught at commit time.
