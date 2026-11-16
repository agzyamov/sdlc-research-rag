import { defineConfig } from 'orval'

// HTTP contract → typed client (ADR-0019). Source of truth: the FastAPI response models,
// exported to ../contracts/openapi.json by tools/gen_api_contract.py. Never edit the output.
export default defineConfig({
  sdlcrag: {
    input: { target: '../contracts/openapi.json' },
    output: {
      target: 'src/lib/api/generated.ts',
      // TanStack Query hooks over axios: loading/error/caching from the libraries, and axios
      // rejects non-2xx responses, so no hand-written fetch wrapper or data hook is needed.
      client: 'react-query',
      httpClient: 'axios',
      mode: 'single',
    },
  },
})
