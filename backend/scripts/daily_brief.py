#!/usr/bin/env python3
"""每日持股 AI 分析 + LINE Push。

流程：
  1. 撈出有設策略的白名單使用者
  2. 對每位使用者撈持股，組 prompt 丟給 gemini CLI
  3. 把 Gemini 回覆切段後 push 給該使用者

使用：
  python scripts/daily_brief.py                  # 正式跑（push 給所有人）
  python scripts/daily_brief.py --dry-run        # 不 push，只印到 stdout
  python scripts/daily_brief.py --user U_xxx     # 只跑指定使用者
  python scripts/daily_brief.py --user U_xxx --dry-run

需要環境變數：
  DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD
  LINE_MESSAGING_CHANNEL_ACCESS_TOKEN  （非 dry-run 時必填）

備註：crontab 設定的工作日判斷由 cron 自己處理，本腳本不檢查日期。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import requests

# 確保 import core.* 找得到 + gemini --include-directories 拿到專案 root
BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

# .env 載入（若有 python-dotenv 就用，沒有就略過）
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

from core.db import get_conn  # noqa: E402

LINE_PUSH_URL = 'https://api.line.me/v2/bot/message/push'
GEMINI_TIMEOUT_SEC = 300
GEMINI_MODEL = 'gemini-3-flash-preview'

# LINE text message 上限 5000 字、單次 push 最多 5 則
MSG_CHAR_LIMIT = 4900
MSG_PER_PUSH = 5
TRUNCATED_SUFFIX = '\n\n…(已截斷)'


def log(msg: str) -> None:
    print(f'[daily_brief] {msg}', file=sys.stderr, flush=True)


def fetch_users(only_user: str | None) -> list[dict]:
    sql = '''SELECT line_user_id, strategy
             FROM whitelist_users
             WHERE strategy IS NOT NULL AND strategy <> '' '''
    params: tuple = ()
    if only_user:
        sql += ' AND line_user_id=%s'
        params = (only_user,)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_holdings(line_user_id: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT market, symbol, name, category, shares, avg_price,
                          purchase_date, note
                   FROM stock_holdings
                   WHERE line_user_id=%s
                   ORDER BY category, market, symbol''',
                (line_user_id,),
            )
            return list(cur.fetchall())


def build_prompt(strategy: str, holdings: list[dict]) -> str:
    lines = ['| 市場 | 代號 | 名稱 | 分類 | 股數 | 平均買價 | 買入日 | 備註 |',
             '|------|------|------|------|------|----------|--------|------|']
    for h in holdings:
        lines.append('| {market} | {symbol} | {name} | {category} | {shares} | {avg_price} | {pd} | {note} |'.format(
            market=h['market'],
            symbol=h['symbol'],
            name=h.get('name') or '',
            category=h.get('category') or '',
            shares=str(h['shares']).rstrip('0').rstrip('.') if h.get('shares') is not None else '',
            avg_price=str(h['avg_price']).rstrip('0').rstrip('.') if h.get('avg_price') is not None else '',
            pd=h['purchase_date'].isoformat() if h.get('purchase_date') else '',
            note=(h.get('note') or '').replace('|', '/').replace('\n', ' '),
        ))
    holdings_md = '\n'.join(lines)

    return textwrap.dedent('''\
        以下是一份個人持股分析任務，所有資料已完整提供，不需要讀取任何檔案或詢問使用者。

        【使用者投資策略】
        {strategy}

        【持股清單（全部 {count} 筆）】
        {holdings}

        【任務】
        請依據上方策略，搜尋今日各持股的最新股價、重要公告或新聞，然後用繁體中文寫出分析。
        格式規定：
        - 純文字，不要使用 markdown 標題符號（#）或程式碼區塊
        - 第一段：一句話總結今日整體狀況
        - 接著逐檔給簡短重點（每檔 1~2 行）
        - 若有明顯偏離策略的部位，要特別點出來
        - 全文控制在 1500 字內
        ''').format(
        strategy=strategy.strip(),
        count=len(holdings),
        holdings=holdings_md,
    )


def call_gemini(prompt: str) -> str:
    # shutil.which 解決 Windows subprocess 找不到 gemini.cmd 的問題（Linux 也適用）。
    # --include-directories 必填：不帶會觸發 gemini CLI 的 quota bug（傳任何有效目錄
    # 都能繞過）。腳本一開始已 os.chdir(BASE_DIR)，這裡直接帶 BASE_DIR。
    gemini_bin = shutil.which('gemini') or 'gemini'
    cmd = [
        gemini_bin, '-m', GEMINI_MODEL,
        '--include-directories', str(BASE_DIR),
        '-y',                      # 自動同意所有 action，避免無 TTY 時卡在 approval prompt
        '-o', 'text',              # 純文字輸出
        '-p', prompt,
    ]
    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,  # 無 TTY 時避免 gemini 進 interactive 等 stdin
            capture_output=True,
            text=True,
            timeout=GEMINI_TIMEOUT_SEC,
            encoding='utf-8',
            errors='replace',
        )
    except FileNotFoundError as e:
        raise RuntimeError(f'找不到 gemini CLI：{e}') from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f'gemini 執行逾時 ({GEMINI_TIMEOUT_SEC}s)') from e

    if result.returncode != 0:
        err_tail = (result.stderr or '').strip()[:500]
        raise RuntimeError(
            f'gemini 失敗 (rc={result.returncode}): {err_tail or "(stderr 已 inherit 至 console)"}'
        )
    out = (result.stdout or '').strip()
    if not out:
        raise RuntimeError('gemini 回覆為空')
    return out


def split_messages(text: str) -> list[str]:
    """把長文切成 ≤ MSG_PER_PUSH 段、每段 ≤ MSG_CHAR_LIMIT 字；超過上限直接截斷。"""
    if not text:
        return []
    chunks: list[str] = []
    remaining = text
    while remaining and len(chunks) < MSG_PER_PUSH:
        if len(remaining) <= MSG_CHAR_LIMIT:
            chunks.append(remaining)
            remaining = ''
            break
        # 從上限位置往前找最近的換行/句點切分，避免切在字中間
        cut = MSG_CHAR_LIMIT
        for sep in ('\n\n', '\n', '。', ' '):
            idx = remaining.rfind(sep, 0, MSG_CHAR_LIMIT)
            if idx > MSG_CHAR_LIMIT // 2:
                cut = idx + len(sep)
                break
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:]

    if remaining:
        # 仍有剩 → 已達 5 則上限，最後一則加截斷標記
        last = chunks[-1]
        budget = MSG_CHAR_LIMIT - len(TRUNCATED_SUFFIX)
        if len(last) > budget:
            last = last[:budget].rstrip()
        chunks[-1] = last + TRUNCATED_SUFFIX
    return chunks


def push_line(token: str, line_user_id: str, messages: list[str]) -> None:
    if not messages:
        return
    payload = {
        'to': line_user_id,
        'messages': [{'type': 'text', 'text': m} for m in messages],
    }
    resp = requests.post(
        LINE_PUSH_URL,
        json=payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f'LINE push 失敗 ({resp.status_code}): {resp.text[:300]}')


def process_user(user: dict, token: str | None, dry_run: bool) -> None:
    uid = user['line_user_id']
    strategy = (user.get('strategy') or '').strip()
    log(f'處理使用者 {uid}')

    holdings = fetch_holdings(uid)
    if not holdings:
        log(f'  跳過：{uid} 無持股')
        return

    prompt = build_prompt(strategy, holdings)

    t0 = time.time()
    try:
        reply = call_gemini(prompt)
    except RuntimeError as e:
        log(f'  Gemini 錯誤：{e}')
        return
    log(f'  Gemini 回覆 {len(reply)} 字 ({time.time() - t0:.1f}s)')

    messages = split_messages(reply)
    log(f'  切為 {len(messages)} 則訊息')

    if dry_run:
        print(f'\n===== {uid} =====')
        for i, m in enumerate(messages, 1):
            print(f'--- msg {i}/{len(messages)} ({len(m)} chars) ---')
            print(m)
        return

    try:
        push_line(token, uid, messages)
        log(f'  已 push 給 {uid}')
    except RuntimeError as e:
        log(f'  LINE push 錯誤：{e}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Daily portfolio AI brief')
    parser.add_argument('--dry-run', action='store_true', help='不打 LINE，只印到 stdout')
    parser.add_argument('--user', help='只跑指定 line_user_id')
    args = parser.parse_args()

    token = os.getenv('LINE_MESSAGING_CHANNEL_ACCESS_TOKEN')
    if not args.dry_run and not token:
        log('缺少環境變數 LINE_MESSAGING_CHANNEL_ACCESS_TOKEN')
        return 1

    try:
        users = fetch_users(args.user)
    except Exception as e:
        log(f'撈使用者失敗：{e}')
        return 1

    if not users:
        log('沒有需要處理的使用者（無策略 / 找不到指定使用者）')
        return 0

    log(f'共 {len(users)} 位使用者待處理')
    for u in users:
        try:
            process_user(u, token, args.dry_run)
        except Exception as e:
            log(f'  使用者 {u["line_user_id"]} 處理失敗：{type(e).__name__}: {e}')

    log('完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
