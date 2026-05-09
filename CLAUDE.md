# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概要

LIFF（LINE 前端）+ Flask（後端）+ MariaDB（資料庫）的個人持股 CRUD，由 LINE 圖文選單啟動，僅白名單使用者可進入。

## 程式碼結構

```
backend/
  run.py                      # 啟動入口：create_app() + debug 模式依 FLASK_ENV 決定
  requirements.txt
  app/
    __init__.py               # create_app()：Flask 工廠、validate_config、register_routes、cache header
    templates/
      index.html              # 單一 shell（無繼承）；{{ app_config | tojson }} 注入設定
    api/
      __init__.py             # register_routes()：掛載各 Blueprint
      holdings.py             # /api/holdings (GET/POST/PUT/DELETE)、/api/categories
      users.py                # /api/me、/api/strategy (GET/PUT)
      pages.py                # GET / 渲染 index.html（注入 app_config dict）
      system.py               # GET /health（無 /api prefix）
    core/
      config.py               # Config class（Flask config）、DB_CONFIG、validate_config(app)
      auth.py                 # require_line_auth decorator + LINE Access Token 驗證 + 白名單檢查
      db.py                   # PyMySQL get_conn() context manager（DictCursor、commit/rollback）
  scripts/
    ftp_upload.py             # FTP 部署腳本（從 repo root 執行）
    daily_brief.py            # Gemini 每日持股分析排程
frontend/
  webpack.config.js           # entry: src/js/portfolio.js → dist/bundle.{js,css}（MiniCssExtractPlugin）
  package.json
  src/
    js/
      config.js               # 從 <script id="app-config"> 讀取後端注入的設定
      liff-init.js            # liff.init / token / api() fetch wrapper / 403/401 全頁畫面
      portfolio.js            # 持股清單渲染、新增/編輯/刪除 modal
    css/
      style.css               # 所有樣式（webpack 編譯進 bundle.css）
  dist/
    bundle.js                 # webpack 輸出（Flask static_folder 指向此目錄）
    bundle.css
infra/
  docker-compose.yml          # 本地 MariaDB（port 3306）
sql/
  schema.sql                  # whitelist_users + stock_holdings 兩張表
```

## 架構重點

- **進入流程**：LINE 圖文選單 → LIFF 開啟 → 前端 `liff.getAccessToken()` → 每次 API 帶 `Authorization: Bearer <accessToken>` → 後端呼叫 `https://api.line.me/v2/profile` 取 `userId` → 查 `whitelist_users` → 不在白名單回 403（response 帶該 userId 給管理員加白名單）。**用 Access Token + Profile API**（不是 ID Token + verify），因為 LIFF SDK 會自動刷新 Access Token，不會像 ID Token 一樣短時間過期。
- **權限隔離**：`core/auth.py` 的 `require_line_auth` 驗證後把 userId 放到 `g.user_id`。所有 CRUD 一律用 `g.user_id`，**絕不接受前端傳入的 userId**。修改/刪除前用 `WHERE id=UNHEX(...) AND line_user_id=%s` 防越權（`rowcount=0` 回 404）。
- **不引入 LINE SDK**，後端直接用 `requests` 打 LINE Profile endpoint。
- **本地開發繞過驗證**：`FLASK_ENV=development` 且 `DEV_MODE_ENABLED=true` 且 host 為 localhost/127.0.0.1 時，`verify_access_token()` 直接回 `U_dev_test_user`；前端 `liff-init.js` 看到 `devMode=true` 時跳過 `liff.init`。
- **持股 id 是 BINARY(16) UUID**：INSERT 時 `SET @new_id = UNHEX(REPLACE(UUID(),'-',''))`；查詢 SELECT 時用 `HEX()` + 多次 `INSERT()` 轉回 hyphenated 字串；API 路徑收到字串先用 `_UUID_RE` 驗證格式。
- **分類欄位** 故意用 `VARCHAR(50)` 直接存字串，不另開 categories 表 — 重新命名分類用一句 UPDATE，前端 autocomplete 由 `/api/categories`（`SELECT DISTINCT category`）取得。
- **前端設定注入**：`backend/app/templates/index.html` 用 `<script type="application/json" id="app-config">` 載入 `liffId / devMode / scriptRoot`；`src/js/config.js` 用 `JSON.parse` 讀取，**不透過 `window.*`**。
- **Static folder**：`create_app()` 用 `pathlib.Path(__file__).parent.parent.parent / 'frontend' / 'dist'` 計算絕對路徑，掛在 `/static`。Cache header 依環境：`app.debug=True`（dev）→ `no-cache, must-revalidate`；prod → `public, max-age=31536000`。
- **API URL 帶 SCRIPT_ROOT**：部署在子路徑 `/portfolio/` 下，前端 `api()` 會自動 prepend `SCRIPT_ROOT`。

## 安全紅線（不可違反）

- 所有 SQL 必須用 PyMySQL 參數化 `%s`，禁止字串拼接。
- 不在 DB 存任何 token，只存 LINE userId。
- `market` 後端做 enum 檢查（只允許 `TW`/`US`），`symbol` 做 trim + upper + 長度 ≤ 20 檢查。
- DECIMAL 欄位後端要轉型 + 範圍檢查（`shares > 0`、`avg_price >= 0`，上限 1e14）。
- `.env` 必須在 `.gitignore` 中（已設定）。
- 路徑參數 `hid` 必須先過 `_valid_uuid` 正則，否則直接回 404（避免 UNHEX 觸發 SQL 錯誤）。

## 常用指令

```bash
# 後端
pip install -r backend/requirements.txt
cd backend && python run.py          # 本地開發伺服器

# 前端
cd frontend && npm install
cd frontend && npm run build         # 輸出 dist/bundle.js + dist/bundle.css
cd frontend && npm run watch         # 開發時 webpack watch

# 本地 DB（Docker）
docker compose -f infra/docker-compose.yml up -d
```

## 部署

- **CI/CD**：push 到 `main` → `.github/workflows/deploy.yml` 自動 `npm ci` + `npm run build` + `python backend/scripts/ftp_upload.py`。
- **FTP 上傳**：`backend/scripts/ftp_upload.py` 從 **repo root** 執行，白名單檔案見 `FILES_TO_UPLOAD`（只上傳必要檔案，不傳 `src/`、`node_modules/`）；上傳後寫入 `tmp/restart.txt` 觸發 Passenger reload。
- **目標 URL**：`https://<your-domain>/portfolio/`，LIFF endpoint 需指向此 URL。
- **白名單**：透過 phpMyAdmin 對 `whitelist_users` 手動 INSERT 維護（首次使用者會在 403 頁面看到自己的 userId 並可一鍵複製）。

## 功能改動後的必要檢查

每次改動功能後，**必須執行以下檢查**，確認無編譯錯誤才算完成：

```bash
# 前端：確認 webpack 能成功 build
cd frontend && npm run build

# 後端：確認所有 Python 檔案語法正確（遞迴掃描 backend/）
python -m compileall backend/
```

## 前端撰寫規範

- **禁止在 HTML 中寫 inline JavaScript**（`onclick`、`oninput` 等 event attribute）。所有事件綁定集中在 `portfolio.js` 的 `bindEvents()`；需要的 DOM 元素先在 `cacheEls()` 快取到 `els` 物件。

## 修改注意事項

- 新增需要部署的後端檔案要記得加進 `backend/scripts/ftp_upload.py` 的 `FILES_TO_UPLOAD`。
- 改 schema 時同步更新 `sql/schema.sql` 並通知使用者在伺服器手動執行 ALTER（沒有自動 migration 機制）。
- 新增 API route：在對應的 blueprint 檔案（`holdings.py` / `users.py` / `system.py`）加入，**不要**動 `api/api.py`（已廢棄）。
