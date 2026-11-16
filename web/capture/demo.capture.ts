import fs from 'node:fs'
import path from 'node:path'
import { type Locator, type Page, test } from '@playwright/test'

/*
 * Frames for the README demo (docs/media/demo). Live stack, except /api/chat: the chat answer is
 * staged so the capture never calls the LLM. Every sentence of it restates a verified abstract
 * quote stored in the corpus (GET /api/papers evidence), and the cited papers are real.
 */
const OUT = path.resolve(import.meta.dirname, '../../docs/media/demo/assets/capture')
const QUESTION = 'Which benchmarks are used to evaluate coding agents?'
const ANSWER = [
  'In this corpus, coding agents are evaluated on repository-level issue-resolution benchmarks:\n\n',
  '- **SWE-bench Pro** and **DeepSWE**: SatisFix improves the base agent\'s pass@1 by 5.09% on DeepSWE and 7.06% on the hard subset of SWE-bench Pro [1].\n',
  '- **ChainSWE**, successive tasks on an evolving repository: CoReMem raises the resolve rate from 21.0% to 25.7% [2].\n',
  '- **Robo-SWE**: 236 executable issue-resolution tasks mined from robot software repositories [3].\n',
].join('')
const SOURCES = [
  ['2611.16289', 'Eliciting and Mitigating Specification Satisficing in Coding Agents · Abstract'],
  ['2611.17316', 'CoReMem: Cost-Internalizing Memory for Successive Coding Tasks with Prospective Valuation · Abstract'],
  ['2611.16116', 'Robo-SWE: An Executable Issue-Resolution Dataset Mined from Robot Software Repositories · Abstract · restricted'],
]
function stagedStream() {
  const lines = ANSWER.match(/[\s\S]{1,24}/g)!.map((t) => `0:${JSON.stringify(t)}`)
  SOURCES.forEach(([id, title], i) =>
    lines.push(`h:${JSON.stringify({ sourceType: 'url', id: String(i + 1), url: `https://arxiv.org/abs/${id}`, title: `[${i + 1}] ${title}` })}`),
  )
  return lines.join('\n') + '\n'
}

type Frame = { file: string; note: string }
const frames: Frame[] = []
const targets: Record<string, { x: number; y: number; w: number; h: number }> = {}

async function shot(page: Page, note: string) {
  const file = `${String(frames.length).padStart(3, '0')}.jpg`
  await page.screenshot({ path: path.join(OUT, file), type: 'jpeg', quality: 88 })
  frames.push({ file, note })
}
async function mark(name: string, locator: Locator) {
  const box = (await locator.boundingBox())!
  targets[name] = { x: box.x, y: box.y, w: box.width, h: box.height }
}

test('capture demo frames', async ({ page }) => {
  fs.rmSync(OUT, { recursive: true, force: true })
  fs.mkdirSync(OUT, { recursive: true })
  let release = () => {}
  const answered = new Promise<void>((r) => (release = r))
  await page.route(
    (url) => url.pathname === '/api/chat',
    async (route) => {
      await answered
      await route.fulfill({ contentType: 'text/plain; charset=utf-8', body: stagedStream() })
    },
  )

  // 1. Ask
  await page.goto('/?tab=chat&user=bob')
  const input = page.getByRole('textbox', { name: 'Message input' })
  await input.waitFor()
  await page.waitForTimeout(500)
  await mark('composer', input)
  await shot(page, 'chat-empty')
  await input.click()
  const steps = 8
  for (let s = 1; s <= steps; s++) {
    await input.fill(QUESTION.slice(0, Math.round((QUESTION.length * s) / steps)))
    await shot(page, `type-${s}`)
  }
  await mark('send', page.getByRole('button', { name: /send/i }).last())
  await page.keyboard.press('Enter')
  await page.waitForTimeout(400)
  await shot(page, 'sent')
  release()
  const answer = page.locator('[data-role="assistant"]').last()
  await answer.locator('a[data-slot="source"]').nth(2).waitFor()
  await page.waitForTimeout(600)
  await mark('answer', answer)
  await shot(page, 'answer')

  // 2. Landscape at a glance
  const landscapeTab = page.getByRole('tab', { name: 'Landscape' })
  await mark('tab-landscape', landscapeTab)
  await landscapeTab.click()
  const strip = page.getByLabel('Papers per SDLC phase')
  await strip.getByRole('button').first().waitFor()
  await page.waitForTimeout(800)
  await shot(page, 'landscape')

  // 3. Graph at a glance
  const graphTab = page.getByRole('tab', { name: 'Knowledge graph' })
  await mark('tab-graph', graphTab)
  await graphTab.click()
  await page.waitForTimeout(2000)
  await shot(page, 'graph')

  // 4. Check a claim: 4. Testing -> its papers -> the quote behind a tag
  await landscapeTab.click()
  await strip.getByRole('button').first().waitFor()
  await page.waitForTimeout(600)
  const testing = strip.getByRole('button', { name: /^4\. Testing/ })
  await mark('phase-testing', testing)
  await testing.click()
  const panel = page.getByRole('complementary', { name: 'Papers behind the selection' })
  await panel.getByRole('listitem').first().waitFor()
  await page.waitForTimeout(700)
  await shot(page, 'testing')
  const why = panel.getByText('Why these tags? Quotes from the abstract').first()
  await mark('why', why)
  await why.click()
  await page.waitForTimeout(500)
  await mark('quote', panel.locator('details blockquote').first())
  await shot(page, 'evidence')

  fs.writeFileSync(
    path.join(OUT, 'capture.json'),
    JSON.stringify({ viewport: { width: 1920, height: 1080 }, question: QUESTION, frames, targets }, null, 2),
  )
})
