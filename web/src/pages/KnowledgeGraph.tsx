import {
  ControlsContainer,
  SigmaContainer,
  useLoadGraph,
  useRegisterEvents,
  useSigma,
  ZoomControl,
} from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import Graph from 'graphology'
import circular from 'graphology-layout/circular'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import noverlap from 'graphology-layout-noverlap'
import { ChevronsUpDown, Search } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { DEFAULT_STYLES } from 'sigma'
import { sdfCircle, sdfDiamond, sdfRectangle, sdfSquare, sdfTriangle } from 'sigma/rendering'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { asUser, type GraphData, useGraph } from '@/lib/api'
import { phaseColor, phaseVar, resolveColor } from '@/lib/colors'
import { type FilterKey, useSelectedPapers, useSelection } from '@/lib/selection'
import { useTheme } from '@/lib/useTheme'
import PaperPanel from '@/pages/PaperPanel'
import { ShapeIcon, TYPE_SHAPES } from '@/pages/shapes'

// Phases wear their lifecycle hue (same as the Landscape) and always show their numbered
// label; every node type also has its own shape (pages/shapes.tsx), so type is never told
// by shade alone.
const TYPES: Record<string, { label: string; token: string; filter: FilterKey }> = {
  paper: { label: 'Paper', token: '--graph-paper', filter: 'paper' },
  phase: { label: 'SDLC phase', token: '', filter: 'phase' },
  technique: { label: 'Technique', token: '--graph-technique', filter: 'technique' },
  model: { label: 'Model', token: '--graph-model', filter: 'model' },
  benchmark: { label: 'Benchmark', token: '--graph-benchmark', filter: 'benchmark' },
}
const PRIMITIVES = {
  nodes: {
    shapes: [sdfCircle(), sdfSquare(), sdfTriangle(), sdfDiamond(), sdfRectangle({ aspectRatio: 1.8 })],
  },
}
type Attrs = Record<string, unknown>
type State = Record<string, boolean>
// Style functions live at module level: react-sigma deep-compares `options` and rebuilds the
// whole Sigma instance when they change, so inline arrows would recreate it every render.
// A function, not a state array: sigma's array predicate means ALL states.
const labelVisibility = (attrs: Attrs, state: State) =>
  state.isHovered || state.isSelected || state.isHighlighted
    ? 'visible'
    : state.isDimmed
      ? 'hidden'
      : attrs.nodeType === 'phase'
        ? 'visible'
        : // long paper titles are labelled on hover/selection only (listed in full in the
          // panel); the overview labels facts and phases
          attrs.nodeType === 'paper'
          ? 'hidden'
          : 'auto'
// the selected node is bigger and sits on a backdrop (halo), so it is findable
const nodeSize = (attrs: Attrs, state: State) =>
  (attrs.size as number) * (state.isSelected ? 1.7 : state.isHovered ? 1.2 : 1)
const backdropVisibility = (_attrs: Attrs, state: State) =>
  state.isSelected || state.isHovered ? 'visible' : 'hidden'
/** cmdk filter: 1 = label starts with the query, 0.8 = a word starts with it, else hidden. */
function findScore(value: string, search: string) {
  const label = value.toLowerCase()
  const query = search.trim().toLowerCase()
  if (!query) return 1
  if (label.startsWith(query) || label.replace(/^\d+\.\s*/, '').startsWith(query)) return 1
  return label.split(/[^a-z0-9.+-]+/).some((word) => word.startsWith(query)) ||
    label.includes(` ${query}`)
    ? 0.8
    : 0
}

const PANEL_WIDTH = 412 // overlay width + gap: the camera keeps the selection clear of it

/** Keyboard path into the graph: search any node and select it (same as clicking it). */
function NodeFinder({ data }: { data: GraphData }) {
  const [open, setOpen] = useState(false)
  const { select } = useSelection()
  // facts and phases first, papers last: a typed term usually names a fact
  const order = ['phase', 'technique', 'model', 'benchmark', 'paper']
  const groups = order.map((type) => [type, TYPES[type]] as const).map(([type, t]) => ({
    type,
    t,
    nodes: data.nodes.filter((n) => n.type === type).sort((a, b) => a.label.localeCompare(b.label)),
  }))
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button variant="outline" size="sm" className="w-64 justify-between font-normal">
            <span className="text-muted-foreground flex items-center gap-2">
              <Search className="size-3.5" aria-hidden /> Find a paper, phase or fact…
            </span>
            <ChevronsUpDown className="size-3.5 opacity-50" aria-hidden />
          </Button>
        }
      />
      <PopoverContent className="w-96 p-0" align="start">
        {/* cmdk's built-in `filter`: whole-word matches only (no fuzzy letter skipping), a
            label starting with the query ranks first. */}
        <Command filter={findScore}>
          <CommandInput placeholder="Type to search…" aria-label="Find a node" />
          <CommandList>
            <CommandEmpty>No matching node.</CommandEmpty>
            {groups.map(({ type, t, nodes }) =>
              nodes.length ? (
                <CommandGroup key={type} heading={t.label}>
                  {nodes.map((n) => (
                    <CommandItem
                      key={n.id}
                      value={`${n.label} ${n.id}`}
                      onSelect={() => {
                        select(t.filter, n.id)
                        setOpen(false)
                      }}
                    >
                      {n.label}
                    </CommandItem>
                  ))}
                </CommandGroup>
              ) : null,
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
const MAX_TITLE = 48

function nodeColor(type: string, id: string) {
  return resolveColor(type === 'phase' ? phaseVar(id) : (TYPES[type]?.token ?? '--graph-paper'))
}

function LoadGraph({ data, theme }: { data: GraphData; theme: string }) {
  const loadGraph = useLoadGraph()
  useEffect(() => {
    const graph = new Graph({ type: 'directed' })
    for (const n of [...data.nodes].sort((a, b) => a.id.localeCompare(b.id))) {
      const label =
        n.type === 'paper' && n.label.length > MAX_TITLE ? `${n.label.slice(0, MAX_TITLE)}…` : n.label
      graph.addNode(n.id, {
        label, // drawn as text on a canvas, never injected as HTML
        size: (n.type === 'paper' ? 5 : 4) + 2.5 * Math.sqrt(n.degree),
        color: nodeColor(n.type, n.id),
        shape: TYPE_SHAPES[n.type] ?? 'circle',
        nodeType: n.type,
      })
    }
    const edgeColor = resolveColor('--graph-edge')
    for (const e of data.edges) graph.mergeEdge(e.source, e.target, { size: 1, color: edgeColor })
    // Deterministic layout: circular seed (sorted node order) refined by ForceAtlas2, so
    // switching user or theme does not reshuffle the picture.
    circular.assign(graph)
    forceAtlas2.assign(graph, {
      iterations: 300,
      settings: {
        ...forceAtlas2.inferSettings(graph),
        barnesHutOptimize: graph.order > 500,
        strongGravityMode: true, // pack disconnected clusters instead of pushing them out
        gravity: 0.6,
      },
    })
    // then push apart overlapping nodes so labels and shapes do not sit on each other
    noverlap.assign(graph, { maxIterations: 200, settings: { margin: 6, ratio: 1.3 } })
    loadGraph(graph)
  }, [data, theme, loadGraph])
  return null
}

/** Click a node to select it (opens the paper panel); the selection's neighbourhood stays
 * bright, everything else dims, and the camera centres on the selected node. */
function Selection({ user }: { user: string }) {
  const sigma = useSigma()
  const registerEvents = useRegisterEvents()
  const { filters, select, clear } = useSelection()
  // The highlight is exactly the panel's paper set (same query and cache entry), plus every
  // selected phase/fact node, so graph and panel never disagree when filters combine.
  const papers = useSelectedPapers(user)
  const paperIds = useMemo(() => papers.data?.map((p) => p.paper_id), [papers.data])
  // camera focus: the most specific selected node. Node ids: papers by arXiv id, facts by
  // name, phases by slug.
  const selected = useMemo(
    () =>
      (['paper', 'technique', 'model', 'benchmark', 'phase'] as FilterKey[])
        .map((k) => filters[k])
        .find(Boolean) ?? null,
    [filters],
  )
  const selectedNodes = useMemo(() => Object.values(filters).filter(Boolean) as string[], [filters])

  useEffect(() => {
    // Test seam (dev builds only, stripped from production): Playwright reads node
    // positions from the Sigma instance to click them (e2e/graph.spec.ts).
    if (import.meta.env.DEV) (window as unknown as { __sigma?: unknown }).__sigma = sigma
  }, [sigma])

  // Register the Sigma handlers once: useRegisterEvents stores them in React state, so
  // re-registering on every render (select/clear are new functions each time) would loop.
  // The handlers read the latest callbacks through a ref.
  const actions = useRef({ select, clear })
  actions.current = { select, clear }
  useEffect(() => {
    registerEvents({
      clickNode: ({ node }) => {
        const type = sigma.getGraph().getNodeAttribute(node, 'nodeType') as string
        actions.current.select(TYPES[type]?.filter ?? 'paper', node)
      },
      clickStage: () => actions.current.clear(),
    })
  }, [registerEvents, sigma])

  useEffect(() => {
    const graph = sigma.getGraph()
    const chosen = selectedNodes.filter((n) => graph.hasNode(n))
    // An active selection with no node in this user's graph is an EMPTY selection (dim all),
    // not "no selection" (e.g. a fact only internal papers have, after switching to alice).
    let keep: Set<string> | null = selectedNodes.length ? new Set() : null
    if (chosen.length) {
      keep = new Set(chosen)
      // a single paper: show its facts; otherwise: the papers the panel lists
      if (filters.paper && chosen.length === 1)
        for (const n of graph.neighbors(filters.paper)) keep.add(n)
      for (const id of paperIds ?? []) if (graph.hasNode(id)) keep.add(id)
    }
    graph.forEachNode((node) =>
      sigma.setNodeState(node, {
        isDimmed: keep ? !keep.has(node) : false,
        isHighlighted: keep ? keep.has(node) : false, // highlighted nodes always get labels
        isSelected: chosen.includes(node),
      } as never),
    )
    graph.forEachEdge((edge, _attrs, source, target) =>
      sigma.setEdgeState(edge, {
        // only edges between highlighted nodes that touch a selected node stay visible
        isHidden: keep
          ? !(keep.has(source) && keep.has(target) && (chosen.includes(source) || chosen.includes(target)))
          : false,
      }),
    )
  }, [selected, selectedNodes, paperIds, filters.paper, sigma])

  // Camera moves only when the focused node changes (not when the paper set resolves, which
  // would re-target a running animation from an intermediate state).
  useEffect(() => {
    const graph = sigma.getGraph()
    if (!selected || !graph.hasNode(selected)) return
    // Centre the node in the part of the canvas the panel overlay leaves visible.
    const { width } = sigma.getDimensions()
    const shift = width > 900 ? PANEL_WIDTH / 2 : 0
    const at = sigma.getNodeDisplayData(selected)!
    const camera = sigma.getCamera()
    const ratio = camera.getState().ratio
    const centre = sigma.viewportToFramedGraph({ x: width / 2, y: 0 })
    const offset = sigma.viewportToFramedGraph({ x: width / 2 + shift, y: 0 })
    camera.animate({ x: at.x + (offset.x - centre.x), y: at.y, ratio }, { duration: 400 })
  }, [selected, sigma])
  return null
}

export default function GraphPage({ user }: { user: string }) {
  const theme = useTheme()
  const { active, filters } = useSelection()
  const query = useGraph(asUser<GraphData>(user, '/api/graph'))
  const { data } = query

  const colors = useMemo(
    () => ({
      label: resolveColor('--foreground'),
      backdrop: resolveColor('--popover'),
      dim: resolveColor('--graph-dim'),
    }),
    // re-resolve when the theme changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [theme],
  )

  const options = useMemo(
    () => ({
          primitives: PRIMITIVES as never,
          customNodeState: { isDimmed: false, isSelected: false },
          styles: {
            ...DEFAULT_STYLES,
            nodes: {
              ...DEFAULT_STYLES.nodes,
              color: { whenState: 'isDimmed', then: colors.dim, else: { attribute: 'color' } },
              labelVisibility: labelVisibility,
              size: nodeSize,
              backdropVisibility: backdropVisibility,
              shape: { attribute: 'shape', defaultValue: 'circle' },
              labelColor: colors.label,
              backdropColor: colors.backdrop,
            },
          } as never,
          settings: { labelRenderedSizeThreshold: 8, labelDensity: 0.5, renderEdgeLabels: false },
    }),
    [colors],
  )

  if (query.isPending)
    return (
      <div className="h-full p-4">
        <Skeleton className="h-full w-full rounded-lg" aria-label="Loading the knowledge graph" />
      </div>
    )
  if (query.isError || !data)
    return (
      <div className="p-4 text-sm">
        <p>Couldn't load the knowledge graph.</p>
        <Button variant="outline" size="sm" className="mt-2" onClick={() => query.refetch()}>
          Try again
        </Button>
      </div>
    )
  if (!data.nodes.length)
    return (
      <p className="text-muted-foreground p-4 text-sm">
        No extracted facts in the papers {user} may read yet.
      </p>
    )

  const counts = data.nodes.reduce<Record<string, number>>(
    (acc, n) => ({ ...acc, [n.type]: (acc[n.type] ?? 0) + 1 }),
    {},
  )
  const phaseLabels = Object.fromEntries(
    data.nodes.filter((n) => n.type === 'phase').map((n) => [n.id, n.label]),
  )
  const withoutFacts = data.total_papers - (counts.paper ?? 0)
  const ids = new Set(data.nodes.map((n) => n.id))
  const unmatched = active && !Object.values(filters).some((v) => v && ids.has(v))

  return (
    <div className="flex h-full flex-col gap-2 p-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <NodeFinder data={data} />
        <span className="text-muted-foreground">
          Papers <b className="text-foreground">{user}</b> may read, linked to their extracted
          facts. Hover a paper for its title; click a node or search one to see its papers. Drag to pan, scroll to zoom.
          {withoutFacts > 0 &&
            ` ${withoutFacts} ${withoutFacts === 1 ? 'paper has' : 'papers have'} no extracted facts and no node.`}
        </span>
        <ul className="flex flex-wrap gap-3" aria-label="Node types">
          {Object.entries(TYPES).map(([type, t]) => (
            <li key={type} className="flex items-center gap-1.5">
              {type === 'phase' ? (
                <span className="flex" aria-hidden>
                  {['requirements', 'testing', 'maintenance_evolution'].map((p) => (
                    <span
                      key={p}
                      className="-mr-1 size-2.5 rounded-full"
                      style={{ background: phaseColor(p) }}
                    />
                  ))}
                </span>
              ) : (
                <ShapeIcon shape={TYPE_SHAPES[type]} color={`var(${t.token})`} />
              )}
              <span className={type === 'phase' ? 'ml-1' : undefined}>{t.label}</span>
              <span className="text-muted-foreground tabular-nums">{counts[type] ?? 0}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="relative min-h-0 flex-1">
        <SigmaContainer
          className="h-full rounded-lg border"
          style={{ background: 'var(--card)' }}
          options={options}
        >
          <LoadGraph data={data} theme={theme} />
          <Selection user={user} />
          <ControlsContainer position="bottom-left">
            <ZoomControl labels={{ zoomIn: 'Zoom in', zoomOut: 'Zoom out', reset: 'Fit the whole graph' }} />
          </ControlsContainer>
        </SigmaContainer>
        {unmatched && (
          <p
            role="status"
            className="bg-card text-muted-foreground absolute top-3 left-3 rounded-md border px-3 py-2 text-sm shadow-sm"
          >
            Nothing {user} may read matches this selection.
          </p>
        )}
        {active && (
          <PaperPanel
            user={user}
            phaseLabels={phaseLabels}
            className="absolute inset-y-3 right-3 w-[400px] shadow-lg"
          />
        )}
      </div>
    </div>
  )
}
