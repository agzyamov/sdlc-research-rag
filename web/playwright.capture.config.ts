import { defineConfig, devices } from '@playwright/test'

/**
 * Captures real app frames for the README demo video (docs/media/demo, HyperFrames).
 * Not an acceptance test: separate testDir, never run in CI. Needs the live stack
 * (`uv run sdlcrag serve` + `pnpm dev` + services); the chat step calls the LLM once.
 *   pnpm exec playwright test -c playwright.capture.config.ts
 */
export default defineConfig({
  testDir: 'capture',
  testMatch: '*.capture.ts',
  timeout: 180_000,
  workers: 1,
  reporter: 'list',
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://127.0.0.1:5173',
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
    colorScheme: 'light',
  },
})
