# ADR-0010: SEC 10-K filings as the corpus

- Status: **Superseded** by [ADR-0013](0013-dataset-arxiv-llm4se.md) (2026-11-15)
- Modules: `ingestion` (fetch), `evaluation` (golden set)

## Decision
Use the latest annual 10-K reports of five large US companies (Apple, Microsoft, NVIDIA, Tesla, Alphabet) from SEC EDGAR. The list is in `data/sources.yaml`, and links and terms are in `data/README.md`.

## Rationale
- Public, free, and authoritative, with stable URLs.
- Rich quantitative content (segment revenue suits pie charts) and entities (subsidiaries, suppliers, competitors, risks suit a knowledge graph).
- **Ground truth available**: XBRL companyfacts gives exact numbers to score extraction; FinanceBench provides 10-K Q&A to seed the golden set.
- Contains tables and some graphics (multimodal); documents are naturally separable by company and filing, which suits the ACL demo.

## Consequences
− SEC fair-access policy: a descriptive User-Agent and ≤10 requests/s. Enforced in `providers.edgar_client`.
