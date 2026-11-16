"""`sdlcrag` CLI entry point."""

import os
from pathlib import Path

import dagster as dg
import typer

from sdlcrag.core.config import get_settings
from sdlcrag.core.logging import configure_logging
from sdlcrag.evaluation.dataset import load_golden
from sdlcrag.ingestion.pipeline import load_corpus_window
from sdlcrag.orchestration.assets import (
    PAPERS_PARTITION,
    SyncConfig,
    corpus_plan,
    entity_resolution,
    paper_facts,
    paper_index,
)

# show_locals off: locals hold models and clients, and rendering them takes minutes.
app = typer.Typer(
    help="SDLC Research RAG", no_args_is_help=True, pretty_exceptions_show_locals=False
)


@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    configure_logging("INFO" if verbose else "WARNING")


NOT_IMPLEMENTED = "not implemented yet (scaffold)"
# Dagster logs every step event at DEBUG; the CLI prints its own progress instead.
QUIET_LOGS = {"console": {"config": {"log_level": "WARNING"}}}


def _dagster_instance() -> dg.DagsterInstance:
    home = Path(os.environ.setdefault("DAGSTER_HOME", str(get_settings().dagster_home)))
    home.mkdir(parents=True, exist_ok=True)
    (home / "dagster.yaml").touch()  # defaults: SQLite storage inside DAGSTER_HOME
    return dg.DagsterInstance.get()


def _run(max_papers: int, *, incremental: bool) -> None:
    """Materialize the corpus assets in-process (same instance as `dagster dev` uses)."""
    instance = _dagster_instance()
    result = dg.materialize(
        [corpus_plan],
        instance=instance,
        run_config=dg.RunConfig(
            ops={"corpus_plan": SyncConfig(max_papers=max_papers, incremental=incremental)},
            loggers=QUIET_LOGS,
        ),
    )
    meta = result.asset_materializations_for_node("corpus_plan")[0].metadata
    typer.echo(", ".join(f"{k}={v.value}" for k, v in meta.items()))

    planned = list(result.output_for_node("corpus_plan"))  # new, newer version or stale format
    to_index = list(dict.fromkeys(planned + _missing(instance, "paper_index")))
    _materialize("index", instance, to_index)
    # Re-indexing rewrites the abstract point (dropping its facts), so re-run extraction for
    # every paper just indexed; the asset skips papers whose facts are already current.
    to_extract = list(dict.fromkeys(to_index + _missing(instance, "paper_facts")))
    _materialize("extract facts", instance, to_extract)
    _resolve(instance)


def _resolve(instance: dg.DagsterInstance) -> None:
    """Merge spelling variants of extracted names across papers (one unpartitioned run)."""
    result = dg.materialize(
        [entity_resolution],
        instance=instance,
        run_config=dg.RunConfig(loggers=QUIET_LOGS),
    )
    meta = result.asset_materializations_for_node("entity_resolution")[0].metadata
    typer.echo(f"entity resolution: {meta['merged_groups'].value} merged groups")


def _missing(instance: dg.DagsterInstance, asset: str) -> list[str]:
    """Registered papers (the current window) not yet materialized for `asset`."""
    done = instance.get_materialized_partitions(dg.AssetKey(asset))
    return [k for k in instance.get_dynamic_partitions(PAPERS_PARTITION) if k not in done]


def _materialize(step: str, instance: dg.DagsterInstance, keys: list[str]) -> None:
    """Materialize one asset per paper partition in-process; failures are retried next run."""
    asset = {"index": paper_index, "extract facts": paper_facts}[step]
    typer.echo(f"{step}: {len(keys)} papers")
    failed: list[str] = []
    for i, key in enumerate(keys, 1):
        typer.echo(f"  [{i}/{len(keys)}] {key}")
        run = dg.materialize(
            [corpus_plan, paper_index, paper_facts],
            selection=[asset],
            partition_key=key,
            instance=instance,
            run_config=dg.RunConfig(loggers=QUIET_LOGS),
            raise_on_error=False,
        )
        if not run.success:
            failed.append(key)
    typer.echo(f"{step}: {len(keys) - len(failed)}/{len(keys)} done")
    if failed:
        typer.echo(f"{step} failed (retried on the next run): {', '.join(failed)}")


@app.command()
def ingest(
    dev: bool = typer.Option(False, "--dev", help="development slice (window.dev_max_papers)"),
    limit: int | None = typer.Option(None, help="override the number of newest papers"),
) -> None:
    """Initial load: index the newest arXiv papers matching data/corpus.yaml (resumable)."""
    window = load_corpus_window(get_settings().corpus_path)
    _run(limit or (window.dev_max_papers if dev else window.max_papers), incremental=False)


@app.command()
def update(
    dev: bool = typer.Option(False, "--dev", help="keep the development-size window"),
) -> None:
    """Incremental sync from arXiv OAI-PMH (new, revised, withdrawn, evicted) without a rebuild."""
    window = load_corpus_window(get_settings().corpus_path)
    _run(window.dev_max_papers if dev else window.max_papers, incremental=True)


@app.command()
def ask(question: str, user: str = typer.Option("admin", help="principal id")) -> None:
    """Ask a question; prints the answer with numbered citations to arXiv papers."""
    from sdlcrag.core.models import Principal
    from sdlcrag.generation.graph import answer

    result = answer(question, Principal(user_id=user))
    typer.echo(f"\n{result.text}\n")
    for src in result.sources:
        if src.number in result.cited:
            where = f"({src.section}, p.{src.page})"
            typer.echo(f"[{src.number}] [{src.license_class}] {src.title} {where} {src.url}")


@app.command()
def extract(
    all_papers: bool = typer.Option(
        False, "--all", help="check every paper in the window (up-to-date facts are skipped)"
    ),
) -> None:
    """Extract SDLC phases, techniques, models and benchmarks for indexed papers."""
    instance = _dagster_instance()
    keys = (
        list(instance.get_dynamic_partitions(PAPERS_PARTITION))
        if all_papers
        else _missing(instance, "paper_facts")
    )
    _materialize("extract facts", instance, keys)
    _resolve(instance)


GOLDEN_PATH = get_settings().golden_path
REPORTS_DIR = get_settings().reports_dir


@app.command()
def golden() -> None:
    """Synthesize the golden set from open-licensed papers with DeepEval (review before use)."""
    from sdlcrag.evaluation.golden import synthesize_goldens

    typer.echo(f"wrote {synthesize_goldens(GOLDEN_PATH)} goldens to {GOLDEN_PATH}")


@app.command("tune-retrieval")
def tune_retrieval() -> None:
    """Sweep retrieval candidates / top-k / reranking on the golden set (local, no LLM cost)."""
    from sdlcrag.evaluation.retrieval_sweep import sweep

    rows = sweep(load_golden(GOLDEN_PATH))
    typer.echo("| candidates | top_k | rerank | MRR | paper recall | paper precision |")
    typer.echo("|---|---|---|---|---|---|")
    for r in rows:
        n = r.candidates or "-"
        typer.echo(f"| {n} | {r.top_k} | {r.rerank} | {r.mrr} | {r.recall} | {r.precision} |")


@app.command("eval")
def evaluate(
    limit: int | None = typer.Option(None, help="evaluate only the first N goldens"),
    baseline: bool = typer.Option(
        False, help="also run the long-context baseline (~$0.45 per question at 20 papers)"
    ),
) -> None:
    """Run the RAG evaluation (DeepEval metrics + deterministic checks) and write a report."""
    from sdlcrag.evaluation.runner import (
        run_baseline,
        run_evaluation,
        summary_markdown,
        write_report,
    )

    goldens = load_golden(GOLDEN_PATH)[:limit]
    typer.echo(f"evaluating {len(goldens)} goldens...")
    report = run_evaluation(goldens)
    path = write_report(report, REPORTS_DIR)  # saved before the (costly) baseline starts
    if baseline:
        typer.echo("running the long-context baseline...")
        report = run_baseline(goldens, report)
        path = write_report(report, REPORTS_DIR)
    typer.echo(summary_markdown(report))
    typer.echo(f"report: {path}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
    reload: bool = typer.Option(False, help="restart on code changes (development)"),
) -> None:
    """Run the HTTP API for the web front end (`web/`)."""
    import uvicorn

    uvicorn.run("sdlcrag.api.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
