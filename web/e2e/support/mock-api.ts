/**
 * Typed stand-in for the sdlcrag API (mocked mode). Playwright's routeFromHAR cannot be used:
 * it matches on URL and method only, while access control depends on the X-Demo-User header.
 * Response shapes are the orval-generated contract types, so contract changes break here too.
 */
import type { Page, Route } from '@playwright/test'
import type {
  DemoPrincipal,
  EvalReport,
  GraphData,
  Landscape,
  PaperSummary,
} from '../../src/lib/api/generated'

const PHASES: [string, string][] = [
  ['requirements', '1. Requirements'],
  ['design', '2. Design'],
  ['implementation', '3. Implementation'],
  ['testing', '4. Testing'],
  ['code_review', '5. Code review'],
  ['deployment_operations', '6. Deployment & operations'],
  ['maintenance_evolution', '7. Maintenance & evolution'],
  ['process_management', '8. Process & management'],
]

const paper = (
  id: string,
  title: string,
  open: boolean,
  facts: Pick<PaperSummary, 'sdlc_phases' | 'techniques' | 'models' | 'benchmarks'>,
): PaperSummary => ({
  paper_id: id,
  title,
  url: `https://arxiv.org/abs/${id}`,
  license_class: open ? 'open' : 'restricted',
  published: `2026-11-${id.slice(-2)}`,
  // every fact gets a quote except the last technique (exercises "no supporting sentence")
  evidence: (['sdlc_phases', 'techniques', 'models', 'benchmarks'] as const).flatMap((kind) =>
    facts[kind].map((name, i) => ({
      kind,
      name,
      quote:
        kind === 'techniques' && i === facts[kind].length - 1 && i > 0
          ? ''
          : `We study ${name} in this work.`,
    })),
  ),
  ...facts,
})

export const PAPERS: PaperSummary[] = [
  paper('2611.00001', 'Agents That Test Their Own Patches', true, {
    sdlc_phases: ['testing', 'implementation'],
    techniques: ['LLM agents', 'self-correction'],
    models: ['GPT-4o'],
    // a long name, as real extraction produces, exercises label truncation (AC-25)
    benchmarks: ['SWE-bench Pro', '1,065 synthetic LLM-labelled items from the support queue'],
  }),
  paper('2611.00002', 'Visual Diffs for Reviewing Agent Changes', true, {
    sdlc_phases: ['code_review', 'maintenance_evolution'],
    techniques: ['LLM agents'],
    models: [],
    benchmarks: [],
  }),
  paper('2611.00003', 'Robustness of Taint Tracking Under Rewrites', false, {
    sdlc_phases: ['testing', 'code_review'],
    techniques: ['static analysis'],
    models: ['Claude Opus 5.5'],
    benchmarks: [],
  }),
  paper('2611.00004', 'From Requirements to Configuration with LLMs', true, {
    sdlc_phases: ['requirements', 'design'],
    techniques: ['prompt engineering'],
    models: [],
    benchmarks: [],
  }),
  paper('2611.00005', 'Guided Generation of Kernel Patches', false, {
    sdlc_phases: ['maintenance_evolution', 'implementation'],
    techniques: ['prompt engineering', 'guided code generation'],
    models: ['Qwen2.5-Coder 7B'],
    benchmarks: ['Coccinelle semantic patches'],
  }),
]

export const PRINCIPALS: DemoPrincipal[] = [
  { id: 'alice', description: 'public user; sees open-licensed papers only', groups: [] },
  { id: 'bob', description: 'internal researcher (group:internal); sees all papers', groups: ['internal'] },
  { id: 'admin', description: 'internal administrator', groups: ['internal'] },
]

export const EVAL_REPORT: EvalReport = {
  created: '2026-11-16T08:58:08',
  judge: 'AzureChatOpenAI:claude-sonnet',
  summary: {
    Faithfulness: 0.99,
    'Answer Relevancy': 0.95,
    'Contextual Precision': 0.87,
    'Contextual Recall': 0.79,
    Correctness: 0.71,
    'Source hit rate': 1,
    'ACL leaks': 0,
  },
  items: [
    {
      id: 'acl-001',
      question: 'How robust is CodeQL taint tracking against LLM-rewritten code?',
      principal: 'alice',
      answer: 'The sources do not cover this.',
      sources: [],
      scores: {},
      source_hit: null,
      acl_leak: false,
      input_tokens: 900,
      output_tokens: 40,
      cost_usd: 0.002,
      latency_s: 4.1,
    },
    {
      id: 'x-003',
      question: 'What evaluation pitfalls do papers report when benchmarking LLM-based systems?',
      principal: 'alice',
      answer: 'Partial answer [1].',
      sources: [],
      scores: {
        Faithfulness: 1,
        'Answer Relevancy': 0.9,
        'Contextual Precision': 0.17,
        'Contextual Recall': 0,
        Correctness: 0.1,
      },
      source_hit: true,
      acl_leak: null,
      input_tokens: 4100,
      output_tokens: 300,
      cost_usd: 0.015,
      latency_s: 11.6,
    },
  ],
  baseline_summary: {},
  baseline_items: [],
}

const readable = (user: string) =>
  user === 'alice' ? PAPERS.filter((p) => p.license_class === 'open') : PAPERS

const FILTER_FIELDS: Record<string, keyof PaperSummary> = {
  phase: 'sdlc_phases',
  technique: 'techniques',
  model: 'models',
  benchmark: 'benchmarks',
}

function scoped(user: string, params: URLSearchParams) {
  return readable(user).filter(
    (p) =>
      Object.entries(FILTER_FIELDS).every(([key, field]) => {
        const value = params.get(key)
        return !value || (p[field] as string[]).includes(value)
      }) && (!params.get('paper') || p.paper_id === params.get('paper')),
  )
}

function counts(papers: PaperSummary[], field: keyof PaperSummary) {
  const tally = new Map<string, number>()
  for (const p of papers) for (const v of p[field] as string[]) tally.set(v, (tally.get(v) ?? 0) + 1)
  return [...tally].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
}

function landscape(papers: PaperSummary[]): Landscape {
  const phases = new Map(counts(papers, 'sdlc_phases'))
  const top = (field: keyof PaperSummary) =>
    counts(papers, field).map(([label, count]) => ({ label, count }))
  return {
    total_papers: papers.length,
    corpus_papers: PAPERS.length,
    sdlc_phases: PHASES.map(([phase, label]) => ({ phase, label, count: phases.get(phase) ?? 0 })),
    techniques: top('techniques'),
    models: top('models'),
    benchmarks: top('benchmarks'),
  }
}

function graph(papers: PaperSummary[]): GraphData {
  const nodes = new Map<string, GraphData['nodes'][number]>()
  const edges: GraphData['edges'] = []
  const add = (id: string, type: string, label: string) => {
    const node = nodes.get(id) ?? { id, type, label, degree: 0 }
    node.degree += 1
    nodes.set(id, node)
  }
  const kinds: [keyof PaperSummary, string, string][] = [
    ['sdlc_phases', 'phase', 'ADDRESSES'],
    ['techniques', 'technique', 'USES'],
    ['models', 'model', 'USES'],
    ['benchmarks', 'benchmark', 'EVALUATED_ON'],
  ]
  const phaseLabel = Object.fromEntries(PHASES)
  for (const p of papers)
    for (const [field, type, rel] of kinds)
      for (const v of p[field] as string[]) {
        add(p.paper_id, 'paper', p.title)
        add(v, type, type === 'phase' ? phaseLabel[v] : v)
        edges.push({ source: p.paper_id, target: v, label: rel })
      }
  return { total_papers: papers.length, nodes: [...nodes.values()], edges }
}

/** assistant-ui data-stream body: text deltas (0:) then one source part (h:) per citation. */
function chatStream(user: string, question: string) {
  const candidates = readable(user)
  const asksRestricted = /taint|codeql/i.test(question)
  const cited = asksRestricted && user === 'alice' ? [] : candidates.slice(0, 2)
  const text = cited.length
    ? `Two papers address this: ${cited[0].title} [1] and ${cited[1].title} [2].`
    : 'The sources available to you do not cover this question.'
  const lines = text.match(/.{1,12}/g)!.map((t) => `0:${JSON.stringify(t)}`)
  cited.forEach((p, i) =>
    lines.push(
      `h:${JSON.stringify({ sourceType: 'url', id: String(i + 1), url: p.url, title: `[${i + 1}] ${p.title} · Abstract, p. 1${p.license_class === 'restricted' ? ' · restricted' : ''}` })}`,
    ),
  )
  return lines.join('\n') + '\n'
}

export type MockOptions = { fail?: RegExp }

export async function mockApi(page: Page, options: MockOptions = {}) {
  // Match the API path only: a glob like **/api/** also hits Vite's /src/lib/api/* modules.
  await page.route((url) => url.pathname.startsWith('/api/'), async (route: Route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (options.fail?.test(url.pathname))
      return route.fulfill({ status: 500, json: { detail: 'mock failure' } })
    const user = request.headers()['x-demo-user'] ?? ''
    const known = PRINCIPALS.some((p) => p.id === user)
    const needsUser = !['/api/principals', '/api/eval'].includes(url.pathname)
    if (needsUser && !known) return route.fulfill({ status: 403, json: { detail: 'unknown demo user' } })
    switch (url.pathname) {
      case '/api/principals':
        return route.fulfill({ json: PRINCIPALS })
      case '/api/eval':
        return route.fulfill({ json: EVAL_REPORT })
      case '/api/landscape':
        return route.fulfill({ json: landscape(scoped(user, url.searchParams)) })
      case '/api/papers':
        return route.fulfill({ json: scoped(user, url.searchParams) })
      case '/api/graph':
        return route.fulfill({ json: graph(readable(user)) })
      case '/api/chat': {
        const body = request.postDataJSON() as { messages: { role: string; content: unknown }[] }
        const last = [...body.messages].reverse().find((m) => m.role === 'user')
        const text = Array.isArray(last?.content)
          ? (last.content as { text?: string }[]).map((c) => c.text ?? '').join('')
          : String(last?.content ?? '')
        return route.fulfill({ contentType: 'text/plain; charset=utf-8', body: chatStream(user, text) })
      }
    }
    return route.fulfill({ status: 404, json: { detail: 'not mocked' } })
  })
}
