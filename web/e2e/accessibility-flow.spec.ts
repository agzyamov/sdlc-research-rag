import { papersFor } from './support/data'
import { expect, test, view } from './support/test'

const panel = (page: import('@playwright/test').Page) =>
  page.getByRole('complementary', { name: 'Papers behind the selection' })

test('AC-19 every bar row announces its count, and card titles are headings inside <main>', async ({ page }) => {
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  const strip = page.getByLabel('Papers per SDLC phase')
  await expect(strip.getByRole('button')).toHaveCount(8)
  for (const row of await strip.getByRole('button').all())
    await expect(row).toHaveAccessibleName(/^\d\. .+: \d+ papers?$/)
  for (const row of await page.getByLabel('Techniques').getByRole('button').all())
    await expect(row).toHaveAccessibleName(/: \d+ papers?$/)
  for (const title of ['Papers per SDLC phase', 'Techniques', 'Models', 'Benchmarks'])
    await expect(page.getByRole('main').getByRole('heading', { level: 2, name: title })).toBeVisible()
})

test('AC-20 a paper groups its tags by type, and the quotes follow the same order and mark shared ones', async ({ page, request }) => {
  const papers = await papersFor(request, 'bob')
  const paper = papers.find((p) => p.techniques.length + p.models.length + p.benchmarks.length > 1)!
  await page.goto(view({ tab: 'landscape', user: 'bob', paper: paper.paper_id }))
  const item = panel(page).getByRole('listitem').first()
  // visible type label per chip group
  for (const [field, label] of [['sdlc_phases', 'Phases'], ['techniques', 'Techniques'], ['models', 'Models'], ['benchmarks', 'Benchmarks']] as const)
    if (paper[field].length) await expect(item.locator('dt', { hasText: label })).toBeVisible()

  const chipNames = (await item.locator('dd button').allInnerTexts()).map((t) => t.trim())
  await item.getByText('Why these tags? Quotes from the abstract').click()
  const reasonNames = (await item.locator('details li > span').allInnerTexts()).map((t) =>
    t.replace(/^(Phase|Technique|Model|Benchmark): /, '').trim(),
  )
  expect(reasonNames).toEqual(chipNames) // same order as the chips
  const quotes = await item.locator('details blockquote').allInnerTexts()
  const counts = new Map<string, number>()
  for (const q of quotes) {
    const text = q.split('\n')[0]
    counts.set(text, (counts.get(text) ?? 0) + 1)
  }
  for (const [text, n] of counts)
    if (n > 1)
      await expect(item.locator('details blockquote', { hasText: text }).first()).toContainText('Same quote also backs')
})

test('AC-21 a selected graph node is centred beside the panel, not under it', async ({ page }) => {
  await page.goto(view({ tab: 'graph', user: 'bob', phase: 'testing' }))
  await expect(panel(page)).toBeVisible()
  await page.waitForTimeout(900) // camera animation
  const position = await page.evaluate(() => {
    type S = {
      getNodeDisplayData(n: string): { x: number; y: number }
      framedGraphToViewport(p: { x: number; y: number }): { x: number; y: number }
      getDimensions(): { width: number }
    }
    const sigma = (window as unknown as { __sigma: S }).__sigma
    return { x: sigma.framedGraphToViewport(sigma.getNodeDisplayData('testing')).x, width: sigma.getDimensions().width }
  })
  expect(position.x).toBeLessThan(position.width - 412) // left of the panel overlay
  expect(position.x).toBeGreaterThan(0)
})

test('AC-22 keyboard flow: jump to the papers, Esc returns focus to the selected row, the Find input is named', async ({ page }) => {
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  const strip = page.getByLabel('Papers per SDLC phase')
  await expect(strip.locator('span.tabular-nums')).toHaveCount(8)
  const values = await strip.locator('span.tabular-nums').allTextContents()
  const row = strip.getByRole('button').nth(values.findIndex((v) => Number(v) > 0))
  await row.focus()
  await page.keyboard.press('Enter')

  await page.getByRole('button', { name: 'Jump to papers' }).click()
  await expect(panel(page).getByRole('heading', { name: 'Papers behind the selection' })).toBeFocused()

  await page.keyboard.press('Escape')
  await expect(panel(page)).toHaveCount(0)
  await expect(row).toBeFocused()

  await page.goto(view({ tab: 'graph', user: 'bob' }))
  await page.getByRole('button', { name: /Find a paper, phase or fact/ }).click()
  await expect(page.getByRole('combobox', { name: 'Find a node' }).or(page.getByRole('textbox', { name: 'Find a node' })).first()).toBeVisible()
})
