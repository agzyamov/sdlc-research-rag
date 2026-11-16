import AxeBuilder from '@axe-core/playwright'
import { expect, test, view } from './support/test'

const TABS = [
  { tab: 'chat', ready: 'Message input' },
  { tab: 'landscape', ready: 'Papers per SDLC phase' },
  { tab: 'graph', ready: 'Node types' },
  { tab: 'eval', ready: 'Summary' },
]

for (const scheme of ['light', 'dark'] as const)
  for (const { tab, ready } of TABS)
    test(`AC-12 no WCAG 2.1 A/AA violations: ${tab}, ${scheme}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme })
      await page.goto(view({ tab, user: 'bob', ...(tab === 'landscape' && { phase: 'testing' }) }))
      await expect(page.getByText(ready).or(page.getByLabel(ready)).first()).toBeVisible()
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
      expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([])
    })
