import type { APIRequestContext } from '@playwright/test'
import type { PaperSummary } from '../../src/lib/api/generated'
import { PAPERS } from './mock-api'
import { LIVE } from './test'

/** All papers a user may read: from the live API, or the fixture dataset when mocked. */
export async function papersFor(request: APIRequestContext, user: string): Promise<PaperSummary[]> {
  if (!LIVE) return user === 'alice' ? PAPERS.filter((p) => p.license_class === 'open') : PAPERS
  const response = await request.get('/api/papers', { headers: { 'X-Demo-User': user } })
  return (await response.json()) as PaperSummary[]
}
