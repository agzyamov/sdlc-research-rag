# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Primary: AI-in-SDLC practitioners — engineering leads, architects and AI-in-software-engineering specialists. They open the app when they need evidence fast: "what does recent research say about X?", with citations they can check before repeating a claim to their team, plus a sense of where research is concentrated across the software lifecycle.

Secondary: software-engineering researchers doing literature work (finding related papers, comparing methods and benchmarks).

## Product Purpose
SDLC Research RAG answers questions about recent arXiv research on AI in software engineering (cs.SE, LLM and agent topics, since 2023) and shows the research landscape: papers per SDLC phase, the most used techniques, models and benchmarks, and a knowledge graph linking papers to them. Success means a practitioner gets a correct, checkable answer in seconds and can trust it because every claim points to its source.

## Positioning
- **Every claim is cited.** Answers come only from retrieved paper passages, with inline [n] citations that link to the arXiv paper, section and page. "The sources do not cover this" is a valid, expected answer; the app never fills gaps from general knowledge.
- **Measured quality.** The app shows its own evaluation instead of asking for trust: faithfulness, answer relevancy, contextual precision and recall, correctness, cost and latency per question, and a comparison against a long-context baseline.

## Operating Context
- Used on a laptop or desktop during research, architecture or strategy work; answers are read, checked against the cited paper, and reused in discussions and documents.
- The corpus is a rolling window of the 20 newest matching arXiv papers (kept small for the LLM token budget), updated daily without a rebuild.
- Demo users (alice: public, open-licensed papers only; bob and admin: internal, all papers) are switched in the header to show access control. This is a demo switcher, not authentication.

## Capabilities and Constraints
- Chat: single-turn questions answered from hybrid retrieval with reranking; streamed answer text, then the cited sources.
- License-aware access: answers, charts and the graph only use papers the current user may read (OpenFGA; Creative Commons papers are open, arXiv non-exclusive-license papers are restricted to the internal group). Restricted content must never reach a public user.
- Landscape: papers per SDLC phase (numbered in lifecycle order: requirements, design, implementation, testing, code review, deployment & operations, maintenance & evolution, process & management), top techniques, models and benchmarks.
- Knowledge graph: papers linked to their phases, techniques, models and benchmarks.
- Evaluation: the latest report from `sdlcrag eval` (summary and per-question scores, targets, cost, latency, optional long-context baseline).
- Figures in papers are described by a vision model and searchable like text.
- Technical: React + TypeScript front end in `web/` (assistant-ui chat, shadcn/ui, Tremor bar lists, Sigma.js) over a FastAPI API (`sdlcrag.api`); the web app is presentation only and holds no business rules (ADR-0019).
- Open decisions: multi-turn conversation (currently each question is answered on its own); real authentication in front of the API.

## Brand Commitments
- Name: **SDLC Research RAG**.
- A standalone open-source app (Apache-2.0).

## Evidence on Hand
- Evaluation reports: `eval/reports/latest.json` (generated; gitignored) and the summary in `eval/README.md`.
- Golden questions: `eval/golden_qa.jsonl` (synthetic questions from open-licensed papers plus hand-written cross-paper and access-control questions).
- No testimonials, users, customers or third-party benchmarks of the app exist; do not fabricate any. Paper text must not be redistributed beyond what the license allows (restricted papers are shown only to internal users).

## Product Principles
1. Checkable over impressive: a claim without a visible source does not ship.
2. Honest absence: saying "not covered by the sources" beats a fluent guess.
3. Show the measurement: quality, cost and limits are visible, not hidden.
4. Access is part of the answer: who you are changes what you see, and the UI makes that legible.
5. Fast to evidence: the shortest path from question to the cited passage.

## Accessibility & Inclusion
- Required standard: WCAG 2.1 AA.
- Desktop-first; mobile must remain usable.
- Light and dark themes are both first-class (currently following the OS setting).
- Identity in charts and the graph is never color-only (legends, labels, tables).
