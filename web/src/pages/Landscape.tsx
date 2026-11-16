import { BarList } from '@/components/tremor/bar-list'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useState } from 'react'
import { asUser, type Landscape, type Slice, useLandscape } from '@/lib/api'
import { phaseColor } from '@/lib/colors'
import { type FilterKey, useSelection } from '@/lib/selection'
import PaperPanel from '@/pages/PaperPanel'

const TOP_N = 10
const SHOW_ALL_UP_TO = 25 // short lists are never truncated (honest absence)
const papers = (v: number) => `${v} ${v === 1 ? 'paper' : 'papers'}`
const LISTS: [Exclude<keyof Landscape, 'sdlc_phases' | 'total_papers'>, FilterKey, string][] = [
  ['techniques', 'technique', 'Techniques'],
  ['models', 'model', 'Models'],
  ['benchmarks', 'benchmark', 'Benchmarks'],
]

function useLandscapeFor(user: string, filters: Record<string, string | undefined>) {
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
  return useLandscape(
    params,
    asUser<Landscape>(user, `/api/landscape?${new URLSearchParams(params as Record<string, string>)}`),
  )
}

function LoadingCards() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading the landscape">
      <Skeleton className="h-72 w-full rounded-lg" />
      <div className="grid gap-4 xl:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-80 rounded-lg" />
        ))}
      </div>
    </div>
  )
}

export default function LandscapePage({ user }: { user: string }) {
  const { filters, active, toggle } = useSelection()
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const { phase, technique, model, benchmark } = filters
  // The lifecycle strip ignores its own dimension (phase) so selecting a phase never
  // collapses it; the fact lists are filtered by everything that is selected.
  const strip = useLandscapeFor(user, { technique, model, benchmark })
  const lists = useLandscapeFor(user, { phase, technique, model, benchmark })

  // Full skeleton only on the very first load; later selections keep the previous data.
  if (strip.isPending && !strip.data)
    return (
      <div className="mx-auto max-w-7xl p-4">
        <LoadingCards />
      </div>
    )
  if (strip.isError || !strip.data)
    return (
      <div className="p-4 text-sm">
        <p>Couldn't load the research landscape.</p>
        <Button variant="outline" size="sm" className="mt-2" onClick={() => strip.refetch()}>
          Try again
        </Button>
      </div>
    )

  const phases = strip.data.sdlc_phases
  const phaseLabels = Object.fromEntries(phases.map((p) => [p.phase, p.label]))
  const tint = phase ? phaseColor(phase) : undefined
  // Every caption names the full scope it counts over, so a quoted count is never
  // read without its filters ("within 4. Testing, with LLM agents").
  const scope = (keys: FilterKey[]) =>
    [
      keys.includes('phase') && phase && `within ${phaseLabels[phase]}`,
      keys.includes('technique') && technique && `with ${technique}`,
      keys.includes('model') && model && `using ${model}`,
      keys.includes('benchmark') && benchmark && `on ${benchmark}`,
    ]
      .filter(Boolean)
      .join(', ')
  const stripScope = scope(['technique', 'model', 'benchmark'])
  const listScope = scope(['phase', 'technique', 'model', 'benchmark'])
  const scoped = lists.data ?? strip.data
  const updating = strip.isFetching || lists.isFetching
  // a paper selection opens the panel but does not filter the landscape
  const narrowed = Boolean(phase || technique || model || benchmark)
  const hidden = strip.data.corpus_papers - strip.data.total_papers

  return (
    <div
      aria-busy={updating}
      className={`mx-auto grid max-w-7xl items-start gap-4 p-4 ${active ? 'lg:grid-cols-[minmax(0,1fr)_400px]' : ''}`}
    >
      <div
        className={`min-w-0 space-y-4 transition-opacity duration-150 ${lists.isPlaceholderData ? 'opacity-60' : ''}`}
      >
        <p className="text-muted-foreground text-sm">
          <span className="text-foreground font-medium tabular-nums">{scoped.total_papers}</span>
          {!narrowed && hidden > 0 && (
            <>
              {' '}
              of <span className="tabular-nums">{strip.data.corpus_papers}</span>
            </>
          )}{' '}
          {scoped.total_papers === 1 ? 'paper' : 'papers'} <b className="text-foreground">{user}</b>{' '}
          may read{narrowed ? (scoped.total_papers === 1 ? ' matches the selection' : ' match the selection') : ''}
          {!narrowed && hidden > 0 && (
            <>
              {' '}
              · <span className="tabular-nums">{hidden}</span> internal-only (arXiv licence)
            </>
          )}
          .{' '}
          {active ? 'Click more to narrow, or a filter chip to remove it.' : 'Click a phase, technique, model or benchmark to see its papers.'}
          {active && (
            <button
              type="button"
              className="text-primary ml-2 rounded-sm underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              onClick={() => document.getElementById('paper-panel-heading')?.focus()}
            >
              Jump to papers
            </button>
          )}
        </p>

        <Card>
          <CardHeader>
            <CardTitle role="heading" aria-level={2}>
              Papers per SDLC phase
            </CardTitle>
            <CardDescription>
              {stripScope ? `Papers ${stripScope}, per phase` : 'Papers per phase'}, in lifecycle
              order. A paper can target up to three phases, so phases add up to more than the
              paper count.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BarList
              aria-label="Papers per SDLC phase"
              sortOrder="none"
              data={phases.map((p) => ({
                key: p.phase,
                name: p.label,
                value: p.count,
                color: phaseColor(p.phase),
              }))}
              selectedKey={phase ?? null}
              valueLabel={papers}
              onValueChange={(item) => toggle('phase', item.key!)}
            />
          </CardContent>
        </Card>

        <div className="grid gap-4 xl:grid-cols-3">
          {LISTS.map(([field, key, title]) => {
            const items = scoped[field] as Slice[]
            const expandable = items.length > SHOW_ALL_UP_TO
            const showAll = !expandable || expanded[field]
            const shown = showAll ? items : items.slice(0, TOP_N)
            return (
              <Card key={field} className="min-w-0">
                <CardHeader>
                  <CardTitle role="heading" aria-level={2}>
                    {title}
                  </CardTitle>
                  <CardDescription>
                    {items.length === 0
                      ? `None${listScope ? ` ${listScope}` : ''}.`
                      : `${showAll ? `All ${items.length}` : `Top ${TOP_N} of ${items.length}`}, by papers${listScope ? `, ${listScope}` : ''}. Ties in name order.`}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {items.length ? (
                    <BarList
                      aria-label={title}
                      data={shown.map((s) => ({ name: s.label, value: s.count }))}
                      barColor={tint}
                      valueLabel={papers}
                      selectedKey={filters[key] ?? null}
                      onValueChange={(item) => toggle(key, item.name)}
                    />
                  ) : null}
                  {expandable && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-2"
                      aria-expanded={showAll}
                      onClick={() => setExpanded((e) => ({ ...e, [field]: !showAll }))}
                    >
                      {showAll ? `Show top ${TOP_N}` : `Show all ${items.length}`}
                    </Button>
                  )}
                  {items.length ? null : (
                    <p className="text-muted-foreground text-sm">
                      None named in the papers {user} may read
                      {active ? ' that match the selection' : ''}.
                    </p>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
      <PaperPanel
        user={user}
        phaseLabels={phaseLabels}
        className="lg:sticky lg:top-4 lg:h-[calc(100dvh-7.5rem)]"
      />
    </div>
  )
}
