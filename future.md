# Future Work

## AI 持股分析排程推播（後端自動化）

### 現況
使用者點擊 header 的 sparkle 按鈕，前端組合策略 + 持股清單後開啟 Perplexity（手機 deep link / 桌機網頁）讓使用者自行查詢。

### 下一階段目標
由後端排程自動對每位有設定策略的使用者執行分析，並將報告透過 LINE Message API 推播到使用者的 LINE。

### 規劃方向

- **排程腳本**：`backend/scripts/daily_analysis.py`（參考現有 `daily_brief.py` 架構）
- **分析來源**：改用 Perplexity API（`POST https://api.perplexity.ai/chat/completions`）取代 deep link，後端直接取得回應文字
- **資料撈取**：查 `stock_holdings` JOIN 使用者策略，逐一對有策略的使用者產生報告
- **推播**：呼叫 LINE Messaging API `push message`，帶 `line_user_id` 送出 Flex Message 或純文字
- **排程觸發**：cron / hosting 平台的排程功能，每日盤後執行一次
- **設定需求**：新增環境變數 `PERPLEXITY_API_KEY`、`LINE_CHANNEL_ACCESS_TOKEN`

### 注意事項
- Perplexity API 需付費方案才能呼叫
- 推播需要 LINE Official Account 並開啟 Messaging API
- 與現有 `daily_brief.py`（Gemini 分析）的定位需確認是否合併或並存



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


