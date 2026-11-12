# Frontend

Vue 3 (`<script setup>`) + TypeScript + Vite single-page app, with Vue Router,
TanStack Vue Query, Tailwind CSS v4 and shadcn-vue. Node 22+ and npm.

## Setup and run

```sh
cd frontend
npm install
npm run dev        # http://localhost:5173; /api is proxied to the backend on localhost:8000
```

Start the backend separately (see `backend/README.md`).

## Checks

```sh
npm run lint          # ESLint (Vue + TypeScript rules)
npm run format:check  # Prettier (`npm run format` to fix)
npm run typecheck     # vue-tsc
npm run test:run      # Vitest, once (`npm test` watches)
npm run build         # type-check + production build into dist/
```

## API client

Types for the backend API are generated from FastAPI's OpenAPI schema with
[openapi-typescript](https://openapi-ts.dev/) and called through
[openapi-fetch](https://openapi-ts.dev/openapi-fetch/). After changing backend routes or
schemas, regenerate and commit the output:

```sh
npm run gen:api
```

This needs `uv` and the backend's dependencies, but no running server or database:
`gen:api:schema` runs `uv run python -m tracker.openapi ../frontend/openapi.json` in
`backend/`, then `gen:api:types` writes `src/api/schema.d.ts`. Both files are committed;
never edit them by hand.

Usage (see `src/api/health.ts`):

```ts
import { api, type Schemas } from '@/api/client'

const { data, error, response } = await api.GET('/api/health')
type Health = Schemas['HealthStatus']
```

Wrap calls in TanStack Vue Query composables (`useQuery` / `useMutation`) next to the
client, one module per resource under `src/api/`.

## Layout

- `src/router.ts`: routes (`createAppRouter(history?)`; tests pass `createMemoryHistory()`).
- `src/App.vue`: base layout with the main navigation.
- `src/views/`: one component per route.
- `src/components/`: app components, e.g. `MarkdownView` (renders Markdown with
  `markdown-it`, sanitized by DOMPurify so raw HTML cannot execute) and `PageHeader`.
- `src/components/ui/`: shadcn-vue components. Add more with
  `npx shadcn-vue@<version> add <component>` (configured by `components.json`).
- `src/lib/`: helpers (`cn` for class names, `renderMarkdown`).

Tests sit next to the code as `*.test.ts` and stub `fetch` rather than the API modules.
