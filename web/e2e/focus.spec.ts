import type { Locator, Page } from '@playwright/test'
import { expect, test, view } from './support/test'

/** WCAG contrast of the element's focus outline against the nearest opaque background. */
async function focusContrast(page: Page, target: Locator) {
  // keyboard modality first, so :focus-visible applies to the programmatic focus
  await page.keyboard.press('Shift')
  await target.focus()
  await page.waitForTimeout(250) // vendored buttons animate outline-color (transition-all)
  return target.evaluate((el) => {
    const canvas = document.createElement('canvas').getContext('2d')!
    const rgba = (css: string) => {
      canvas.fillStyle = '#000'
      canvas.fillStyle = css
      canvas.fillRect(0, 0, 1, 1)
      return [...canvas.getImageData(0, 0, 1, 1).data]
    }
    const lum = ([r, g, b]: number[]) => {
      const f = (c: number) => ((c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    }
    let node: Element | null = el.parentElement
    let bg = [255, 255, 255, 255]
    while (node) {
      const c = rgba(getComputedStyle(node).backgroundColor)
      if (c[3] === 255) {
        bg = c
        break
      }
      node = node.parentElement
    }
    const style = getComputedStyle(el)
    const ring = rgba(style.outlineColor)
    const [a, b] = [lum(ring), lum(bg)].sort((x, y) => y - x)
    return { ratio: (a + 0.05) / (b + 0.05), outline: style.outlineStyle, width: style.outlineWidth }
  })
}

for (const scheme of ['light', 'dark'] as const)
  test(`AC-27 focus indicators reach 3:1 and differ from selection: ${scheme}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme })
    await page.goto(view({ tab: 'landscape', user: 'bob', phase: 'testing' }))
    const panel = page.getByRole('complementary', { name: 'Papers behind the selection' })
    await expect(panel).toBeVisible()
    const targets: [string, Locator][] = [
      ['phase row', page.getByLabel('Papers per SDLC phase').getByRole('button').first()],
      ['fact row', page.getByLabel('Techniques').getByRole('button').first()],
      ['fact chip', panel.locator('dd button').first()],
      ['filter chip', panel.getByRole('button', { name: /Remove filter/ }).first()],
      ['close button', panel.getByRole('button', { name: 'Close panel' })],
      ['demo-user select', page.getByRole('combobox', { name: 'Demo user' })],
      ['tab', page.getByRole('tab', { name: 'Landscape' })],
      ['tab panel', page.getByRole('tabpanel')],
      ['paper link', panel.getByRole('listitem').first().getByRole('link').first()],
    ]
    for (const [name, target] of targets) {
      const { ratio, outline, width } = await focusContrast(page, target)
      expect(outline, `${name}: focus outline style`).toBe('solid')
      expect(parseFloat(width), `${name}: focus outline width`).toBeGreaterThanOrEqual(2)
      expect(ratio, `${name}: focus contrast`).toBeGreaterThanOrEqual(3)
    }
    // selected (pressed, not focused) rows use an inset ring, never the focus outline
    const selected = page.getByLabel('Papers per SDLC phase').getByRole('button', { pressed: true })
    await page.getByRole('heading', { level: 2, name: 'Techniques' }).click() // move focus away
    expect(await selected.evaluate((el) => getComputedStyle(el).outlineStyle)).toBe('none')
    expect(await selected.evaluate((el) => getComputedStyle(el).boxShadow)).toContain('inset')
  })

test('AC-28 graph Find matches whole words: typing a phase name and Enter selects that phase', async ({ page }) => {
  await page.goto(view({ tab: 'graph', user: 'alice' }))
  await page.getByRole('button', { name: /Find a paper, phase or fact/ }).click()
  await page.keyboard.type('testing')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/phase=testing/)
  await expect(page).not.toHaveURL(/paper=/)
})
