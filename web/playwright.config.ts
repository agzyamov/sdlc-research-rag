import { defineConfig, devices } from '@playwright/test'

/**
 * Acceptance tests (docs/acceptance-criteria.md). Two modes, same specs:
 * - mocked (default, CI): the API is stubbed with typed fixtures (e2e/support/mock-api.ts);
 *   no LLM tokens, no Qdrant/Neo4j/OpenFGA.
 * - live (E2E_LIVE=1): against the real stack (`uv run sdlcrag serve` + services + corpus).
 *   Specs tagged @llm call the real LLM and run only with E2E_LLM=1 (they cost tokens).
 */
const live = !!process.env.E2E_LIVE
const llm = !!process.env.E2E_LLM

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  grepInvert: live ? (llm ? undefined : /@llm/) : /@live/,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    ...devices['Desktop Chrome'],
  },
  projects: [{ name: live ? 'live' : 'mocked' }],
  webServer: {
    command: 'pnpm dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
  },
})
