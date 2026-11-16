import { expect, test as base } from '@playwright/test'
import { mockApi } from './mock-api'

export const LIVE = !!process.env.E2E_LIVE

// Console noise that is not an app defect: the browser logs every non-2xx response, and some
// specs deliberately trigger 403/404/500 responses.
const EXPECTED = [/Failed to load resource: the server responded with a status of (403|404|500)/]

/**
 * Every spec gets the mocked API unless running live (E2E_LIVE=1), and fails on any uncaught
 * page error or console error (render loops, React warnings) even when the UI still works.
 */
export const test = base.extend<{ mocked: void; cleanConsole: void }>({
  mocked: [
    async ({ page }, use) => {
      if (!LIVE) await mockApi(page)
      await use()
    },
    { auto: true },
  ],
  cleanConsole: [
    async ({ page }, use) => {
      const errors: string[] = []
      page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
      page.on('console', (m) => {
        if (m.type() === 'error' && !EXPECTED.some((re) => re.test(m.text())))
          errors.push(`console.error: ${m.text().slice(0, 300)}`)
      })
      await use()
      expect(errors, 'the page logged errors').toEqual([])
    },
    { auto: true },
  ],
})

export { expect }

/** Open a view by URL (the app keeps tab, user and selection in the query string). */
export const view = (params: Record<string, string>) => `/?${new URLSearchParams(params)}`
