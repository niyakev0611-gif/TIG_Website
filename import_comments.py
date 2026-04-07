#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
匯入舊 WordPress 留言到 Waline
用法：python3 import_comments.py
"""

import re
import json
import urllib.request
from urllib.parse import unquote
import time

# ── 設定 ────────────────────────────────────────────────────────────────────
WALINE_SERVER = "https://waline-server-lemon.vercel.app"
XML_PATH      = "taiwaneseingermany.WordPress.202602242.xml"

# WordPress 文章 URL 關鍵字 → 新網站 slug 對應
SLUG_MAP = {
    "永久居留":     "permanent-residence-2026",
    "永久居留權":   "permanent-residence-2026",
    "免付費德國銀行": "german-bank-recommendation",
    "deutschland-ticket": "deutschland-ticket",
    "49%e6%ad%90": "deutschland-ticket",
    "49歐":        "deutschland-ticket",
    "schufa":      "schufa-free",
    "dm%e9%80%80": "dm-tax-refund",
    "藥妝店":      "dm-tax-refund",
}

def map_slug(wp_url: str):
    decoded = unquote(wp_url).lower()
    for keyword, slug in SLUG_MAP.items():
        if keyword.lower() in decoded:
            return slug
    return None

# ── 讀取 XML ─────────────────────────────────────────────────────────────────
def extract_cdata(tag: str, text: str) -> str:
    m = re.search(rf'<{tag}><!\[CDATA\[(.*?)\]\]></{tag}>', text, re.DOTALL)
    if m: return m.group(1).strip()
    m = re.search(rf'<{tag}>(.*?)</{tag}>', text, re.DOTALL)
    return m.group(1).strip() if m else ''

def load_comments(xml_path: str):
    with open(xml_path, encoding='utf-8') as f:
        content = f.read()

    comments = []
    for item in re.findall(r'<item>(.*?)</item>', content, re.DOTALL):
        post_link = re.search(r'<link>(.*?)</link>', item)
        post_link = post_link.group(1) if post_link else ''
        slug = map_slug(post_link)
        if not slug:
            continue

        for c in re.findall(r'<wp:comment>(.*?)</wp:comment>', item, re.DOTALL):
            if extract_cdata('wp:comment_type', c) != 'comment':
                continue
            if extract_cdata('wp:comment_user_id', c) != '0':
                continue

            comments.append({
                'nick':    extract_cdata('wp:comment_author', c),
                'mail':    extract_cdata('wp:comment_author_email', c),
                'link':    extract_cdata('wp:comment_author_url', c),
                'comment': extract_cdata('wp:comment_content', c),
                'date':    extract_cdata('wp:comment_date_gmt', c),
                'url':     f'/post.html?slug={slug}',
            })

    # 按日期排序，新到舊
    comments.sort(key=lambda x: x['date'])
    return comments

# ── 呼叫 Waline API ──────────────────────────────────────────────────────────
def post_comment(entry: dict) -> bool:
    payload = {
        'nick':    entry['nick'] or '匿名',
        'mail':    entry['mail'],
        'link':    entry['link'],
        'comment': entry['comment'],
        'url':     entry['url'],
        'ua':      'WordPress-Migration/1.0',
    }
    data = json.dumps(payload).encode('utf-8')
    req  = urllib.request.Request(
        f"{WALINE_SERVER}/api/comment",
        data    = data,
        headers = {'Content-Type': 'application/json', 'User-Agent': 'WP-Migrator'},
        method  = 'POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get('errmsg') == '' or 'data' in result
    except Exception as e:
        print(f"    ❌ 錯誤：{e}")
        return False

# ── 主程式 ───────────────────────────────────────────────────────────────────
def main():
    comments = load_comments(XML_PATH)
    print(f"找到 {len(comments)} 則留言，開始匯入...\n")

    ok = fail = 0
    for i, c in enumerate(comments, 1):
        print(f"[{i:02}/{len(comments)}] {c['nick']} → {c['url']}")
        print(f"         {c['comment'][:60]}{'…' if len(c['comment']) > 60 else ''}")
        success = post_comment(c)
        if success:
            print("         ✅ 成功")
            ok += 1
        else:
            print("         ❌ 失敗")
            fail += 1
        time.sleep(0.5)  # 避免太快

    print(f"\n完成：成功 {ok}，失敗 {fail}")
    if fail > 0:
        print("失敗的留言可能需要手動在 Waline 管理後台新增。")

if __name__ == '__main__':
    main()
