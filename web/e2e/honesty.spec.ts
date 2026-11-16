import { papersFor } from './support/data'
import { expect, test, view } from './support/test'

test('AC-23 fact lists never truncate silently: all items, or "Top 10 of N" with Show all', async ({ page, request }) => {
  const papers = await papersFor(request, 'bob')
  const distinct = (field: 'techniques' | 'models' | 'benchmarks') => new Set(papers.flatMap((p) => p[field])).size
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  for (const [field, title] of [['techniques', 'Techniques'], ['models', 'Models'], ['benchmarks', 'Benchmarks']] as const) {
    const n = distinct(field)
    if (!n) continue
    const list = page.getByLabel(title).getByRole('button')
    if (n <= 25) {
      await expect(page.getByText(`All ${n}, by papers`).first()).toBeVisible()
      await expect(list).toHaveCount(n)
    } else {
      await expect(page.getByText(`Top 10 of ${n}`)).toBeVisible()
      await page.getByRole('button', { name: `Show all ${n}` }).click()
      await expect(list).toHaveCount(n)
    }
  }
})

test('AC-24 the selected graph node is enlarged and labelled, and its neighbours are labelled', async ({ page }) => {
  await page.goto(view({ tab: 'graph', user: 'bob', technique: 'LLM agents' }))
  await expect(page.getByRole('complementary', { name: 'Papers behind the selection' })).toBeVisible()
  await page.waitForFunction(() => (window as unknown as { __sigma?: unknown }).__sigma)
  await page.waitForTimeout(600)
  const result = await page.evaluate(() => {
    type S = {
      getGraph(): { hasNode(n: string): boolean; neighbors(n: string): string[]; nodes(): string[]; getNodeAttribute(n: string, a: string): unknown }
      getNodeState(n: string): Record<string, boolean>
    }
    const sigma = (window as unknown as { __sigma: S }).__sigma
    const graph = sigma.getGraph()
    const selected = graph.nodes().find((n) => sigma.getNodeState(n).isSelected)
    return {
      selected,
      neighboursHighlighted: selected ? graph.neighbors(selected).every((n) => sigma.getNodeState(n).isHighlighted) : false,
      neighbours: selected ? graph.neighbors(selected).length : 0,
    }
  })
  expect(result.selected).toBe('LLM agents')
  expect(result.neighbours).toBeGreaterThan(0)
  expect(result.neighboursHighlighted).toBe(true) // highlighted nodes always get their label
})

test('AC-25 every count stays visible inside its card, even next to a long label and the open panel', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(view({ tab: 'landscape', user: 'alice', phase: 'testing' }))
  await expect(page.getByRole('complementary', { name: 'Papers behind the selection' })).toBeVisible()
  for (const title of ['Papers per SDLC phase', 'Techniques', 'Models', 'Benchmarks']) {
    const group = page.getByLabel(title)
    if (!(await group.count())) continue
    const overflow = await group.evaluate((el) => {
      const card = el.closest('[data-slot="card"]') ?? el.parentElement!
      const right = card.getBoundingClientRect().right
      return [...el.querySelectorAll('span.tabular-nums')].filter((n) => n.getBoundingClientRect().right > right + 0.5).length
    })
    expect(overflow, `${title}: counts outside the card`).toBe(0)
  }
})

test('AC-26 every card caption names the full scope it counts over', async ({ page }) => {
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  // pick the first technique, then a phase that co-occurs with it
  const technique = (await page.getByLabel('Techniques').getByRole('button').first().getAttribute('aria-label'))!.split(':')[0]
  await page.goto(view({ tab: 'landscape', user: 'bob', technique }))
  const strip = page.getByLabel('Papers per SDLC phase')
  await expect(strip.locator('span.tabular-nums')).toHaveCount(8)
  const values = await strip.locator('span.tabular-nums').allTextContents()
  const index = values.findIndex((v) => Number(v) > 0)
  const phaseName = (await strip.getByRole('button').nth(index).getAttribute('aria-label'))!.split(':')[0]
  await strip.getByRole('button').nth(index).click()

  // the strip ignores its own dimension but says which other filter it counts within
  await expect(page.getByText(`Papers with ${technique}, per phase`)).toBeVisible()
  // fact lists name every active filter; empty lists say None, never "All 0"
  for (const title of ['Techniques', 'Models', 'Benchmarks']) {
    const caption = page.getByRole('heading', { level: 2, name: title }).locator('xpath=following-sibling::*[1]')
    await expect(caption).toContainText(`within ${phaseName}, with ${technique}`)
    await expect(caption).not.toContainText('All 0')
  }
})

test('AC-29 with combined filters the graph highlights exactly the papers the panel lists', async ({ page, request }) => {
  const bob = await import('./support/data').then((m) => m.papersFor(request, 'bob'))
  // a phase + technique pair that co-occurs, so the intersection is non-empty
  const p = bob.find((x) => x.techniques.length && x.sdlc_phases.length)!
  await page.goto(view({ tab: 'graph', user: 'bob', phase: p.sdlc_phases[0], technique: p.techniques[0] }))
  const panel = page.getByRole('complementary', { name: 'Papers behind the selection' })
  await expect(panel.getByRole('listitem').first()).toBeVisible()
  const listed = (await panel.getByText(/^arXiv:/).allInnerTexts()).map((t) => t.replace('arXiv:', '').trim()).sort()
  await page.waitForTimeout(400)
  const lit = await page.evaluate(() => {
    type S = {
      getGraph(): { nodes(): string[]; getNodeAttribute(n: string, a: string): unknown }
      getNodeState(n: string): Record<string, boolean>
    }
    const sigma = (window as unknown as { __sigma: S }).__sigma
    const graph = sigma.getGraph()
    return graph
      .nodes()
      .filter((n) => graph.getNodeAttribute(n, 'nodeType') === 'paper' && sigma.getNodeState(n).isHighlighted)
      .sort()
  })
  expect(lit).toEqual(listed)
})

test('AC-30 a selection with nothing this user may read dims the whole graph and says so', async ({ page, request }) => {
  const { papersFor } = await import('./support/data')
  const alice = new Set((await papersFor(request, 'alice')).flatMap((p) => p.techniques))
  const internalOnly = (await papersFor(request, 'bob')).flatMap((p) => p.techniques).find((t) => !alice.has(t))
  test.skip(!internalOnly, 'every technique appears in an open paper')
  await page.goto(view({ tab: 'graph', user: 'alice', technique: internalOnly! }))
  await expect(page.getByRole('status').filter({ hasText: 'Nothing alice may read matches this selection.' })).toBeVisible()
  await page.waitForFunction(() => (window as unknown as { __sigma?: unknown }).__sigma)
  await page.waitForTimeout(400)
  const undimmed = await page.evaluate(() => {
    type S = { getGraph(): { nodes(): string[] }; getNodeState(n: string): Record<string, boolean> }
    const sigma = (window as unknown as { __sigma: S }).__sigma
    return sigma.getGraph().nodes().filter((n) => !sigma.getNodeState(n).isDimmed).length
  })
  expect(undimmed).toBe(0)
})
