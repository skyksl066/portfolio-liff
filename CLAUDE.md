# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概要

LIFF（LINE 前端）+ Flask（後端）+ MariaDB（資料庫）的個人持股 CRUD，由 LINE 圖文選單啟動，僅白名單使用者可進入。

## 程式碼結構

```
app.py                  # Flask app factory + /health；註冊 pages_bp 與 api_bp(/api)
core/
  config.py             # 環境變數讀取與必要欄位驗證（validate_config）
  auth.py               # require_line_auth decorator + LINE Access Token 驗證 + 白名單檢查
  db.py                 # PyMySQL get_conn() context manager（DictCursor、commit/rollback）
routes/
  pages.py              # GET / 渲染 index.html（注入 liff_id / dev_mode / script_root）
  api.py                # /api/me, /api/holdings (GET/POST/PUT/DELETE), /api/categories
sql/schema.sql          # whitelist_users + stock_holdings 兩張表
src/js/
  config.js             # 從 <script id="app-config"> 讀取後端注入的設定
  liff-init.js          # liff.init / token / api() fetch wrapper / 403/401 全頁畫面
  portfolio.js          # 持股清單渲染、新增/編輯/刪除 modal
templates/{base,index}.html
static/css/style.css
static/dist/bundle.js   # webpack 打包輸出（由 src/js/portfolio.js 入口）
scripts/ftp_upload.py   # FTP 部署腳本（白名單檔案 + tmp/restart.txt 觸發 Passenger reload）
.github/workflows/deploy.yml  # push main 自動 npm build + FTP 上傳
webpack.config.js       # entry: src/js/portfolio.js → static/dist/bundle.js（production mode）
```

## 架構重點

- **進入流程**：LINE 圖文選單 → LIFF 開啟 → 前端 `liff.getAccessToken()` → 每次 API 帶 `Authorization: Bearer <accessToken>` → 後端呼叫 `https://api.line.me/v2/profile` 取 `userId` → 查 `whitelist_users` → 不在白名單回 403（response 帶該 userId 給管理員加白名單）。**用 Access Token + Profile API**（不是 ID Token + verify），因為 LIFF SDK 會自動刷新 Access Token，不會像 ID Token 一樣短時間過期。
- **權限隔離**：`core/auth.py` 的 `require_line_auth` 驗證後把 userId 放到 `g.user_id`。所有 CRUD 一律用 `g.user_id`，**絕不接受前端傳入的 userId**。修改/刪除前用 `WHERE id=UNHEX(...) AND line_user_id=%s` 防越權（`rowcount=0` 回 404）。
- **不引入 LINE SDK**，後端直接用 `requests` 打 LINE Profile endpoint。
- **本地開發繞過驗證**：`FLASK_ENV=development` 且 `DEV_MODE_ENABLED=true` 且 host 為 localhost/127.0.0.1 時，`verify_access_token()` 直接回 `U_dev_test_user`；前端 `liff-init.js` 看到 `devMode=true` 時跳過 `liff.init`。
- **持股 id 是 BINARY(16) UUID**：INSERT 時 `SET @new_id = UNHEX(REPLACE(UUID(),'-',''))`；查詢 SELECT 時用 `HEX()` + 多次 `INSERT()` 轉回 hyphenated 字串；API 路徑收到字串先用 `_UUID_RE` 驗證格式。
- **分類欄位** 故意用 `VARCHAR(50)` 直接存字串，不另開 categories 表 — 重新命名分類用一句 UPDATE，前端 autocomplete 由 `/api/categories`（`SELECT DISTINCT category`）取得。
- **前端設定注入**：`templates/base.html` 用 `<script type="application/json" id="app-config">` 載入 `liffId / devMode / scriptRoot`；`src/js/config.js` 用 `JSON.parse` 讀取，**不透過 `window.*`**（script 標籤 type 不是 JS，不會被執行）。
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
pip install -r requirements.txt   # 後端相依
npm install                        # 前端相依（webpack + @line/liff）
npm run build                      # 打包 src/js/portfolio.js → static/dist/bundle.js
npm run watch                      # 開發時 webpack watch
python app.py                      # 本地開發伺服器
```

## 部署

- **CI/CD**：push 到 `main` → `.github/workflows/deploy.yml` 自動 `npm ci` + `npm run build` + `python scripts/ftp_upload.py`。
- **FTP 上傳**白名單檔案見 `scripts/ftp_upload.py` 的 `FILES_TO_UPLOAD`（只上傳必要檔案，**不傳 src/**）；上傳後寫入 `tmp/restart.txt` 觸發 Passenger reload。
- **目標 URL**：`https://<your-domain>/portfolio/`，LIFF endpoint 需指向此 URL。
- **白名單**：透過 phpMyAdmin 對 `whitelist_users` 手動 INSERT 維護（首次使用者會在 403 頁面看到自己的 userId 並可一鍵複製）。

## 修改注意事項

- 改 `src/js/*.js` 後**必須執行 `npm run build`** 才會更新 `static/dist/bundle.js`；否則本地 / FTP 部署都會用到舊版 bundle。
- 新增需要部署的檔案要記得加進 `scripts/ftp_upload.py` 的 `FILES_TO_UPLOAD`，否則 GitHub Actions 不會上傳。
- 改 schema 時同步更新 `sql/schema.sql` 並通知使用者在伺服器手動執行 ALTER（沒有自動 migration 機制）。
