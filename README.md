# portfolio-liff

LINE LIFF 個人持股管理頁面（Flask + MariaDB），由 LINE 圖文選單啟動，僅白名單使用者可進入。

## 功能

- LIFF 啟動 + LINE ID Token 驗證
- 白名單檢查（非白名單使用者顯示自己的 userId 給管理員加白名單）
- 持股 CRUD（市場、代號、名稱、分類、股數、均價、買入日、備註）
- 依分類分組折疊顯示，分類欄位 autocomplete

## 技術棧

| 元件 | 選擇 |
|---|---|
| Web 框架 | Flask 3.x |
| WSGI 入口 | `passenger_wsgi.py`（Phusion Passenger） |
| DB | MariaDB / MySQL（PyMySQL，純 Python 不需編譯）|
| LINE 驗證 | `https://api.line.me/oauth2/v2.1/verify`（不引入 LINE SDK）|
| 前端 | 原生 JS + LIFF SDK（CDN），無框架 |

## 目錄結構

```
portfolio-liff/
├── passenger_wsgi.py     # 託管伺服器 WSGI 入口
├── app.py                 # Flask 主檔
├── config.py              # 環境變數載入
├── db.py                  # MariaDB 連線（PyMySQL）
├── auth.py                # ID Token 驗證 + 白名單 decorator
├── routes/
│   ├── pages.py           # 頁面路由
│   └── api.py             # /api/* CRUD
├── templates/             # Jinja2 樣板
├── static/                # CSS / JS
├── sql/schema.sql         # 資料表 schema
├── requirements.txt
├── .env.example
└── plan.md                # 實作計劃（source of truth）
```

## 環境變數

複製 `.env.example` 為 `.env` 並填入：

| 變數 | 說明 |
|---|---|
| `LINE_CHANNEL_ID` | LIFF 所屬 LINE Login Channel 的 Channel ID（驗證 ID Token 用） |
| `LIFF_ID` | LIFF App ID（前端 `liff.init()` 用） |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | DB 連線資訊 |
| `FLASK_SECRET_KEY` | Flask session 用，部署時請改隨機字串 |
| `FLASK_ENV` | `development` 或 `production` |

> `.env` 已加入 `.gitignore`，不會被提交。

## 本地開發

### 1. 啟動 MariaDB

可用 docker 起一個：

```yaml
# tmp/docker-compose.yml（範例）
services:
  mariadb:
    image: mariadb:11.4
    container_name: portfolio-mariadb
    restart: unless-stopped
    ports:
      - "3306:3306"
    environment:
      MARIADB_ROOT_PASSWORD: "123456"
      MARIADB_DATABASE: "portfolio"
      MARIADB_USER: "portfolio"
      MARIADB_PASSWORD: "123456"
    volumes:
      - ./mariadb-data:/var/lib/mysql
```

```bash
docker compose -f tmp/docker-compose.yml up -d
```

### 2. 匯入 schema

```bash
docker exec -i portfolio-mariadb mariadb -uportfolio -p123456 portfolio < sql/schema.sql
```

### 3. 安裝相依 + 啟動

```bash
pip install -r requirements.txt
python app.py
```

預設啟動於 `http://127.0.0.1:5000/`。

> 本地不在 LINE 環境中，`liff.init()` 會失敗 → 主畫面會顯示無法啟動。要完整測試 UI，需走線上 LIFF 流程。本地可測：
> - `GET /health` → `ok`
> - `GET /api/me`（無 token）→ 401

## 部署到 Phusion Passenger 託管伺服器

### 1. 上傳檔案

把整個專案上傳到伺服器目錄（例如 `/home/<user>/domains/<domain>/portfolio/`）。**注意：所有 Python 檔案必須用空白縮排，不可混入 tab，否則 Passenger 啟動會 `TabError`**。

### 2. 設定 Python App

託管後台建立 Python App：

- URL：`/portfolio`
- 啟動檔：`passenger_wsgi.py`
- Python 版本：3.10+

### 3. 安裝相依

後台終端執行：

```bash
pip install -r requirements.txt
```

### 4. 設定環境變數

把 `.env` 上傳到專案根目錄（與 `passenger_wsgi.py` 同層），或直接在後台設定環境變數。

### 5. 初始化資料庫

進 phpMyAdmin（或同等工具）目標 database，匯入 `sql/schema.sql`。

### 6. 重啟 App

託管後台點「重啟」（或 `touch tmp/restart.txt`）。

驗證：瀏覽 `https://<your-domain>/portfolio/health` 應回 `ok`。

## LINE 設定

### LIFF App

LINE Developers Console → 對應 Provider → LINE Login Channel → LIFF：

- Endpoint URL：`https://<your-domain>/portfolio/`
- Size：Full / Tall（隨喜好）
- Scope：`profile`、`openid`
- Bot link feature：可不開

複製出 LIFF ID 與該 Channel 的 Channel ID 填到 `.env`。

### 圖文選單

LINE Official Account Manager → 圖文選單：

- 動作類型：連結
- 連結 URL：`https://liff.line.me/{LIFF_ID}`

### 取得自己的 userId（首次使用）

1. 從 LINE 圖文選單點進去
2. 因為還沒在白名單，會顯示 403 頁面與自己的 userId
3. 複製該 userId，到 phpMyAdmin INSERT 進白名單：
   ```sql
   INSERT INTO whitelist_users (line_user_id, display_name, note)
   VALUES ('Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', '你的名字', '管理員');
   ```
4. 重新從 LINE 進入即可

## API 一覽

所有 `/api/*` 需於 Header 帶 `Authorization: Bearer <idToken>`。

| Method | Path | 說明 |
|---|---|---|
| GET | `/` | LIFF 主頁 HTML |
| GET | `/health` | 健康檢查（無需驗證）|
| GET | `/api/me` | 驗證 + 白名單檢查 |
| GET | `/api/holdings` | 取得當前使用者全部持股 |
| POST | `/api/holdings` | 新增持股 |
| PUT | `/api/holdings/<id>` | 修改持股 |
| DELETE | `/api/holdings/<id>` | 刪除持股 |
| GET | `/api/categories` | 已用過的分類清單（autocomplete）|

錯誤格式：

```json
{ "error": "FORBIDDEN", "message": "不在白名單", "userId": "Uxxxxx..." }
```

狀態碼：`400` 欄位錯誤、`401` token 失效、`403` 不在白名單、`404` 找不到或非本人擁有。

## 安全要點

- 所有 SQL 用 PyMySQL 參數化（`%s`），絕無字串拼接
- 不在 DB 存任何 token，只存 LINE userId
- 後端 CRUD 一律用 token 解出的 userId（`g.user_id`），不接受前端傳入的 userId
- 修改 / 刪除 SQL 都帶 `WHERE id=%s AND line_user_id=%s` 防越權
- `market` 後端 enum 檢查（只允許 `TW` / `US`），`symbol` trim + upper
- DECIMAL 欄位後端轉型 + 範圍檢查（shares > 0、avg_price >= 0）
- `.env` 已在 `.gitignore`
