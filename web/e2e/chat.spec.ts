import { expect, LIVE, test, view } from './support/test'

// Chat specs call the LLM when live, so they carry @llm (run live only with E2E_LLM=1).

test('AC-1 a question streams an answer with inline citations and arXiv source chips @llm', async ({ page }) => {
  await page.goto(view({ tab: 'chat', user: 'bob' }))
  await page.getByRole('textbox', { name: 'Message input' }).fill('Which benchmarks are used to evaluate coding agents?')
  await page.keyboard.press('Enter')
  const answer = page.locator('[data-role="assistant"]').last()
  await expect(answer).toContainText('[1]', { timeout: LIVE ? 60_000 : 5_000 })
  const sources = answer.locator('a[data-slot="source"]')
  await expect(sources.first()).toBeVisible()
  for (const href of await sources.evaluateAll((els) => els.map((e) => e.getAttribute('href')))) {
    expect(href).toMatch(/^https:\/\/arxiv\.org\/abs\//)
  }
})

test('AC-2 a public user never gets a restricted paper as a source @llm', async ({ page }) => {
  await page.goto(view({ tab: 'chat', user: 'alice' }))
  await page
    .getByRole('textbox', { name: 'Message input' })
    .fill('How robust is CodeQL taint tracking against LLM-rewritten vulnerable code?')
  await page.keyboard.press('Enter')
  const answer = page.locator('[data-role="assistant"]').last()
  await expect(answer).not.toBeEmpty({ timeout: LIVE ? 60_000 : 5_000 })
  await expect(page.locator('[data-role="assistant"] a[data-slot="source"]', { hasText: 'restricted' })).toHaveCount(0)
})

test('AC-3 switching the demo user changes the view and resets the chat thread @llm', async ({ page }) => {
  await page.goto(view({ tab: 'chat', user: 'bob' }))
  await page.getByRole('textbox', { name: 'Message input' }).fill('What is SatisFix?')
  await page.keyboard.press('Enter')
  await expect(page.locator('[data-role="assistant"]').last()).not.toBeEmpty({ timeout: LIVE ? 60_000 : 5_000 })

  await page.getByRole('combobox', { name: 'Demo user' }).click()
  await page.getByRole('option', { name: 'alice' }).click()
  await expect(page).not.toHaveURL(/user=bob/) // alice is the default, so nuqs drops it from the URL
  await expect(page.getByText('public user; sees open-licensed papers only')).toBeVisible()
  await expect(page.locator('[data-role="assistant"]')).toHaveCount(0)
})
