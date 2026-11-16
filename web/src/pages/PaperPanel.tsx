import { ExternalLink, Lock, LockOpen, X } from 'lucide-react'
import { type ReactNode, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import type { PaperSummary } from '@/lib/api'
import { phaseColor } from '@/lib/colors'
import { FILTER_LABELS, type FilterKey, useSelectedPapers, useSelection } from '@/lib/selection'
import { useMediaQuery } from '@/lib/useMediaQuery'
import { ShapeIcon, TYPE_SHAPES } from '@/pages/shapes'

type Props = {
  user: string
  /** Display names for slugs, e.g. phase "testing" → "4. Testing". */
  phaseLabels: Record<string, string>
  className?: string
}

const FACT_GROUPS: [keyof PaperSummary, FilterKey, string][] = [
  ['sdlc_phases', 'phase', 'Phases'],
  ['techniques', 'technique', 'Techniques'],
  ['models', 'model', 'Models'],
  ['benchmarks', 'benchmark', 'Benchmarks'],
]

function License({ value }: { value: string }) {
  const open = value === 'open'
  const Icon = open ? LockOpen : Lock
  return (
    <span className="text-muted-foreground inline-flex items-center gap-1 text-xs">
      <Icon className="size-3" aria-hidden />
      {open ? 'Open licence (CC)' : 'Internal only (arXiv licence)'}
    </span>
  )
}

const KIND_LABELS: Record<string, string> = {
  sdlc_phases: 'Phase',
  techniques: 'Technique',
  models: 'Model',
  benchmarks: 'Benchmark',
}
const submitted = (iso: string) =>
  new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric' }).format(
    new Date(`${iso}T00:00:00`),
  )

const quoteOf = (paper: PaperSummary, kind: string, name: string) =>
  paper.evidence.find((e) => e.kind === kind && e.name === name)?.quote ?? ''

/** Why each tag is on the paper: the verbatim abstract quote the extraction cited, in the
 * same order as the chips; a quote that backs several tags says so. */
function Evidence({ paper, phaseLabels }: { paper: PaperSummary; phaseLabels: Props['phaseLabels'] }) {
  if (!paper.evidence.length) return null
  const display = (kind: string, name: string) =>
    kind === 'sdlc_phases' ? (phaseLabels[name] ?? name) : name
  const rows = FACT_GROUPS.flatMap(([field]) =>
    (paper[field] as string[]).map((name) => ({ kind: field as string, name, quote: quoteOf(paper, field, name) })),
  )
  return (
    <details className="group mt-2">
      <summary className="text-muted-foreground hover:text-foreground w-fit cursor-pointer rounded-sm text-xs select-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring focus-visible:ring-2">
        Why these tags? Quotes from the abstract
      </summary>
      <ul className="mt-2 space-y-2">
        {rows.map((e) => {
          const shared = e.quote
            ? rows.filter((o) => o.quote === e.quote && !(o.kind === e.kind && o.name === e.name))
            : []
          return (
            <li key={`${e.kind}:${e.name}`} className="text-xs">
              <span className="inline-flex items-center gap-1 font-medium">
                <ShapeIcon shape={TYPE_SHAPES[e.kind]} color="currentColor" className="size-2.5" />
                {KIND_LABELS[e.kind] ?? e.kind}: {display(e.kind, e.name)}
              </span>
              {e.quote ? (
                <blockquote className="border-border mt-0.5 border-l-2 pl-2">
                  “{e.quote}”
                  {shared.length > 0 && (
                    <span className="text-muted-foreground block not-italic">
                      Same quote also backs: {shared.map((o) => display(o.kind, o.name)).join(', ')}
                    </span>
                  )}
                </blockquote>
              ) : (
                <p className="text-muted-foreground mt-0.5">
                  No supporting sentence found in the abstract (model-extracted).
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </details>
  )
}

function PaperItem({ paper, phaseLabels }: { paper: PaperSummary; phaseLabels: Props['phaseLabels'] }) {
  const { filters, toggle } = useSelection()
  return (
    <li className="border-border/60 border-b py-3 last:border-b-0">
      <a
        href={paper.url}
        target="_blank"
        rel="noreferrer"
        className="group hover:text-primary text-sm leading-snug font-medium underline-offset-2 hover:underline"
      >
        {paper.title}
        <ExternalLink className="ml-1 inline size-3 opacity-60" aria-hidden />
        <span className="sr-only"> (opens arXiv)</span>
      </a>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-muted-foreground font-mono text-xs">arXiv:{paper.paper_id}</span>
        {paper.published && (
          <span className="text-muted-foreground text-xs">Submitted {submitted(paper.published)}</span>
        )}
        <License value={paper.license_class} />
      </div>
      <dl className="mt-2 space-y-1">
        {FACT_GROUPS.map(([field, key, label]) => {
          const values = paper[field] as string[]
          if (!values.length) return null
          return (
            <div key={field} className="flex flex-wrap items-baseline gap-1">
              <dt className="text-muted-foreground mr-1 inline-flex w-24 shrink-0 items-center gap-1 text-xs">
                <ShapeIcon shape={TYPE_SHAPES[field]} color="currentColor" className="size-2.5" />
                {label}
              </dt>
              {values.map((value) => {
                const quote = quoteOf(paper, field, value)
                return (
                  <dd key={value}>
                    <button
                      type="button"
                      aria-pressed={filters[key] === value}
                      aria-description={quote ? undefined : 'no supporting quote in the abstract'}
                      onClick={() => toggle(key, value)}
                      className={`bg-muted hover:bg-accent aria-pressed:bg-foreground aria-pressed:text-background inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${quote ? '' : 'border-muted-foreground/60 border border-dashed'}`}
                    >
                      {key === 'phase' && (
                        <span className="size-2 rounded-[2px]" style={{ background: phaseColor(value) }} />
                      )}
                      {key === 'phase' ? (phaseLabels[value] ?? value) : value}
                    </button>
                  </dd>
                )
              })}
            </div>
          )
        })}
      </dl>
      <Evidence paper={paper} phaseLabels={phaseLabels} />
    </li>
  )
}

function PanelBody({ user, phaseLabels }: Props) {
  const { filters, clear } = useSelection()
  const query = useSelectedPapers(user)
  const label = (key: FilterKey, value: string) =>
    key === 'phase' ? (phaseLabels[value] ?? value) : value

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-1.5 pb-3">
        {Object.entries(filters).map(([key, value]) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              clear(key as FilterKey)
              requestAnimationFrame(() => document.getElementById('paper-panel-heading')?.focus())
            }}
            aria-label={`Remove filter ${FILTER_LABELS[key as FilterKey]}: ${label(key as FilterKey, value!)}`}
            className="bg-secondary hover:bg-accent inline-flex items-center gap-1 rounded-sm px-2 py-1 text-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            <span className="text-foreground/70">{FILTER_LABELS[key as FilterKey]}:</span>
            {label(key as FilterKey, value!)}
            <X className="size-3" aria-hidden />
          </button>
        ))}
      </div>
      <p className="text-muted-foreground pb-1 text-xs" aria-live="polite">
        {query.data
          ? `${query.data.length} ${query.data.length === 1 ? 'paper' : 'papers'} ${user} may read`
          : ' '}
      </p>
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {query.isPending && !query.data ? (
          <div className="space-y-4 py-3" aria-busy="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-11/12" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : query.isError ? (
          <div className="py-3 text-sm">
            <p>Couldn't load the papers.</p>
            <Button variant="outline" size="sm" className="mt-2" onClick={() => query.refetch()}>
              Try again
            </Button>
          </div>
        ) : query.data?.length ? (
          <ul>
            {query.data.map((p) => (
              <PaperItem key={p.paper_id} paper={p} phaseLabels={phaseLabels} />
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground py-3 text-sm">
            None of the papers {user} may read match all of these filters. Remove one to widen
            the set.
          </p>
        )}
      </div>
    </div>
  )
}

/** Papers behind the current selection: an in-flow side panel on desktop, a sheet below lg. */
export default function PaperPanel(props: Props) {
  const { active, clear } = useSelection()
  const desktop = useMediaQuery('(min-width: 1024px)')
  /** Clear, then return focus to the row that was selected (it stays mounted), not <body>. */
  const close = () => {
    const selected = document.querySelector<HTMLElement>('main [aria-pressed="true"]')
    clear()
    requestAnimationFrame(() => selected?.focus())
  }

  useEffect(() => {
    if (!active || !desktop) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (!active) return null
  const header: ReactNode = (
    <>
      <h2 id="paper-panel-heading" tabIndex={-1} className="focus-visible:outline-ring rounded-sm text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2">
        Papers behind the selection
      </h2>
      <p className="text-muted-foreground text-xs">Click a fact to narrow; Esc clears.</p>
    </>
  )
  if (!desktop)
    return (
      <Sheet open onOpenChange={(open) => !open && close()}>
        <SheetContent side="right" className="w-[min(420px,92vw)] p-4">
          <SheetHeader className="p-0 pb-2">
            <SheetTitle>Papers behind the selection</SheetTitle>
            <SheetDescription>Click a fact to narrow.</SheetDescription>
          </SheetHeader>
          <PanelBody {...props} />
        </SheetContent>
      </Sheet>
    )
  return (
    <aside
      aria-label="Papers behind the selection"
      className={`bg-card flex min-h-0 flex-col rounded-lg border p-4 ${props.className ?? ''}`}
    >
      <div className="flex items-start justify-between gap-2 pb-2">
        <div>{header}</div>
        <Button variant="ghost" size="icon" aria-label="Close panel" onClick={close}>
          <X />
        </Button>
      </div>
      <PanelBody {...props} />
    </aside>
  )
}
