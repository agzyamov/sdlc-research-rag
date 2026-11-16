import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useEvaluation } from '@/lib/api'

// QA scenario targets (docs/architecture/04-quality-attributes.md), as in evaluation.runner.
const TARGETS: Record<string, number> = {
  Faithfulness: 0.85,
  'Answer Relevancy': 0.8,
  'Contextual Precision': 0.75,
  'Contextual Recall': 0.75,
  Correctness: 0.7,
}
const METRICS = Object.keys(TARGETS)

const fmt = (v: number | undefined, digits = 2) => (v === undefined ? '–' : v.toFixed(digits))

function Score({ name, value }: { name: string; value: number | undefined }) {
  const below = value !== undefined && TARGETS[name] !== undefined && value < TARGETS[name]
  return (
    <span className={below ? 'text-destructive font-medium' : undefined}>
      {fmt(value)}
      {below && <span className="sr-only"> (below target)</span>}
    </span>
  )
}

export default function EvaluationPage() {
  const { data, error, isPending: loading } = useEvaluation({ query: { select: (r) => r.data } })
  const status = error?.response?.status
  if (loading) return <p className="text-muted-foreground p-4 text-sm">Loading…</p>
  if (status === 404 || (!error && !data))
    return (
      <p className="text-muted-foreground p-4 text-sm">
        No evaluation report yet: run <code>uv run sdlcrag eval</code>.
      </p>
    )
  if (error || !data) return <p className="text-destructive p-4 text-sm">{error?.message}</p>

  const base = data.baseline_summary ?? {}
  const hasBase = Object.keys(base).length > 0
  const rows = Object.entries(data.summary)

  return (
    <div className="mx-auto grid max-w-6xl gap-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle>Summary</CardTitle>
          <CardDescription>
            Run {data.created}, {data.items.length} questions, judge {data.judge}. Scores below
            target are marked red.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead className="text-right">RAG</TableHead>
                {hasBase && <TableHead className="text-right">Long-context baseline</TableHead>}
                <TableHead className="text-right">Target</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map(([name, value]) => (
                <TableRow key={name}>
                  <TableCell>{name}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    <Score name={name} value={value} />
                  </TableCell>
                  {hasBase && (
                    <TableCell className="text-right tabular-nums">
                      <Score name={name} value={base[name]} />
                    </TableCell>
                  )}
                  <TableCell className="text-muted-foreground text-right tabular-nums">
                    {name === 'ACL leaks' ? '0' : TARGETS[name] ? `≥ ${TARGETS[name]}` : '–'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Per question</CardTitle>
          <CardDescription>
            Source hit: a paper the question was written from is among the retrieved sources.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Question</TableHead>
                <TableHead>User</TableHead>
                {METRICS.map((m) => (
                  <TableHead key={m} className="text-right">
                    {m.replace('Contextual ', 'Ctx ')}
                  </TableHead>
                ))}
                <TableHead>Source hit / leak</TableHead>
                <TableHead className="text-right">Cost</TableHead>
                <TableHead className="text-right">Latency</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="max-w-md whitespace-normal">
                    <div className="text-muted-foreground font-mono text-xs">{item.id}</div>
                    {item.question}
                  </TableCell>
                  <TableCell>{item.principal}</TableCell>
                  {METRICS.map((m) => (
                    <TableCell key={m} className="text-right tabular-nums">
                      <Score name={m} value={item.scores?.[m]} />
                    </TableCell>
                  ))}
                  <TableCell>
                    {item.acl_leak !== null
                      ? item.acl_leak
                        ? 'LEAK'
                        : 'no leak'
                      : item.source_hit
                        ? 'hit'
                        : 'miss'}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    ${fmt(item.cost_usd, 3)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{fmt(item.latency_s, 1)} s</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
