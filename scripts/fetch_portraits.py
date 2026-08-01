# -*- coding: utf-8 -*-
"""人物肖像抓取器 — 德國知識小種子 Das deutsche Wissen
================================================================
從 Wikimedia Commons 取得政治人物肖像，**只接受自由授權**，並把攝影者與
授權資訊寫進 manifest，供網站文章加上 figcaption 標示。

⚠️ 授權鐵則（2026/08 查證，勿自行放寬）
--------------------------------------------------------------
1. 「肖像權」不是問題：政治人物執行公職時屬時事人物（Person der
   Zeitgeschichte），編輯性報導引用其肖像，德國 KUG §23 已有豁免。
   **真正的關卡是攝影師的著作權**——照片本身必須有授權。
2. 只用 Wikimedia Commons 的自由授權圖：CC0／Public Domain／CC BY／CC BY-SA。
   姓名標示（攝影者＋授權名稱＋連結）是**義務**，不是禮貌。
3. **CC BY-SA 不可合成進圖卡**：Share-Alike 會傳染——把 SA 照片合成進
   1080x1080 PNG 等於製作衍生作品，整張圖卡就得改用 CC BY-SA 釋出。
   本腳本因此把授權分成兩級：
     • CARD_SAFE（CC0／PD／CC BY）：理論上可入圖卡
     • WEB_ONLY（CC BY-SA）：**只能**放網站文章、獨立 <img> ＋ figcaption
   目前專案政策：**圖卡一律維持 Seedling Flat 插畫，不放真人照片**
   （品牌一致性＋避免 SA 傳染），照片只用於網站長文。
4. 聯邦政府／聯邦議院官方新聞照**不要用**：其使用條款限於新聞編輯目的、
   商業用途須事先書面同意、社群媒體僅特定圖片可用、且禁止裁切調色以外
   的加工——不符本站工作流程。

用法
--------------------------------------------------------------
  python3 scripts/fetch_portraits.py --names "Thorsten Frei,Nina Warken"
  python3 scripts/fetch_portraits.py --html "Thorsten Frei"   # 印出可貼的 <figure>
  python3 scripts/fetch_portraits.py --list                   # 看目前圖庫
  python3 scripts/fetch_portraits.py --selftest               # 離線自我測試

輸出：assets/images/people/{slug}.jpg ＋ assets/images/people/portraits.json
圖庫跨週重複使用——同一位政治人物只需抓一次。
"""
import argparse
import json
import os
import re
import ssl
import sys
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'assets', 'images', 'people')
MANIFEST = os.path.join(OUT_DIR, 'portraits.json')

SIZE = 400          # 輸出方形邊長
TOP_BIAS = 0.12     # 方形裁切偏上（人臉通常在畫面上半）
UA = 'TIG-Website-portraits/1.0 (https://taiwanese-in-germany.com; niyakev0611@gmail.com)'

# 授權分級——鍵是 Commons extmetadata 的 LicenseShortName（正規化後）
CARD_SAFE = {'cc0', 'public domain', 'pd', 'cc by 2.0', 'cc by 3.0', 'cc by 4.0',
             'cc by 2.0 de', 'cc by 3.0 de'}
WEB_ONLY = {'cc by-sa 2.0', 'cc by-sa 3.0', 'cc by-sa 4.0',
            'cc by-sa 2.0 de', 'cc by-sa 3.0 de', 'cc by-sa 3.0 germany'}


def _opener():
    ca = '/root/.ccr/ca-bundle.crt'
    ctx = ssl.create_default_context(cafile=ca if os.path.exists(ca) else None)
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy:
        handlers.append(urllib.request.ProxyHandler({'https': proxy, 'http': proxy}))
    op = urllib.request.build_opener(*handlers)
    op.addheaders = [('User-Agent', UA)]
    return op


def api(host, params):
    url = f'https://{host}/w/api.php?' + urllib.parse.urlencode(params)
    return json.loads(_opener().open(url, timeout=30).read().decode())


def slugify(name):
    s = unicodedata.normalize('NFKD', name)
    s = s.replace('ß', 'ss')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return s


def strip_html(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


def normalize_license(s):
    return re.sub(r'\s+', ' ', (s or '').strip().lower())


def crop_square(img, top_bias=TOP_BIAS):
    """裁成正方形；直式照片偏上取（避免把頭切掉），橫式置中。"""
    w, h = img.size
    if w == h:
        return img
    if w < h:
        top = int((h - w) * top_bias)
        return img.crop((0, top, w, top + w))
    left = (w - h) // 2
    return img.crop((left, 0, left + h, h))


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_manifest(m):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2, sort_keys=True)


def resolve(name):
    """de.wikipedia 主圖 → Commons 授權資料。回傳 dict 或 None。"""
    r = api('de.wikipedia.org', dict(action='query', titles=name, prop='pageimages',
                                     piprop='name', format='json', formatversion=2,
                                     redirects=1))
    pages = r.get('query', {}).get('pages', [])
    if not pages or 'pageimage' not in pages[0]:
        print(f'  ❌ {name}：Wikipedia 無主圖')
        return None
    filename = pages[0]['pageimage']

    c = api('commons.wikimedia.org', dict(action='query', titles='File:' + filename,
                                          prop='imageinfo',
                                          iiprop='extmetadata|url', iiurlwidth=800,
                                          format='json', formatversion=2))
    cp = c.get('query', {}).get('pages', [])
    if not cp or 'imageinfo' not in cp[0]:
        print(f'  ❌ {name}：檔案不在 Commons（可能是本地上傳的合理使用圖）')
        return None
    ii = cp[0]['imageinfo'][0]
    em = ii.get('extmetadata', {})

    def g(k):
        return em.get(k, {}).get('value', '')

    lic_raw = g('LicenseShortName')
    lic = normalize_license(lic_raw)
    if lic in CARD_SAFE:
        tier = 'card_safe'
    elif lic in WEB_ONLY:
        tier = 'web_only'
    else:
        print(f'  ⛔ {name}：授權「{lic_raw or "未標示"}」不在自由授權允許清單，跳過')
        return None

    return dict(
        name=name,
        slug=slugify(name),
        file=f'{slugify(name)}.jpg',
        license=lic_raw,
        license_url=g('LicenseUrl'),
        artist=strip_html(g('Artist')) or '（未標示）',
        tier=tier,
        source_url=ii.get('descriptionurl', ''),
        thumburl=ii.get('thumburl') or ii.get('url'),
    )


def download(entry):
    from PIL import Image
    from io import BytesIO
    raw = _opener().open(entry['thumburl'], timeout=60).read()
    img = Image.open(BytesIO(raw)).convert('RGB')
    img = crop_square(img).resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, entry['file'])
    img.save(path, 'JPEG', quality=86, optimize=True)
    return path


def figure_html(e):
    """網站文章用的 <figure>——figcaption 的姓名標示是授權義務，勿刪。"""
    lic = (f'<a href="{e["license_url"]}" target="_blank" rel="noopener noreferrer">{e["license"]}</a>'
           if e.get('license_url') else e['license'])
    src = (f'<a href="{e["source_url"]}" target="_blank" rel="noopener noreferrer">Wikimedia Commons</a>'
           if e.get('source_url') else 'Wikimedia Commons')
    return (f'<figure class="post-portrait">\n'
            f'  <img src="assets/images/people/{e["file"]}" alt="{e["name"]}">\n'
            f'  <figcaption><span class="post-portrait__name">{e["name"]}</span>'
            f'<span class="post-portrait__credit">Foto: {e["artist"]}, {lic}, via {src}</span></figcaption>\n'
            f'</figure>')


def cmd_fetch(names, force=False):
    manifest = load_manifest()
    for name in names:
        name = name.strip()
        if not name:
            continue
        slug = slugify(name)
        if slug in manifest and not force and os.path.exists(os.path.join(OUT_DIR, manifest[slug]['file'])):
            print(f'  ⏭  {name}：圖庫已有，跳過（--force 可重抓）')
            continue
        entry = resolve(name)
        if not entry:
            continue
        try:
            download(entry)
        except Exception as exc:
            print(f'  ⚠️  {name}：下載失敗 {type(exc).__name__}: {exc}')
            continue
        entry.pop('thumburl', None)
        manifest[slug] = entry
        flag = '（CC BY-SA：僅限網站，勿入圖卡）' if entry['tier'] == 'web_only' else ''
        print(f'  ✅ {name} — {entry["license"]} / {entry["artist"]} {flag}')
    save_manifest(manifest)
    print(f'\n圖庫：{OUT_DIR}\nmanifest：{MANIFEST}')


def cmd_html(names):
    manifest = load_manifest()
    for name in names:
        slug = slugify(name.strip())
        if slug not in manifest:
            print(f'<!-- {name}：圖庫沒有，請先執行 --names "{name}" -->')
            continue
        print(figure_html(manifest[slug]))
        print()


def cmd_list():
    manifest = load_manifest()
    if not manifest:
        print('圖庫是空的。')
        return
    for slug in sorted(manifest):
        e = manifest[slug]
        tier = '圖卡可用' if e['tier'] == 'card_safe' else '僅網站（SA）'
        print(f'{e["name"]:24} {e["license"]:16} {tier:12} {e["artist"][:40]}')


def cmd_selftest():
    """離線驗證：裁切、slug、授權分級、HTML 產出。"""
    from PIL import Image
    ok = True

    tall = Image.new('RGB', (300, 500), 'white')
    c = crop_square(tall)
    ok &= c.size == (300, 300) and c.size[0] == c.size[1]
    print(f'  {"✅" if c.size == (300, 300) else "❌"} 直式裁切 300x500 → {c.size}')

    wide = Image.new('RGB', (900, 400), 'white')
    c2 = crop_square(wide)
    ok &= c2.size == (400, 400)
    print(f'  {"✅" if c2.size == (400, 400) else "❌"} 橫式裁切 900x400 → {c2.size}')

    cases = [('Thorsten Frei', 'thorsten-frei'), ('Markus Söder', 'markus-soder'),
             ('Sahra Wagenknecht', 'sahra-wagenknecht')]
    for raw, want in cases:
        got = slugify(raw)
        ok &= got == want
        print(f'  {"✅" if got == want else "❌"} slug {raw!r} → {got!r}')

    for lic, want in [('CC BY-SA 3.0', 'web_only'), ('CC BY 4.0', 'card_safe'),
                      ('CC0', 'card_safe'), ('Fair use', None)]:
        n = normalize_license(lic)
        got = 'card_safe' if n in CARD_SAFE else 'web_only' if n in WEB_ONLY else None
        ok &= got == want
        print(f'  {"✅" if got == want else "❌"} 授權分級 {lic!r} → {got}')

    demo = dict(name='Thorsten Frei', file='thorsten-frei.jpg', license='CC BY-SA 3.0',
                license_url='https://creativecommons.org/licenses/by-sa/3.0',
                artist='Tobias Koch', source_url='https://commons.wikimedia.org/wiki/File:X.jpg')
    html = figure_html(demo)
    ok &= 'post-portrait' in html and 'Tobias Koch' in html and 'CC BY-SA 3.0' in html
    print(f'  {"✅" if "Tobias Koch" in html else "❌"} figure HTML 含姓名標示')
    print('\n' + html)
    print('\n' + ('全部通過 ✅' if ok else '有失敗 ❌'))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description='從 Wikimedia Commons 抓自由授權的人物肖像')
    p.add_argument('--names', help='逗號分隔的人名（德文維基條目名）')
    p.add_argument('--html', help='印出這些人的 <figure> 片段（逗號分隔）')
    p.add_argument('--list', action='store_true', help='列出目前圖庫')
    p.add_argument('--force', action='store_true', help='已存在也重新抓')
    p.add_argument('--selftest', action='store_true', help='離線自我測試')
    a = p.parse_args()

    if a.selftest:
        return cmd_selftest()
    if a.list:
        return cmd_list()
    if a.html:
        return cmd_html(a.html.split(','))
    if a.names:
        return cmd_fetch(a.names.split(','), force=a.force)
    p.print_help()


if __name__ == '__main__':
    sys.exit(main() or 0)
