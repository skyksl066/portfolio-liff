# Future Work

## Frontend JS Architecture Refactor

### Goal
Reorganize `frontend/src/js` by feature (MVP structure). `index.html` stays unchanged.

### New JS Structure
```
frontend/src/js/
  core/
    config.js       ← moved from src/js/config.js (no logic changes)
    liff.js         ← initLiff(), appAuth (LIFF SDK init only)
    auth.js         ← LINE token 驗證、白名單檢查相關邏輯
    api.js          ← api() fetch wrapper
    utils.js        ← escapeHtml, fmtNum, fmtDate (extracted from portfolio.js)
  ui/
    error-screens.js ← showForbidden, showFatal, showSessionExpired (from liff-init.js)
  features/
    holdings/
      index.js      ← all holdings logic: cachedHoldings, loadAndRender, renderHoldings,
                       showLoading, showError, openEdit, confirmDelete, form validation
    strategy/
      index.js      ← openStrategy, form submit
  main.js           ← entry point: DOMContentLoaded, cacheEls(), bindEvents(), auth flow
```

### Files to Delete After Refactor
- `frontend/src/js/portfolio.js`
- `frontend/src/js/liff-init.js`
- `frontend/src/js/config.js`

### webpack.config.js Change
```js
entry: './src/js/main.js',  // was: './src/js/portfolio.js'
```

### Dependency Graph (no circular deps)
```
config.js        → (none)
utils.js         → (none)
error-screens.js → utils.js
liff.js          → config.js, error-screens.js, @line/liff
auth.js          → liff.js
api.js           → config.js, auth.js, error-screens.js, @line/liff
features/holdings/index.js → core/api.js, core/utils.js
features/strategy/index.js → core/api.js
main.js          → all of the above
```

### Coding Guidelines to Follow
- `const` by default, `let` only for reassignment
- `async/await` only, no `.then()` chains
- ES modules (`import`/`export`) throughout
- No `window.*` assignments
- Prefix private module-level functions/vars with `_`


