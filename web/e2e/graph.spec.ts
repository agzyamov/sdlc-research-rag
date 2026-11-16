import type { Page } from '@playwright/test'
import { expect, test, view } from './support/test'

type SigmaLike = {
  getGraph(): {
    filterNodes(fn: (n: string, a: Record<string, unknown>) => boolean): string[]
    nodes(): string[]
  }
  getDimensions(): { width: number; height: number }
  getNodeDisplayData(n: string): { x: number; y: number }
  framedGraphToViewport(p: { x: number; y: number }): { x: number; y: number }
}

/** Viewport position of the first node of a type (via the dev-only Sigma test seam). */
async function nodePosition(page: Page, type: string) {
  await page.waitForFunction(() => (window as unknown as { __sigma?: SigmaLike }).__sigma)
  return page.evaluate((nodeType) => {
    const sigma = (window as unknown as { __sigma: SigmaLike }).__sigma
    const [node] = sigma.getGraph().filterNodes((_n, a) => a.nodeType === nodeType)
    const point = sigma.framedGraphToViewport(sigma.getNodeDisplayData(node))
    return { node, ...point }
  }, type)
}

/** A viewport point at least 40px away from every node (a guaranteed background click). */
async function emptyPoint(page: Page) {
  return page.evaluate(() => {
    const sigma = (window as unknown as { __sigma: SigmaLike }).__sigma
    const { width, height } = sigma.getDimensions()
    const nodes = sigma.getGraph().nodes().map((n) => sigma.framedGraphToViewport(sigma.getNodeDisplayData(n)))
    for (let y = 20; y < height; y += 20)
      for (let x = 20; x < width; x += 20)
        if (nodes.every((p) => Math.hypot(p.x - x, p.y - y) > 40)) return { x, y }
    throw new Error('no empty point on the stage')
  })
}

test('AC-8 clicking a graph node opens its papers and focuses it; clicking the background clears', async ({ page }) => {
  await page.goto(view({ tab: 'graph', user: 'bob' }))
  const canvas = page.locator('.sigma-container canvas').last()
  await expect(canvas).toBeVisible()
  await page.waitForTimeout(600) // layout + first render

  const box = (await page.locator('.sigma-container').boundingBox())!
  const { node, x, y } = await nodePosition(page, 'phase')
  await page.mouse.click(box.x + x, box.y + y)

  const panel = page.getByRole('complementary', { name: 'Papers behind the selection' })
  await expect(page).toHaveURL(new RegExp(`phase=${node}`))
  await expect(panel).toBeVisible()
  await expect(panel.getByRole('listitem').first()).toBeVisible()

  // a background click clears the selection
  await page.waitForTimeout(500) // camera animation to the selected node
  const empty = await emptyPoint(page)
  await page.mouse.click(box.x + empty.x, box.y + empty.y)
  await expect(panel).toHaveCount(0)
  await expect(page).not.toHaveURL(/phase=/)
})
