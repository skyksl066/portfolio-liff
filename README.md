# portfolio-liff

LINE LIFF 個人持股管理頁面（Flask + MariaDB），由 LINE 圖文選單啟動，僅白名單使用者可進入。

## 技術棧

- 後端：Flask 3.x + PyMySQL（MariaDB / MySQL）
- 前端：原生 JS + LIFF SDK + webpack
- 部署：Phusion Passenger（FTP 自動部署 via GitHub Actions）

## 本地開發

```bash
pip install -r requirements.txt
npm install
npm run build
python app.py
```

複製 `.env.example` 為 `.env` 填入 `LIFF_ID` / `LINE_CHANNEL_ID` / DB 連線資訊即可。

DB schema 在 `sql/schema.sql`。

## 部署

push 到 `main` 即觸發 `.github/workflows/deploy.yml` 自動打包並 FTP 上傳。

詳細架構與安全規範見 `CLAUDE.md`。
