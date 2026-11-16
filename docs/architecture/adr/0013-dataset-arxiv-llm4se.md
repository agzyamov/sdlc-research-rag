# ADR-0013: arXiv papers on AI for software engineering as the corpus

- Status: Accepted (2026-11-15). Supersedes [ADR-0010](0010-dataset-sec-10k-superseded.md).
- Modules: `providers` (arXiv clients), `ingestion` (harvest), `access` (license policy), `evaluation`

## Context
The app's purpose is research intelligence on **AI across the software development lifecycle**. The corpus must be:
- real-scale, current and growing
- PDF-based, for tables and figures
- legally usable
- able to supply ground truth for evaluation

The original choice (SEC 10-K filings) was off-domain. Smaller requirements-document sets (PURE, 79 PDFs) were judged too small.

## Decision
- **Corpus:** arXiv cs.SE papers since 2023-01-01 that mention LLMs, foundation models or agents (`data/corpus.yaml`), limited to a **rolling window of the newest 2,000 papers** (20 for development; 300 and 2k only after every step works on the small corpus). The full set (~10–20k) would take 2–3 days to process locally for no extra demo value; the window keeps ingestion overnight-sized and makes eviction a real incremental-delete case. `window.max_papers` scales it by configuration.
- **Initial load:** arXiv search API or the Kaggle metadata snapshot (the most popular document dataset on Kaggle related to the domain). PDFs come from arXiv or the public GCS bulk mirror.
- **Incremental updates:** OAI-PMH `ListRecords` (`set=cs`, `from=<last sync>`) returns new papers, new versions and withdrawals. `indexing.Manifest` diffs content hashes so only changed chunks are re-embedded or deleted, and the collection is never rebuilt (QA-5).
- **Access control:** derived from each paper's license. CC-licensed papers belong to `collection:open` (everyone); arXiv non-exclusive papers belong to `collection:restricted` (`group:internal`).
- **No redistribution:** git holds ids and metadata only.

## Alternatives considered
| Option | Why not |
|---|---|
| SEC 10-K filings (ADR-0010) | Off-domain for the product's audience |
| PURE requirements specs (79 PDFs, CC-BY-4.0) | Too small (~1M tokens, so it fits in one long-context prompt); documents are dated |
| Kaggle Stack Overflow / StackSample / GitHub Issues | Not PDFs; frozen in 2016–2019, before LLM-assisted development |
| Public Jira Dataset (2.7M issues, CC-BY-4.0) | Strong for backlog analytics, but not documents or PDFs; a candidate for a later second corpus |

## Consequences
+ Live, growing corpus; incremental updates use real daily changes.
+ Rich multimodal content: architecture diagrams, result charts, tables.
+ Natural, realistic access-control rule (license-aware retrieval).
− Rate-limited fetching (3 s/request): the initial load runs in batches or uses the bulk mirror.
− Heterogeneous PDF layouts: Docling plus figure descriptions; parse failures are logged and skipped.
