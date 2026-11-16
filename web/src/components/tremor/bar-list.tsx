// Tremor BarList [v1.0.0] — https://github.com/tremorlabs/tremor (Apache-2.0)
// Vendored registry component. Adapted for this app:
// - cn() and theme tokens instead of Tremor's cx()/focusRing and gray/blue palette
// - per-row `color` (CSS color, e.g. var(--series-4)) so SDLC phases keep their colour
// - `selectedKey` renders aria-pressed + a ring on the selected row
// - zero-value rows keep a visible track (honest absence) instead of disappearing
// - container is role="group" (so aria-label is valid); aria-sort removed (only valid on
//   table headers; flagged by axe)
// - label column is min-w-0 so a long name truncates (with a title tooltip) instead of
//   pushing the value column out of the card
// - each row's accessible name includes its value ("4. Testing: 12 papers"); the visual
//   value column is aria-hidden so screen readers do not read orphan numbers

import React from 'react'
import { cn } from '@/lib/utils'

type Bar<T> = T & {
  key?: string
  value: number
  name: string
  color?: string
}

interface BarListProps<T = unknown> extends React.HTMLAttributes<HTMLDivElement> {
  data: Bar<T>[]
  valueFormatter?: (value: number) => string
  /** Spoken value for the row's accessible name, e.g. (v) => `${v} papers`. */
  valueLabel?: (value: number) => string
  onValueChange?: (payload: Bar<T>) => void
  sortOrder?: 'ascending' | 'descending' | 'none'
  selectedKey?: string | null
  barColor?: string
}

function BarListInner<T>(
  {
    data = [],
    valueFormatter = (value) => value.toString(),
    valueLabel = (value) => value.toString(),
    onValueChange,
    sortOrder = 'descending',
    selectedKey = null,
    barColor = 'var(--series-neutral)',
    className,
    ...props
  }: BarListProps<T>,
  forwardedRef: React.ForwardedRef<HTMLDivElement>,
) {
  const sortedData = React.useMemo(() => {
    if (sortOrder === 'none') return data
    return [...data].sort((a, b) => {
      const byValue = sortOrder === 'ascending' ? a.value - b.value : b.value - a.value
      return byValue || a.name.localeCompare(b.name) // ties: alphabetical, stated in the UI
    })
  }, [data, sortOrder])

  const widths = React.useMemo(() => {
    const maxValue = Math.max(...sortedData.map((item) => item.value), 0)
    return sortedData.map((item) =>
      item.value === 0 ? 0 : Math.max((item.value / maxValue) * 100, 2),
    )
  }, [sortedData])

  return (
    <div
      ref={forwardedRef}
      role="group"
      className={cn('flex justify-between gap-4', className)}
      {...props}
    >
      <div className="relative w-full min-w-0 space-y-1">
        {sortedData.map((item, index) => {
          const key = item.key ?? item.name
          const selected = selectedKey === key
          const content = (
            <div className="bg-muted/60 relative flex h-7 items-center rounded-sm">
              <div
                className="absolute inset-y-0 left-0 rounded-sm opacity-35 transition-[width,opacity] duration-200 ease-out group-hover:opacity-55"
                style={{ width: `${widths[index]}%`, background: item.color ?? barColor }}
              />
              <span
                title={item.name}
                className={cn(
                  'text-foreground relative truncate px-2 text-left text-sm',
                  item.value === 0 && 'text-muted-foreground',
                )}
              >
                {item.name}
              </span>
            </div>
          )
          return onValueChange ? (
            <button
              key={key}
              type="button"
              aria-pressed={selected}
              aria-label={`${item.name}: ${valueLabel(item.value)}`}
              onClick={() => onValueChange(item)}
              className={cn(
                'group block w-full cursor-pointer rounded-sm',
                // focus: offset outline; selection: inset ring (never confusable)
                'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                selected && 'ring-foreground/70 ring-2 ring-inset',
              )}
            >
              {content}
            </button>
          ) : (
            <div key={key}>{content}</div>
          )
        })}
      </div>
      <div className="shrink-0" aria-hidden>
        {sortedData.map((item, index) => (
          <div
            key={item.key ?? item.name}
            className={cn('flex h-7 items-center justify-end', index > 0 && 'mt-1')}
          >
            <span
              className={cn(
                'text-sm tabular-nums',
                item.value === 0 ? 'text-muted-foreground' : 'text-foreground',
              )}
            >
              {valueFormatter(item.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

BarListInner.displayName = 'BarList'

const BarList = React.forwardRef(BarListInner) as <T>(
  p: BarListProps<T> & { ref?: React.ForwardedRef<HTMLDivElement> },
) => ReturnType<typeof BarListInner>

export { BarList, type BarListProps }
