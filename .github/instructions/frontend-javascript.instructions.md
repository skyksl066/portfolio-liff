---
description: "Guidelines for writing vanilla browser JavaScript without a framework"
applyTo: "frontend/src/js/**/*.js"
---

# Frontend JavaScript Guidelines

## Module system
- Use ES modules (`import` / `export`). Never use IIFE wrappers or `<script>` tags without `type="module"` (or a bundler entry point).
- Every file must explicitly export what it exposes. Nothing is implicitly shared between files.

## No global scope pollution
- Never assign variables, functions, or config to `window.*`.
- Server-injected runtime config (e.g. from Flask) must be embedded in the HTML as a `<script type="application/json" id="app-config">` data node — the browser does not execute this tag. A dedicated bridge module (e.g. `config.js`) reads it once via `document.getElementById('app-config').textContent` and re-exports named constants. All other modules import from that bridge.
- State shared between modules must be passed as function arguments or imported from a shared module — never stored on `window`.

## File structure
- Organize source files under `src/js/` by responsibility:
  ```
  src/js/
    core/       # infrastructure with no feature logic (config, auth, API client, utilities)
    ui/         # shared UI components
    features/   # one sub-folder per feature; each owns its DOM, state, and API calls
    main.js     # entry point: wires everything together
  ```
- Keep `core/` free of feature logic. Each feature folder is self-contained.
- `main.js` is responsible for bootstrapping: caching DOM refs, initializing feature modules, and binding top-level events.
- Prefix private module-level variables and functions with `_`.

## Coding standards
- Use `const` by default; use `let` only when reassignment is required. Never use `var`.
- Use `async`/`await` for all asynchronous code. Do not use `.then()` chains.
- Use descriptive variable and function names. Do not add comments unless the logic is genuinely non-obvious.
- Prefer plain functions over classes for simple logic.
- Do not rely on hover-only interactions. All interactive elements must respond to click/tap.
