# Web workspace

Next.js 15, TypeScript, TanStack Query and Tailwind dependencies are prepared.
There are no pages or layouts in S0. Consequently there is no runnable web UI,
`next build` validation, or dev-server target yet. Add these at S8 against the
reviewed S6 API contract; install shadcn/ui components only when needed.

`npm run typecheck --workspace @equity/web` checks the current configuration.
No valuation arithmetic belongs in this workspace.
