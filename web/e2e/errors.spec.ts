import { expect, LIVE, test, view } from './support/test'

test('AC-14 when the API fails a page shows a plain message and Try again recovers', async ({ page }) => {
  test.skip(LIVE, 'failure is injected; covered in mocked mode')
  let fail = true
  await page.route((url) => url.pathname === '/api/landscape', (route) =>
    fail ? route.fulfill({ status: 500, json: { detail: 'boom' } }) : route.fallback(),
  )
  await page.goto(view({ tab: 'landscape', user: 'bob' }))
  await expect(page.getByText("Couldn't load the research landscape.")).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText(/500|boom|axios/i)).toHaveCount(0)

  fail = false
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByText('Papers per SDLC phase')).toBeVisible()
})
