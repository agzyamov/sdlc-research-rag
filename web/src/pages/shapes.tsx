/** One shape per node / fact type, shared by the graph, its legend and the paper panel, so
 * type is never told by colour alone. Must match the Sigma node shapes in KnowledgeGraph. */
export type Shape = 'circle' | 'square' | 'triangle' | 'diamond' | 'rectangle'

export const TYPE_SHAPES: Record<string, Shape> = {
  paper: 'circle',
  phase: 'square',
  sdlc_phases: 'square',
  technique: 'triangle',
  techniques: 'triangle',
  model: 'diamond',
  models: 'diamond',
  benchmark: 'rectangle',
  benchmarks: 'rectangle',
}

const PATHS: Record<Shape, string> = {
  circle: 'M6 1a5 5 0 1 1 0 10A5 5 0 0 1 6 1z',
  square: 'M2 2h8v8H2z',
  triangle: 'M6 1.5l5 9H1z',
  diamond: 'M6 1l5 5-5 5-5-5z',
  rectangle: 'M0.5 3.5h11v5h-11z',
}

export function ShapeIcon({ shape, color, className = 'size-3' }: { shape: Shape; color: string; className?: string }) {
  return (
    <svg viewBox="0 0 12 12" className={className} aria-hidden>
      <path d={PATHS[shape]} fill={color} />
    </svg>
  )
}
