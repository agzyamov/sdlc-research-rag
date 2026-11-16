# Contributing

Thanks for your interest! This project uses an explicit, enforced architecture, so please read this first.

## Ground rules
1. **The Module View is the quality gate.** New code goes into the module in [docs/architecture/01-module-view.md](docs/architecture/01-module-view.md) whose responsibility fits. If none fits, open an issue to discuss an architectural change before writing code. `uv run lint-imports` enforces the layer rules.
2. **Docs evolve with the code.** If you change runtime flow, deployment or module dependencies, update the matching view in the same PR. Regenerate the as-implemented diagrams with `uv run python tools/gen_diagrams.py`; CI fails if they're stale.
3. **OSS building blocks first.** Don't hand-roll what a library or framework built-in already provides (see ADR-0016's building-block map). Custom code needs a one-line justification in the PR naming the libraries checked.
4. **Technology changes need an ADR** in [docs/architecture/adr/](docs/architecture/adr/).
5. **Never commit papers** (PDFs, extracted text, figures, indexes). Many arXiv papers aren't redistributable. Only ids and metadata definitions go in git.
6. **No secrets in code or config.** Configuration goes through `sdlcrag.core.config.Settings` (env prefix `SDLCRAG_`).

## Commits
- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, `chore:`), checked by a commitizen commit-msg hook. Releases and the CHANGELOG are generated from them (`uv run cz bump`).
- **gitleaks** runs before every commit and in CI; never commit `.env` or keys.
- Dependabot opens weekly grouped PRs for Python deps and GitHub Actions.

## Setup
```bash
uv sync
uv run pre-commit install   # pre-commit + commit-msg hooks
pnpm -C web install         # Node 24 + pnpm (web app, Playwright)
docker compose up -d qdrant neo4j openfga
cp .env.example .env        # ANTHROPIC_API_KEY for anything that calls the LLM
```

Most tests need no services or keys: `uv run pytest` and `pnpm -C web e2e` (mocked API) run offline.

## Before opening a PR
```bash
uv run pytest
uv run lint-imports
uv run ruff check . && uv run ruff format --check .
uv run pyrefly check
tools/check_mermaid.sh        # if you touched diagrams
pnpm -C web check && pnpm -C web build && pnpm -C web e2e   # if you touched web/ or the API
```

Reporting a vulnerability? See [SECURITY.md](SECURITY.md). Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
