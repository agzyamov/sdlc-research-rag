# Datasets

## Primary corpus: arXiv papers on AI for software engineering (LLM4SE)

| | |
|---|---|
| Source | [arXiv](https://arxiv.org), category [cs.SE (Software Engineering)](https://arxiv.org/list/cs.SE/recent) |
| Metadata snapshot | [Kaggle: arXiv Dataset (Cornell University)](https://www.kaggle.com/datasets/Cornell-University/arxiv): about 2.8M papers, CC0, refreshed weekly |
| Scope | The **newest 2,000** cs.SE papers (primary or cross-listed, since 2023-01-01) whose title or abstract mentions LLMs, foundation models or agents. Development uses the newest 20 (every step is verified there before larger runs). Rolling window: daily updates add new papers and evict the oldest. Definition: [`corpus.yaml`](corpus.yaml) |
| Full text | PDFs from `arxiv.org/pdf/<id>` or the public bulk mirror `storage.googleapis.com/arxiv-dataset` (see the Kaggle page) |
| Updates | [arXiv OAI-PMH](https://info.arxiv.org/help/oa/index.html) at `https://oaipmh.arxiv.org/oai` (`ListRecords`, `set=cs`, `from=<last sync>`) |
| Search API | [arXiv API](https://info.arxiv.org/help/api/index.html) at `https://export.arxiv.org/api/query` |

### Terms and licensing
- arXiv API [terms of use](https://info.arxiv.org/help/api/tos.html): at most one request every 3 seconds; the client enforces this.
- Each paper has its own [license](https://info.arxiv.org/help/license/index.html): CC BY / BY-SA / BY-NC-SA / BY-NC-ND / CC0, or the arXiv non-exclusive distribution license. About half of recent cs papers use the latter.
- **This repository never redistributes papers.** Only arXiv ids and metadata are committed. PDFs, parsed text, figures and indexes are created locally and stay gitignored.
- The app's access control follows the licenses: open-licensed papers are visible to everyone, non-exclusive ones only to internal users (`license_policy` in `corpus.yaml`).

## Evaluation ground truth
| Source | Use |
|---|---|
| arXiv metadata (categories, dates, versions, licenses) | exact ground truth for metadata questions and ACL tests |
| `eval/golden_qa.jsonl` | hand-verified question/answer set over the corpus (see [eval/README.md](../eval/README.md)) |
| Hand-labeled sample (planned, `eval/phase_labels.jsonl`) | SDLC-phase labels for scoring extraction (precision/recall/F1) |

## Local layout
- `data/raw/`: downloaded PDFs and extracted figures (gitignored)
- `data/index/`: ingest manifest, including content hashes and the last OAI-PMH sync date (gitignored). The vectors live in Qdrant.
