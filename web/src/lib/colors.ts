import { formatRgb, parse } from 'culori'

/** Lifecycle order: phase N always wears categorical slot N, on every tab. */
export const PHASE_ORDER = [
  'requirements',
  'design',
  'implementation',
  'testing',
  'code_review',
  'deployment_operations',
  'maintenance_evolution',
  'process_management',
] as const

export const phaseVar = (phase: string) => `--series-${PHASE_ORDER.indexOf(phase as never) + 1}`
export const phaseColor = (phase: string) => `var(${phaseVar(phase)})`

/** A theme token resolved to rgb()/rgba() for canvas/WebGL renderers: Sigma cannot parse
 * oklch(), and alpha (e.g. dark-mode borders) must survive the conversion. */
export function resolveColor(token: string, fallback = 'rgb(136, 136, 136)'): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim()
  const parsed = value ? parse(value) : undefined
  return parsed ? formatRgb(parsed) : fallback
}
