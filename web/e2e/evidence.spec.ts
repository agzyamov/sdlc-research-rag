import { papersFor } from './support/data'
import { expect, LIVE, test, view } from './support/test'

const panel = (page: import('@playwright/test').Page) =>
  page.getByRole('complementary', { name: 'Papers behind the selection' })

test('AC-15 every tag on a paper shows its abstract quote, or says none was found', async ({ page, request }) => {
  const [paper] = await papersFor(request, 'bob')
  await page.goto(view({ tab: 'landscape', user: 'bob', paper: paper.paper_id }))
  const item = panel(page).getByRole('listitem').first()
  await expect(item.getByText(/Submitted \w+ \d+, \d{4}/)).toBeVisible()

  const chips = await item.locator('dd button').count()
  await item.getByText('Why these tags? Quotes from the abstract').click()
  const reasons = item.locator('details li')
  await expect(reasons).toHaveCount(chips) // one reason per tag
  for (const reason of await reasons.all())
    await expect(reason.locator('blockquote').or(reason.getByText(/No supporting sentence found/))).toBeVisible()
  await expect(item.locator('details blockquote').first()).toBeVisible() // at least one real quote
})

test('AC-16 changing the selection keeps the page and keyboard focus in place while it loads', async ({ page }) => {
  if (!LIVE) {
    // slow down cross-filtered landscape responses so the loading state is observable
    await page.route(
      (url) => url.pathname === '/api/landscape' && url.searchParams.has('technique'),
      async (route) => {
        await new Promise((r) => setTimeout(r, 800))
        await route.fallback()
      },
    )
  }
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  const technique = page.getByLabel('Techniques').getByRole('button').first()
  await technique.focus()
  await page.keyboard.press('Enter')

  await expect(page.getByLabel('Loading the landscape')).toHaveCount(0) // no full-page skeleton
  await expect(page.getByLabel('Papers per SDLC phase')).toBeVisible()
  await expect(page.getByRole('complementary', { name: 'Papers behind the selection' })).toBeVisible()
  await expect(page.getByLabel('Techniques').getByRole('button', { pressed: true })).toBeFocused()
})

test('AC-17 the graph is usable from the keyboard: search a node to select it; zoom controls exist', async ({ page }) => {
  await page.goto(view({ tab: 'graph', user: 'bob' }))
  const finder = page.getByRole('button', { name: /Find a paper, phase or fact/ })
  await finder.focus()
  await page.keyboard.press('Enter')
  await page.keyboard.type('4. Testing')
  await page.keyboard.press('Enter')

  await expect(page).toHaveURL(/phase=testing/)
  await expect(panel(page).getByRole('listitem').first()).toBeVisible()
  for (const name of ['Zoom in', 'Zoom out', 'Fit the whole graph'])
    await expect(page.getByRole('button', { name })).toBeVisible()
  // node types differ by shape as well as shade: the legend draws a shape per type
  await expect(page.getByLabel('Node types').locator('svg')).toHaveCount(4)
})

test('AC-18 a public user sees how many papers exist beyond their access, never which', async ({ page, request }) => {
  const alice = await papersFor(request, 'alice')
  const all = await papersFor(request, 'bob')
  await page.goto(view({ tab: 'landscape', user: 'alice' }))
  await expect(
    page.getByText(`${alice.length} of ${all.length} papers alice may read · ${all.length - alice.length} internal-only`),
  ).toBeVisible()

  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  await expect(page.getByText(`${all.length} papers bob may read`)).toBeVisible()
  await expect(page.getByText(/internal-only/)).toHaveCount(0)
})
