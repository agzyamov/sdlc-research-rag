/**
 * Module rules for the web app (ADR-0019): the TypeScript counterpart of import-linter.
 * Run: pnpm depcruise (part of pnpm check, pre-commit and CI).
 *
 *   pages ──> components, lib/api (+ lib/utils)
 *   components/{ui,assistant-ui}, hooks (vendored registry code) ──> lib/utils, hooks only
 *   lib/api ──> lib/api/generated (orval output from contracts/openapi.json)
 */
/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'stay-inside-web',
      comment:
        'The web app never imports from the Python repo or anywhere outside web/: the only ' +
        'shared artifact is contracts/openapi.json, consumed by orval at build time.',
      severity: 'error',
      from: { path: '^src' },
      to: { path: '^(?!src/|node_modules/)', pathNot: '^(vite/client|node:)' },
    },
    {
      name: 'api-only-via-lib-api',
      comment: 'Pages and components use the backend only through @/lib/api.',
      severity: 'error',
      from: { pathNot: '^src/lib/api' },
      to: { path: '^src/lib/api/generated' },
    },
    {
      name: 'http-client-only-in-lib-api',
      comment: 'No hand-written HTTP calls: axios is used only by the generated client.',
      severity: 'error',
      from: { pathNot: '^src/lib/api' },
      to: { path: 'node_modules/axios' },
    },
    {
      name: 'vendored-code-does-not-import-app-code',
      comment: 'Registry code (components, hooks) never depends on pages or the API client.',
      severity: 'error',
      from: { path: '^src/(components|hooks)' },
      to: { path: '^src/(pages|lib/api|App)' },
    },
    {
      name: 'lib-is-a-leaf',
      comment: 'lib/ holds no UI: it must not import pages or components.',
      severity: 'error',
      from: { path: '^src/lib' },
      to: { path: '^src/(pages|components)' },
    },
    {
      name: 'no-circular',
      severity: 'error',
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    // swc parses TypeScript without the compiler API that TypeScript 7.0 no longer ships.
    parser: 'swc',
    tsConfig: { fileName: 'tsconfig.app.json' },
    enhancedResolveOptions: { exportsFields: ['exports'], conditionNames: ['import', 'require', 'default'] },
  },
}
