import { papersFor } from './support/data'
import { expect, test, view } from './support/test'

const PHASE_ORDER = [
  '1. Requirements',
  '2. Design',
  '3. Implementation',
  '4. Testing',
  '5. Code review',
  '6. Deployment & operations',
  '7. Maintenance & evolution',
  '8. Process & management',
]
const panel = (page: import('@playwright/test').Page) =>
  page.getByRole('complementary', { name: 'Papers behind the selection' })
const phaseRows = (page: import('@playwright/test').Page) =>
  page.getByLabel('Papers per SDLC phase').getByRole('button')

/** The first phase row with at least one paper, and its count. */
async function firstNonEmptyPhase(page: import('@playwright/test').Page) {
  const strip = page.getByLabel('Papers per SDLC phase')
  await expect(strip.locator('span.tabular-nums')).toHaveCount(8) // data loaded
  const values = await strip.locator('span.tabular-nums').allTextContents()
  const index = values.findIndex((v) => Number(v) > 0)
  return { row: phaseRows(page).nth(index), name: PHASE_ORDER[index], count: Number(values[index]) }
}

test('AC-4 shows the readable-paper total and all 8 phases in lifecycle order, zeros included', async ({ page, request }) => {
  const papers = await papersFor(request, 'bob')
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  await expect(page.getByText(`${papers.length} papers bob may read`)).toBeVisible()
  await expect(phaseRows(page)).toHaveText(PHASE_ORDER)
})

test('AC-5 clicking a phase opens its papers and cross-filters the fact lists', async ({ page }) => {
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  const { row, name, count } = await firstNonEmptyPhase(page)
  await row.click()

  await expect(row).toHaveAttribute('aria-pressed', 'true')
  await expect(panel(page)).toBeVisible()
  await expect(panel(page).getByText(`${count} ${count === 1 ? 'paper' : 'papers'} bob may read`)).toBeVisible()
  const items = panel(page).getByRole('listitem')
  await expect(items).toHaveCount(count)
  await expect(items.first().getByRole('link')).toHaveAttribute('href', /^https:\/\/arxiv\.org\/abs\//)
  await expect(items.first().getByText(/Open licence|Internal only/)).toBeVisible()
  await expect(page.getByText(new RegExp(`within ${name.replace(/[.&]/g, '\\$&')}`)).first()).toBeVisible()
  await expect(page.getByText(`${count} ${count === 1 ? 'paper' : 'papers'} bob may read ${count === 1 ? 'matches' : 'match'} the selection`)).toBeVisible()
})

test('AC-6 fact chips pivot, filter chips remove filters, Esc and Close clear the panel', async ({ page }) => {
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  await (await firstNonEmptyPhase(page)).row.click()

  // pivot: a technique chip on the first paper adds a technique filter
  const chip = panel(page).getByRole('listitem').first().getByRole('button', { pressed: false }).last()
  const fact = (await chip.textContent())!.trim()
  await chip.click()
  await expect(panel(page).getByRole('button', { name: new RegExp(`Remove filter .*: ${fact.replace(/[.()+]/g, '\\$&')}`) })).toBeVisible()

  // remove one filter chip
  const removePhase = panel(page).getByRole('button', { name: /Remove filter Phase/ })
  await removePhase.click()
  await expect(removePhase).toHaveCount(0)
  await expect(panel(page)).toBeVisible()

  // Esc closes
  await page.keyboard.press('Escape')
  await expect(panel(page)).toHaveCount(0)

  // Close button closes
  await (await firstNonEmptyPhase(page)).row.click()
  await panel(page).getByRole('button', { name: 'Close panel' }).click()
  await expect(panel(page)).toHaveCount(0)
  await expect(page).not.toHaveURL(/phase=/)
})

test('AC-7 a public user only ever sees open-licensed papers, also via a direct paper URL', async ({ page, request }) => {
  const alice = await papersFor(request, 'alice')
  const bob = await papersFor(request, 'bob')
  expect(alice.length).toBeLessThan(bob.length)
  expect(alice.every((p) => p.license_class === 'open')).toBe(true)

  await page.goto(view({ tab: 'landscape', user: 'alice' }))
  await expect(page.getByText(new RegExp(`^${alice.length} (of \\d+ )?papers alice may read`))).toBeVisible()
  await (await firstNonEmptyPhase(page)).row.click()
  await expect(panel(page).getByText('Internal only')).toHaveCount(0)

  const restricted = bob.find((p) => p.license_class === 'restricted')!
  await page.goto(view({ tab: 'landscape', user: 'alice', paper: restricted.paper_id }))
  await expect(panel(page).getByText(/None of the papers alice may read match/)).toBeVisible()
  await expect(panel(page).getByText(restricted.title)).toHaveCount(0)
})

test('AC-9 opening a view URL restores tab, user and selection', async ({ page }) => {
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  const { name } = await firstNonEmptyPhase(page)
  const phase = { '1. Requirements': 'requirements', '2. Design': 'design', '3. Implementation': 'implementation', '4. Testing': 'testing', '5. Code review': 'code_review', '6. Deployment & operations': 'deployment_operations', '7. Maintenance & evolution': 'maintenance_evolution', '8. Process & management': 'process_management' }[name]!

  await page.goto(view({ tab: 'landscape', user: 'bob', phase }))
  await expect(page.getByRole('tab', { name: 'Landscape' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('combobox', { name: 'Demo user' })).toContainText('bob')
  await expect(phaseRows(page).filter({ hasText: name })).toHaveAttribute('aria-pressed', 'true')
  await expect(panel(page).getByRole('button', { name: `Remove filter Phase: ${name}` })).toBeVisible()
})

test('AC-11 phase rows and panel controls work from the keyboard with a visible focus ring', async ({ page }) => {
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  const { row } = await firstNonEmptyPhase(page)

  // reach the row by tabbing (bounded), not by clicking
  for (let i = 0; i < 40 && !(await row.evaluate((el) => el === document.activeElement)); i++)
    await page.keyboard.press('Tab')
  await expect(row).toBeFocused()
  const outline = await row.evaluate((el) => getComputedStyle(el).outlineStyle)
  expect(outline).toBe('solid') // visible focus indicator (contrast checked in AC-27)

  await page.keyboard.press('Enter')
  await expect(panel(page)).toBeVisible()
  await expect(row).toHaveAttribute('aria-pressed', 'true')
  await page.keyboard.press('Escape')
  await expect(panel(page)).toHaveCount(0)
})
