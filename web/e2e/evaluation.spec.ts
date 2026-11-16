import { expect, LIVE, test, view } from './support/test'

test('AC-10 the evaluation page shows summary metrics against targets and per-question rows', async ({ page }) => {
  await page.goto(view({ tab: 'eval', user: 'alice' }))
  const summary = page.getByRole('table').first()
  for (const metric of ['Faithfulness', 'Answer Relevancy', 'Contextual Precision', 'Contextual Recall', 'Correctness', 'ACL leaks'])
    await expect(summary.getByRole('row', { name: new RegExp(metric) })).toBeVisible()
  await expect(summary.getByRole('row', { name: /Faithfulness/ })).toContainText('≥ 0.85')
  await expect(page.getByRole('table').nth(1).getByText('acl-001')).toBeVisible()
})

test('AC-10 before the first evaluation run the page explains how to create a report', async ({ page }) => {
  test.skip(LIVE, 'needs a missing report; covered in mocked mode')
  await page.route((url) => url.pathname === '/api/eval', (route) => route.fulfill({ status: 404, json: { detail: 'no evaluation report yet' } }))
  await page.goto(view({ tab: 'eval', user: 'alice' }))
  await expect(page.getByText('No evaluation report yet')).toBeVisible()
  await expect(page.getByText('uv run sdlcrag eval')).toBeVisible()
})
