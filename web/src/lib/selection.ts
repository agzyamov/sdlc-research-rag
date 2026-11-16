import { parseAsString, useQueryStates } from 'nuqs'
import { asUser, type PaperSummary, usePapers } from '@/lib/api'

/**
 * Drill-through selection, kept in the URL (shareable: ?tab=landscape&phase=testing).
 * Keys match the API filters of /api/papers and /api/landscape.
 */
export const FILTER_KEYS = ['phase', 'technique', 'model', 'benchmark', 'paper'] as const
export type FilterKey = (typeof FILTER_KEYS)[number]
export type Filters = Partial<Record<FilterKey, string>>

const parsers = Object.fromEntries(FILTER_KEYS.map((k) => [k, parseAsString])) as Record<
  FilterKey,
  typeof parseAsString
>

export function useSelection() {
  const [state, setState] = useQueryStates(parsers)
  const filters: Filters = Object.fromEntries(
    Object.entries(state).filter(([, v]) => v),
  ) as Filters
  return {
    filters,
    active: Object.keys(filters).length > 0,
    /** Select a value; selecting the current value again clears it (toggle). */
    toggle: (key: FilterKey, value: string) =>
      setState({ [key]: state[key] === value ? null : value, ...(key !== 'paper' && { paper: null }) }),
    /** Replace the whole selection with one value (graph clicks). */
    select: (key: FilterKey, value: string) =>
      setState({
        ...Object.fromEntries(FILTER_KEYS.map((k) => [k, null])),
        [key]: state[key] === value && Object.keys(filters).length === 1 ? null : value,
      }),
    clear: (key?: FilterKey) =>
      setState(key ? { [key]: null } : Object.fromEntries(FILTER_KEYS.map((k) => [k, null]))),
  }
}

export const FILTER_LABELS: Record<FilterKey, string> = {
  phase: 'Phase',
  technique: 'Technique',
  model: 'Model',
  benchmark: 'Benchmark',
  paper: 'Paper',
}

/**
 * The readable papers behind the current selection: one query (and one cache entry) shared by
 * the paper panel and the graph highlight, so the two can never show different sets.
 */
export function useSelectedPapers(user: string) {
  const { filters, active } = useSelection()
  const { phase, technique, model, benchmark, paper } = filters
  const options = asUser<PaperSummary[]>(
    user,
    `/api/papers?${new URLSearchParams(filters as Record<string, string>)}`,
  )
  return usePapers(
    { phase, technique, model, benchmark, paper },
    { ...options, query: { ...options.query, enabled: active } },
  )
}

