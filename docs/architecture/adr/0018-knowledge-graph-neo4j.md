# ADR-0018: Knowledge graph in Neo4j with neo4j-graphrag entity resolution

- Status: Accepted (2026-11-16). Refines ADR-0016 (building-block map: facet counts, knowledge graph).
- Modules: `indexing` widened to "vector store + knowledge graph store" (`indexing.graph`); `extraction` reads and writes facts through it.

## Context
Extracted facts lived as a payload on each paper's abstract point in Qdrant. Charts counted them with the Qdrant Facet API, and the knowledge graph was rebuilt with NetworkX on every page view. Free-text names split one concept into several values ("LLM agent" / "LLM agents", "RAG" / "retrieval-augmented generation", "LLM" listed as a technique). Charts at 2k papers would be fragmented. A first fix was a hand-written alias map plus normalization code. That conflicts with the OSS-first rule (ADR-0016), since entity resolution is a solved problem in graph tooling.

## Decision
- **Neo4j Community** (with APOC core) is the knowledge graph store: `(:Paper)-[:ADDRESSES]->(:Phase)`, `-[:USES]->(:Technique|:Model)`, `-[:EVALUATED_ON]->(:Benchmark)`. Fact nodes are written with `MERGE` on `name`, so exact duplicates never arise.
- **neo4j-graphrag** (`FuzzyMatchResolver`, RapidFuzz `WRatio`) merges spelling variants of technique names after each extraction run. This runs as the Dagster asset `entity_resolution`. The threshold is 0.95: at 0.90 WRatio's partial matching merged substrings ("LLM" into "LLM agents", "retrieval" into "retrieval-augmented generation").
- Synonyms and acronyms are handled at the source: the extraction prompt asks for spelled-out acronyms and forbids generic terms ("LLM", "large language models"). `FACTS_FORMAT` 2 re-extracts all papers.
- Models and benchmarks are proper names, so they are matched exactly only: "Claude Opus 5" and "Claude Opus 5.5" are different models.
- Charts and the graph are Cypher reads filtered by the principal's readable paper ids from OpenFGA, so they stay license-aware.

## Alternatives
- **Alias map + normalization code**: rejected as custom code for a library-solved problem.
- **`SpaCySemanticMatchResolver`** (neo4j-graphrag): tried and rejected. General-purpose spaCy vectors score "RAG" vs "retrieval-augmented generation" at 0.26, but "experience memory" vs "graph-based memory" at 0.60, so any threshold merges wrong pairs first.
- **Fixed technique taxonomy as a schema enum**: clean charts with no resolution step, but no discovery of new techniques. Kept as an option if fuzzy resolution plus the prompt is not enough at 2k papers.
- **Microsoft GraphRAG / LightRAG**: they include entity merging, but would replace the retrieval pipeline.
- **`SimpleKGPipeline`** (neo4j-graphrag): extracts per chunk, which costs far more than one abstract-level call per paper, and has no LangChain model adapter for the gateway.

## Consequences
+ One canonical node per concept; charts and the graph read a persistent store instead of rebuilding per request.
+ The graph can be explored in Neo4j Browser, and graph queries become available for later features.
− One more service (Neo4j) in the allocation view.
− Fuzzy resolution only fixes spelling. Synonym quality depends on the prompt and is to be re-checked on the 2k corpus.
