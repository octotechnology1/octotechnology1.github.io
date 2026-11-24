"""Build the OctoTechnology site from content/ + tools/templates/.

    python tools/build.py

Generates:
  index.html, 404.html, privacy/index.html, sitemap.xml, robots.txt
  apps/<slug>/index.html, apps/<slug>/privacy-android.html, apps/<slug>/privacy-ios.html
  lang/en.json, lang/uk.json, lang/ru.json, lang/sk.json
  <lang>/index.html, <lang>/apps/<slug>/index.html  — the home and app pages with the text already in uk/ru/sk
                                                     (search engines see every language; hreflang links them)

Content lives in:
  content/site/<lang>.json      — texts of the home page and shared labels
  content/apps/<slug>.json      — one file per app (status, links, colours, texts in 4 languages)
  content/policies/*.html       — ORIGINAL policy pages; their text is copied verbatim
  apps/<slug>/media/            — icons, covers, screenshots, video (tools/import_media.py)
  content/showreel.json         — chapters of the showreel (tools/import_media.py)

Needs: Python 3.10+, beautifulsoup4.
"""
import html
import json
import posixpath
import re
import sys
import time
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup

SITE_URL = "https://octotechnology1.github.io/"   # change here if the site moves (e.g. own domain)
OG_DIMS = ('  <meta property="og:image:width" content="1200">\n'
           '  <meta property="og:image:height" content="630">\n'
           '  <meta property="og:image:alt" content="OctoTechnology: the cyan octopus on the letter O">\n')   # только для обложки студии
LANGS = ["en", "uk", "ru", "sk"]
DEFAULT = "en"
FEATURES = 6

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "tools" / "templates"
VER = time.strftime("%Y%m%d%H%M")

GP_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#34a853" d="M3.6 1.8 13.4 12 3.6 22.2c-.4-.2-.6-.7-.6-1.2V3c0-.5.2-1 .6-1.2z"/>'
           '<path fill="#fbbc04" d="m16.8 8.6-3.4 3.4 3.4 3.4 3.9-2.2c.8-.5.8-1.7 0-2.2z"/>'
           '<path fill="#ea4335" d="M3.6 22.2 13.4 12l3.4 3.4L5 22.1c-.5.3-1 .3-1.4.1z"/>'
           '<path fill="#4285f4" d="M3.6 1.8c.4-.2.9-.2 1.4.1l11.8 6.7-3.4 3.4z"/></svg>')
APPLE_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M16.37 12.6c-.02-2.2 1.8-3.26 1.88-3.31'
              '-1.02-1.5-2.62-1.7-3.19-1.72-1.36-.14-2.65.8-3.34.8-.69 0-1.75-.78-2.88-.76-1.48.02-2.85.86-3.61 2.19-1.54 2.67'
              '-.39 6.62 1.11 8.79.73 1.06 1.6 2.25 2.75 2.21 1.1-.04 1.52-.71 2.85-.71 1.33 0 1.71.71 2.88.69 1.19-.02 1.94-1.08'
              ' 2.66-2.15.84-1.23 1.19-2.42 1.21-2.48-.03-.01-2.31-.89-2.32-3.55zM14.17 6.13c.6-.74 1.02-1.76.9-2.78-.88.04-1.94'
              '.59-2.57 1.32-.56.65-1.06 1.69-.93 2.69.98.08 1.98-.5 2.6-1.23z"/></svg>')


# ── helpers ────────────────────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s), quote=True)


def read(p):
    return Path(p).read_text(encoding="utf-8")


def write(p, text):
    p = ROOT / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    print("  wrote", p.relative_to(ROOT))


def render(tpl, d, vars_, slug=None):
    if slug:
        tpl = tpl.replace("@.", f"apps.{slug}.")
    for _ in range(3):  # snippets may contain [[...]] themselves
        tpl = re.sub(r"\[\[(\w+)\]\]", lambda m: str(vars_[m.group(1)]), tpl)
    if slug:
        tpl = tpl.replace("@.", f"apps.{slug}.")

    def text(m, raw):
        key = m.group(1)
        if key not in d:
            sys.exit(f"missing text key: {key}")
        return d[key] if raw else esc(d[key])
    tpl = re.sub(r"\{\{\{([\w.\-]+)\}\}\}", lambda m: text(m, True), tpl)
    tpl = re.sub(r"\{\{([\w.\-]+)\}\}", lambda m: text(m, False), tpl)
    return tpl


def t(key, tag="span", cls="", d=None, extra=""):
    """Element with a translatable text (default language inline, others via lang/*.json)."""
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-i18n="{key}"{extra}>{{{{{key}}}}}</{tag}>'


# ── content ────────────────────────────────────────────────────────────────
def load():
    site = {l: json.loads(read(ROOT / f"content/site/{l}.json")) for l in LANGS}
    apps = [json.loads(read(p)) for p in (ROOT / "content/apps").glob("*.json")]
    apps.sort(key=lambda a: a["order"])
    for a in apps:
        mf = ROOT / "apps" / a["slug"] / "media" / "manifest.json"
        a["media"] = json.loads(read(mf)) if mf.exists() else {"shots": [], "mark": None, "video": None}
    chap_file = ROOT / "content/showreel.json"
    chapters = json.loads(read(chap_file)) if chap_file.exists() else []
    return site, apps, chapters


def build_langs(site, apps):
    dicts = {}
    base_keys = set(site[DEFAULT])
    for l in LANGS:
        d = dict(site[l])
        missing = base_keys - set(d)
        if missing:
            print(f"  ! {l}: missing site keys -> fallback to {DEFAULT}: {sorted(missing)}")
            for k in missing:
                d[k] = site[DEFAULT][k]
        for a in apps:
            txt = dict(a["text"][DEFAULT])
            txt.update(a["text"].get(l, {}))
            for k, v in txt.items():
                d[f"apps.{a['slug']}.{k}"] = v
            # <title> и description страниц приложения переводятся целиком: «Имя — слоган · OctoTechnology»,
            # иначе после смены языка во вкладке и в поиске оставалось только имя приложения
            k, name = f"apps.{a['slug']}", txt["name"]
            d[f"{k}.page_title"] = f"{name} — {txt['tagline']} · OctoTechnology"
            d[f"{k}.policy_title_android"] = f"{name} — {d['policy.title']} (Android) · OctoTechnology"
            d[f"{k}.policy_title_ios"] = f"{name} — {d['policy.title']} (iOS) · OctoTechnology"
            d[f"{k}.policy_desc"] = f"{name} — {d['policy.title']}"
            d[f"{k}.support_title"] = f"{name} — {d['support.title']} · OctoTechnology"
            d[f"{k}.support_desc"] = f"{name} — {d['support.lead']}"
        dicts[l] = d
        write(f"lang/{l}.json", json.dumps(d, ensure_ascii=False, indent=0))
    return dicts


# ── policy extraction (text is kept verbatim) ─────────────────────────────
def extract_policy(src_html):
    soup = BeautifulSoup(src_html, "html.parser")
    body = soup.body
    for el in body.select("header.site-header, footer.site-footer, script, .clouds, .cats-layer"):
        el.decompose()
    hero = body.select_one("header.hero")
    if hero:
        for el in hero.select("img, .plate"):
            el.decompose()
        hero.name = "div"
        hero.attrs = {"class": ["policy-intro"]}
    for el in body.find_all("footer"):
        el.name = "div"
        el.attrs = {"class": ["policy-foot"]}
    for sel in ("div.wrap", "main"):
        for el in body.select(sel):
            el.unwrap()
    for h in body.find_all("h1"):
        h.name = "h2"
    for dv in body.find_all("div"):
        if not dv.get_text(strip=True) and not dv.find(["img", "table", "svg"]):
            dv.decompose()
    for a in body.find_all("a", href=True):
        h = a["href"]
        if h.startswith("privacy.html"):
            a["href"] = "privacy-android.html" + h[len("privacy.html"):]
    return body.decode_contents().strip()


def norm_text(s):
    return re.sub(r"\s+", " ", s).strip()


def verify_policy(src_html, out_html, app_name):
    """Every word of the original policy body must be in the copy (only the app-name plate is dropped)."""
    soup = BeautifulSoup(src_html, "html.parser")
    body = soup.body
    for el in body.select("header.site-header, footer.site-footer, script, .plate"):
        el.decompose()
    src = norm_text(body.get_text(" "))
    out = norm_text(BeautifulSoup(out_html, "html.parser").get_text(" "))
    if src != out:
        import difflib
        sm = difflib.SequenceMatcher(None, src, out)
        diff = [f"{op}: {src[a1:a2]!r} -> {out[b1:b2]!r}" for op, a1, a2, b1, b2 in sm.get_opcodes() if op != "equal"]
        sys.exit(f"policy text changed for {app_name}:\n  " + "\n  ".join(diff[:10]))


# ── snippets ───────────────────────────────────────────────────────────────
ANDROID_STATE = {"play": "live", "testing": "testing", "soon": "soon", "dev": "dev"}


def plat_chip(platform, state):
    return (f'<span class="status status-{state}"><b>{platform}</b>'
            f'<span data-i18n="st.{state}">{{{{st.{state}}}}}</span></span>')


def status_chip(a):
    """Two chips — Android and iOS — each: live · testing · soon · dev."""
    return ('<span class="plat-chips">' + plat_chip("Android", ANDROID_STATE.get(a["status"], a["status"]))
            + plat_chip("iOS", a.get("ios_status", "soon")) + '</span>')


def support_path(a):
    return f"apps/{a['slug']}/support.html"


def app_url(a, root):
    return f"{root}apps/{a['slug']}/index.html"


def policy_path(a, kind):
    return f"apps/{a['slug']}/privacy-{kind}.html"


def orbit_items(apps, root):
    n = len(apps)
    out = []
    for i, a in enumerate(apps):
        out.append(
            f'            <a class="orbit-item" style="--a:{i * 360 / n:.1f}deg" href="{app_url(a, root)}" '
            f'aria-label="{esc(a["text"][DEFAULT]["name"])}"><span class="orbit-face">'
            f'<img src="{root}apps/{a["slug"]}/media/icon.webp" alt="" width="92" height="92"></span></a>')
    return "\n".join(out)


def shelf(apps, root):
    per_set = max(1, -(-8 // len(apps)))  # repeat apps so one set is wider than a wide screen
    def book(a, hidden):
        th = a["theme"]
        tab = ' tabindex="-1"' if hidden else ""
        k = f"apps.{a['slug']}"
        return (f'            <a class="book" href="{app_url(a, root)}"{tab} style="--book-a:{th["a"]};--book-b:{th["ink"]}">'
                f'<div class="book-3d"><img class="book-cover-img" src="{root}apps/{a["slug"]}/media/cover.webp" alt="" '
                f'width="560" height="560" decoding="async"><span class="book-gloss"></span>'
                f'<img class="book-badge" src="{root}apps/{a["slug"]}/media/icon.webp" alt="" width="52" height="52"></div>'
                f'<div class="book-cap"><h3 data-i18n="{k}.name">{{{{{k}.name}}}}</h3>'
                f'<p class="book-meta" data-i18n="{k}.meta">{{{{{k}.meta}}}}</p>{status_chip(a)}</div></a>')
    sets = []
    for s in range(2):
        hidden = s == 1
        items = [book(a, hidden) for _ in range(per_set) for a in apps]
        attr = ' aria-hidden="true"' if hidden else ""
        sets.append(f'          <div class="shelf-set"{attr}>\n' + "\n".join(items) + "\n          </div>")
    return "\n".join(sets)


def reel_chips(apps, chapters, root):
    by = {c["app"]: c["t"] for c in chapters}
    out = []
    for a in apps:
        if a["slug"] not in by:
            continue
        k = f"apps.{a['slug']}.name"
        out.append(f'          <button class="reel-chip" type="button" data-app="{a["slug"]}" data-t="{by[a["slug"]]}">'
                   f'<img src="{root}apps/{a["slug"]}/media/icon.webp" alt="" width="30" height="30">'
                   f'<span data-i18n="{k}">{{{{{k}}}}}</span></button>')
    return "\n".join(out)


def privacy_links_inline(a, root):
    pol = a["policy"]
    support = f'<a href="{root}{support_path(a)}" data-i18n="apps.support">{{{{apps.support}}}}</a>'
    if not pol.get("android") and not pol.get("ios"):
        return (f'<div class="app-card-privacy"><span data-i18n="apps.privacy">{{{{apps.privacy}}}}</span>'
                f'<span class="muted-pill" data-i18n="privacy.soon">{{{{privacy.soon}}}}</span>· {support}</div>')
    return (f'<div class="app-card-privacy"><span data-i18n="apps.privacy">{{{{apps.privacy}}}}</span>'
            f'<a href="{root}{policy_path(a, "android")}" data-i18n="apps.android">{{{{apps.android}}}}</a>'
            f'<a href="{root}{policy_path(a, "ios")}" data-i18n="apps.ios">{{{{apps.ios}}}}</a>· {support}</div>')


def play_button(a, small=False):
    if a.get("play_live") and a.get("play"):
        return (f'<a class="store-btn" href="{esc(a["play"])}" target="_blank" rel="noopener">{GP_ICON}'
                f'<span><small>GET IT ON</small>Google Play</span></a>')
    return (f'<span class="store-btn off">{GP_ICON}<span><small>Google Play</small>'
            f'<span data-i18n="apps.play_soon">{{{{apps.play_soon}}}}</span></span></span>')


def appstore_button(a):
    if a.get("appstore_live") and a.get("appstore"):
        return (f'<a class="store-btn" href="{esc(a["appstore"])}" target="_blank" rel="noopener">{APPLE_ICON}'
                f'<span><small>Download on the</small>App Store</span></a>')
    return (f'<span class="store-btn off">{APPLE_ICON}<span><small>iPhone · iPad</small>'
            f'<span data-i18n="app.appstore_soon">{{{{app.appstore_soon}}}}</span></span></span>')


def app_cards(apps, root):
    out = []
    for a in apps:
        k = f"apps.{a['slug']}"
        th = a["theme"]
        extra = ""
        if a.get("test_url"):
            extra += f'<a class="btn btn-ghost btn-sm" href="{esc(a["test_url"])}" target="_blank" rel="noopener" data-i18n="apps.test">{{{{apps.test}}}}</a>'
        out.append(f'''          <article class="app-card" style="--app-a:{th["a"]};--app-b:{th["b"]}">
            <div class="app-card-art"><img src="{root}apps/{a["slug"]}/media/feature.webp" alt="" width="1024" height="500" loading="lazy">{status_chip(a)}</div>
            <div class="app-card-body">
              <div class="app-card-head"><img class="app-card-icon" src="{root}apps/{a["slug"]}/media/icon.webp" alt="" width="76" height="76">
                <div><h3><a class="link-cover" href="{app_url(a, root)}" style="color:inherit;text-decoration:none" data-i18n="{k}.name">{{{{{k}.name}}}}</a></h3><span class="meta" data-i18n="{k}.meta">{{{{{k}.meta}}}}</span></div></div>
              <p class="app-card-tagline" data-i18n="{k}.tagline">{{{{{k}.tagline}}}}</p>
              <p class="app-card-price"><span aria-hidden="true">💳 </span><span data-i18n="{k}.price">{{{{{k}.price}}}}</span></p>
              <div class="app-card-actions"><a class="btn btn-violet btn-sm" href="{app_url(a, root)}" data-i18n="apps.more">{{{{apps.more}}}}</a>{extra}</div>
              {privacy_links_inline(a, root)}
            </div>
          </article>''')
    return "\n".join(out)


MARK_ROLES = [  # (image, text key prefix, app slug)
    ("assets/mark/teacher_heart.webp", "mark.r1", "twomeows"),
    ("assets/mark/mechanic.webp", "mark.r2", "marks-garage"),
    ("assets/mark/host_fly.webp", "mark.r3", "mark-the-cat"),
    ("assets/mark/artist_hello.webp", "mark.r4", "marks-art"),
    ("assets/mark/home_cheer.webp", "mark.r5", "marks-home"),
    ("assets/mark/trains_cheer.webp", "mark.r6", "marks-trains"),
]


def mark_tiles(root):
    out = []
    for img, k, slug in MARK_ROLES:
        out.append(f'          <a class="mark-tile" href="{root}apps/{slug}/index.html"><div class="mark-tile-img">'
                   f'<img src="{root}{img}" alt="" loading="lazy"></div>'
                   f'<h3 data-i18n="{k}t">{{{{{k}t}}}}</h3><p data-i18n="{k}d">{{{{{k}d}}}}</p></a>')
    return "\n".join(out)


def policy_cell(a, kind, root):
    if not a["policy"].get(kind):
        return '<span class="muted-pill" data-i18n="privacy.soon">{{privacy.soon}}</span>'
    path = policy_path(a, kind)
    full = SITE_URL + path
    label = "apps.android" if kind == "android" else "apps.ios"
    return (f'<div class="policy-link"><a href="{root}{path}" data-i18n="{label}">{{{{{label}}}}}</a>'
            f'<button class="copy-btn" type="button" data-copy="{full}" data-i18n="privacy.copy">{{{{privacy.copy}}}}</button></div>'
            f'<span class="policy-url">{full}</span>')


def policy_table(apps, root):
    rows = []
    for a in apps:
        k = f"apps.{a['slug']}.name"
        rows.append(f'''          <tr>
            <td data-th=""><a class="policy-app" href="{app_url(a, root)}" style="color:inherit;text-decoration:none"><img src="{root}apps/{a["slug"]}/media/icon.webp" alt="" width="40" height="40"><span data-i18n="{k}">{{{{{k}}}}}</span></a><a class="policy-support" href="{root}{support_path(a)}" data-i18n="privacy.support">{{{{privacy.support}}}}</a></td>
            <td data-th="Android">{policy_cell(a, "android", root)}</td>
            <td data-th="iOS">{policy_cell(a, "ios", root)}</td>
          </tr>''')
    return ('        <table class="policy-table">\n          <thead><tr><th data-i18n="privacy.app">{{privacy.app}}</th>'
            '<th data-i18n="privacy.android">{{privacy.android}}</th><th data-i18n="privacy.ios">{{privacy.ios}}</th></tr></thead>\n'
            '          <tbody>\n' + "\n".join(rows) + '\n          </tbody>\n        </table>')


def head(d, root, title_key, desc_key, canonical, og_image, theme="#a9d3e9", title_override=None, desc_override=None,
         extra=""):
    tpl = read(TPL / "_head.html")
    return render(tpl, d, {
        "title_key": title_key, "desc_key": desc_key,
        "title": esc(title_override or d[title_key]), "desc": esc(desc_override or d[desc_key]),
        "canonical": canonical, "og_image": og_image, "theme_color": theme, "root": root, "ver": VER,
        "og_dims": OG_DIMS if og_image.endswith("assets/brand/og-cover.jpg") else "",
        "extra_head": extra,
    })


def chrome(d, root, home):
    v = {"root": root, "home": home, "ver": VER}
    return render(read(TPL / "_header.html"), d, v), render(read(TPL / "_footer.html"), d, v)


def brand_dims():
    """Размеры полотен логотипа и героя (их пишет tools/brand.py), чтобы страница не прыгала при загрузке картинок."""
    f = ROOT / "content" / "brand.json"
    d = json.loads(read(f)) if f.exists() else {}
    return {"logo_w": str(d.get("logo_w", 800)), "logo_h": str(d.get("logo_h", 464)),
            "octo_w": str(d.get("octo_w", 440)), "octo_h": str(d.get("octo_h", 458))}


def org_jsonld():
    """Студия для поисковиков: название, сайт, логотип, почта (schema.org Organization)."""
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "OctoTechnology", "url": SITE_URL,
           "logo": SITE_URL + "assets/brand/android-chrome-512.png", "email": "octo.technology.dev@gmail.com"}
    return '  <script type="application/ld+json">' + json.dumps(org, ensure_ascii=False) + '</script>\n'


# ── pages ──────────────────────────────────────────────────────────────────
def build_home(d, apps, chapters):
    root = ""
    header, footer = chrome(d, root, "")
    v = {
        "head": head(d, root, "meta.title", "meta.desc", SITE_URL, SITE_URL + "assets/brand/og-cover.jpg", extra=org_jsonld()),
        "header": header, "footer": footer, "ver": VER, **brand_dims(),
        "orbit_items": orbit_items(apps, root), "shelf": shelf(apps, root),
        "chapters_json": esc(json.dumps(chapters)), "reel_chips": reel_chips(apps, chapters, root),
        "app_cards": app_cards(apps, root), "mark_tiles": mark_tiles(root),
        "policy_table": policy_table(apps, root), "app_count": str(len(apps)),
    }
    write("index.html", render(read(TPL / "home.html"), d, v))


def build_app(d, a, apps):
    slug, root = a["slug"], "../../"
    k = f"apps.{slug}"
    th = a["theme"]
    m = a["media"]
    header, footer = chrome(d, root, root + "index.html")

    stores = [play_button(a)]
    if a.get("test_url"):
        stores.append(f'<a class="btn btn-ghost btn-sm" href="{esc(a["test_url"])}" target="_blank" rel="noopener" data-i18n="apps.test">{{{{apps.test}}}}</a>')
    if a.get("website"):
        stores.append(f'<a class="btn btn-ghost btn-sm" href="{esc(a["website"])}" target="_blank" rel="noopener" data-i18n="app.site">{{{{app.site}}}}</a>')
    stores.insert(1, appstore_button(a))

    feats = []
    for i in range(1, FEATURES + 1):
        emoji = a["emoji"][i - 1] if i - 1 < len(a["emoji"]) else "⭐"
        feats.append(f'          <div class="card"><div class="card-emoji">{emoji}</div>'
                     f'<h3 data-i18n="{k}.f{i}t">{{{{{k}.f{i}t}}}}</h3><p data-i18n="{k}.f{i}d">{{{{{k}.f{i}d}}}}</p></div>')

    shots = ""
    if m["shots"]:
        items = "\n".join(
            f'          <button type="button"{" class=\"portrait\"" if s["portrait"] else ""} data-full="media/{s["file"]}">'
            f'<img src="media/{s["file"]}" alt="" loading="lazy" decoding="async"></button>' for s in m["shots"])
        shots = f'''    <section class="section" id="shots">
      <div class="section-inner reveal">
        <h2 data-i18n="app.shots">{{{{app.shots}}}}</h2>
        <div class="gallery">
{items}
        </div>
      </div>
    </section>'''

    video = ""
    if m.get("video"):
        video = f'''    <section class="section" id="video">
      <div class="section-inner reveal">
        <h2 data-i18n="app.video">{{{{app.video}}}}</h2>
        <div class="video-box"><video controls playsinline preload="none" poster="media/promo.jpg"><source src="media/promo.mp4" type="video/mp4"></video></div>
      </div>
    </section>'''

    cards = []
    for kind, icon, label in (("android", "🤖", "policy.android"), ("ios", "🍏", "policy.ios")):
        if a["policy"].get(kind):
            full = SITE_URL + policy_path(a, kind)
            cards.append(f'''          <div class="policy-card"><div class="pc-icon">{icon}</div><div>
            <h3 data-i18n="{label}">{{{{{label}}}}}</h3><span class="policy-url">{full}</span>
            <div class="row"><a class="btn btn-violet btn-sm" href="privacy-{kind}.html" data-i18n="app.open">{{{{app.open}}}}</a>
            <button class="copy-btn" type="button" data-copy="{full}" data-i18n="privacy.copy">{{{{privacy.copy}}}}</button></div></div></div>''')
        else:
            cards.append(f'''          <div class="policy-card"><div class="pc-icon">{icon}</div><div>
            <h3 data-i18n="{label}">{{{{{label}}}}}</h3><p><span class="muted-pill" data-i18n="privacy.soon">{{{{privacy.soon}}}}</span></p>
            <div class="row"><a class="btn btn-ghost btn-sm" href="privacy-{kind}.html" data-i18n="app.open">{{{{app.open}}}}</a></div></div></div>''')
    sfull = SITE_URL + support_path(a)
    cards.append(f'''          <div class="policy-card"><div class="pc-icon">🛟</div><div>
            <h3 data-i18n="app.support_t">{{{{app.support_t}}}}</h3><p class="pc-note" data-i18n="app.support_d">{{{{app.support_d}}}}</p><span class="policy-url">{sfull}</span>
            <div class="row"><a class="btn btn-violet btn-sm" href="support.html" data-i18n="app.open">{{{{app.open}}}}</a>
            <button class="copy-btn" type="button" data-copy="{sfull}" data-i18n="privacy.copy">{{{{privacy.copy}}}}</button></div></div></div>''')

    others = "\n".join(
        f'          <a class="mini-app" href="../{o["slug"]}/index.html"><img src="../{o["slug"]}/media/icon.webp" alt="" width="52" height="52">'
        f'<div><b data-i18n="apps.{o["slug"]}.name">{{{{apps.{o["slug"]}.name}}}}</b><span data-i18n="apps.{o["slug"]}.meta">{{{{apps.{o["slug"]}.meta}}}}</span></div></a>'
        for o in apps if o["slug"] != slug)

    dev_note = ""
    if a["status"] == "dev" or not m["shots"]:
        dev_note = '        <p class="dev-note" data-i18n="app.dev_note">{{app.dev_note}}</p>'

    cats_layer, series = "", ""
    if a.get("line") == "mark":   # серия «Приключения кота Марка»; у приложений студии без кота — ни кота, ни подписи серии
        peek = a.get("peek", "host_wave")
        peek_file = next((p.name for p in (ROOT / "assets/mark").glob(peek + ".*")), "host_wave.webp")
        flip = " flip" if a.get("peek_flip") else ""
        cats_layer = (f'  <div class="cats-layer" aria-hidden="true">\n'
                      f'    <img class="cat cat-left cat-m{flip}" data-cat="features" src="../../assets/mark/{peek_file}" alt="">\n'
                      f'    <img class="cat cat-right cat-m" data-cat="privacy" src="../../assets/mark/host_thumb.webp" alt="">\n'
                      f'  </div>')
        series = ('<p class="app-series"><a href="../../index.html#mark" data-i18n="series.mark">{{series.mark}}</a></p>')
    url = SITE_URL + f"apps/{slug}/"
    # Smart App Banner у Safari на iPhone/iPad — з'явиться сам, щойно в JSON буде apple_id
    smart = f'  <meta name="apple-itunes-app" content="app-id={esc(a["apple_id"])}">\n' if a.get("apple_id") else ""
    v = {
        "head": head(d, root, f"{k}.page_title", f"{k}.tagline", url, SITE_URL + f"apps/{slug}/media/icon-512.png",
                     th["b"], extra=smart),
        "header": header, "footer": footer,
        "theme_style": f"--app-a:{th['a']};--app-b:{th['b']};--app-ink:{th['ink']}",
        "status_chip": status_chip(a), "age": esc(a["age"]), "store_buttons": "\n".join("            " + s for s in stores),
        "mark_file": m.get("mark") or "mark.webp", "features": "\n".join(feats),
        "shots_section": shots, "video_section": video, "policy_cards": "\n".join(cards), "others": others,
        "dev_note": dev_note, "cats_layer": cats_layer, "series": series,
    }
    write(f"apps/{slug}/index.html", render(read(TPL / "app.html"), d, v, slug=slug))

    # policy pages
    for kind in ("android", "ios"):
        src = a["policy"].get(kind)
        if src:
            src_html = read(ROOT / "content/policies" / src)
            body = extract_policy(src_html)
            verify_policy(src_html, body, f"{slug}/{kind}")
        else:
            src = "—"
            body = ('<div class="policy-soon"><div class="big">🛠️</div>'
                    '<h2 data-i18n="policy.soon_t">{{policy.soon_t}}</h2><p data-i18n="policy.soon_d">{{policy.soon_d}}</p></div>')
        purl = SITE_URL + policy_path(a, kind)
        pv = {
            "head": head(d, root, f"{k}.policy_title_{kind}", f"{k}.policy_desc", purl,
                         SITE_URL + f"apps/{slug}/media/icon-512.png", th["b"]),
            "header": header, "footer": footer,
            "theme_style": f"--app-a:{th['a']};--app-b:{th['b']};--app-ink:{th['ink']}",
            "android_active": ' class="active" aria-current="page"' if kind == "android" else "",
            "ios_active": ' class="active" aria-current="page"' if kind == "ios" else "",
            "policy_html": "%%POLICY%%" if src != "—" else body, "source": src,
        }
        page = render(read(TPL / "policy.html"), d, pv, slug=slug)
        if src != "—":  # inserted after templating, so nothing in the legal text can be altered
            page = page.replace("%%POLICY%%", body)
        write(policy_path(a, kind), page)

    # support page — its URL is the "Support URL" for App Store Connect (and fine for Google Play too)
    subject = urllib.parse.quote(f"{a['text'][DEFAULT]['name']} — support")
    links = []
    for kind, label in (("android", "policy.android"), ("ios", "policy.ios")):
        if a["policy"].get(kind):
            links.append(f'          <li><a href="privacy-{kind}.html" data-i18n="{label}">{{{{{label}}}}}</a></li>')
        else:
            links.append(f'          <li><span data-i18n="{label}">{{{{{label}}}}}</span> — '
                         f'<span class="muted-pill" data-i18n="privacy.soon">{{{{privacy.soon}}}}</span></li>')
    sv = {
        "head": head(d, root, f"{k}.support_title", f"{k}.support_desc", SITE_URL + support_path(a),
                     SITE_URL + f"apps/{slug}/media/icon-512.png", th["b"]),
        "header": header, "footer": footer,
        "theme_style": f"--app-a:{th['a']};--app-b:{th['b']};--app-ink:{th['ink']}",
        "status_chip": status_chip(a), "policy_links": "\n".join(links),
        "mailto": f"mailto:octo.technology.dev@gmail.com?subject={subject}",
    }
    write(support_path(a), render(read(TPL / "support.html"), d, sv, slug=slug))


def build_privacy_index(d, apps):
    root = "../"
    header, footer = chrome(d, root, root + "index.html")
    v = {"head": head(d, root, "privacy.page_title", "privacy.lead", SITE_URL + "privacy/", SITE_URL + "assets/brand/og-cover.jpg"),
         "header": header, "footer": footer, "policy_table": policy_table(apps, root)}
    write("privacy/index.html", render(read(TPL / "privacy_index.html"), d, v))


def build_404(d):
    root = "/"
    header, footer = chrome(d, root, "/index.html")
    v = {"head": head(d, root, "notfound.title", "notfound.text", SITE_URL, SITE_URL + "assets/brand/og-cover.jpg"),
         "header": header, "footer": footer}
    write("404.html", render(read(TPL / "404.html"), d, v))


# ── pages per language (search engines do not run the language switch) ─────
URL_ATTRS = ("href", "src", "poster", "data-anim", "data-full")
SKIP_PREFIX = ("http:", "https:", "//", "/", "#", "mailto:", "tel:", "data:", "blob:", "javascript:")


def localized_pages(apps):
    """Pages that get a copy per language: the home page and the app pages (policies stay one page — their text is
    the original legal text; their header and buttons still switch language in place)."""
    return ["index.html"] + [f"apps/{a['slug']}/index.html" for a in apps]


def page_url(page, lang=DEFAULT):
    path = page[:-len("index.html")] if page.endswith("index.html") else page
    return SITE_URL + ("" if lang == DEFAULT else lang + "/") + path


def alternates(page):
    lines = [f'  <link rel="alternate" hreflang="{l}" href="{page_url(page, l)}">' for l in LANGS]
    lines.append(f'  <link rel="alternate" hreflang="x-default" href="{page_url(page)}">')
    return "\n".join(lines) + "\n"


def add_alternates(page):
    """hreflang links in the default-language page (right after the canonical link)."""
    text = read(ROOT / page)
    text = re.sub(r'\n  <link rel="alternate" hreflang="[^"]+" href="[^"]*">', "", text)
    text = re.sub(r'(<link rel="canonical" href="[^"]*">\n)', lambda m: m.group(1) + alternates(page), text, count=1)
    write(page, text)


def relink(value, page, lang, local):
    """A relative link of `page` as seen from `<lang>/page`: links to pages that have a copy in this language stay
    inside the language folder, everything else (assets, policies, support) points to the one shared file."""
    if not value or value.startswith(SKIP_PREFIX):
        return value
    m = re.match(r"([^?#]*)(.*)", value)
    path, tail = m.group(1), m.group(2)
    if not path:
        return value
    base = posixpath.dirname(page)
    target = posixpath.normpath(posixpath.join(base, path))
    is_dir = path.endswith("/") or target == "."
    key = "index.html" if target == "." else (target.rstrip("/") + "/index.html" if is_dir else target)
    if key in local:
        target = posixpath.join(lang, target) if target != "." else lang
    new = posixpath.relpath(target, posixpath.join(lang, base) if base else lang)
    if is_dir and not new.endswith("/"):
        new += "/"
    return new + tail


def build_localized(dicts, apps):
    local = set(localized_pages(apps))
    for page in local:
        add_alternates(page)
        src = read(ROOT / page)
        for l in LANGS:
            if l == DEFAULT:
                continue
            d = dicts[l]
            soup = BeautifulSoup(src, "html.parser")
            for el in soup.select("[data-i18n]"):
                k = el["data-i18n"]
                if k in d:
                    el.string = d[k]
            for el in soup.select("[data-i18n-html]"):
                k = el["data-i18n-html"]
                if k in d:
                    el.clear()
                    el.append(BeautifulSoup(d[k], "html.parser"))
            for el in soup.select("[data-i18n-content]"):
                k = el["data-i18n-content"]
                if k in d:
                    el["content"] = d[k]
            for el in soup.find_all(True):
                for a in URL_ATTRS:
                    if el.has_attr(a):
                        el[a] = relink(el[a], page, l, local)
            for m_ in soup.find_all("meta", attrs={"name": "msapplication-config"}):
                m_["content"] = relink(m_["content"], page, l, local)
            h = soup.html
            h["lang"] = l
            h["data-root"] = posixpath.relpath(".", posixpath.join(l, posixpath.dirname(page))) + "/"
            h["data-page-lang"] = l
            title = soup.title.get_text()
            desc = soup.find("meta", attrs={"name": "description"})
            for prop, val in (("og:title", title), ("og:description", desc["content"] if desc else ""),
                              ("og:url", page_url(page, l))):
                m_ = soup.find("meta", attrs={"property": prop})
                if m_:
                    m_["content"] = val
            soup.find("link", attrs={"rel": "canonical"})["href"] = page_url(page, l)
            write(posixpath.join(l, page), str(soup))
    # the default-language pages also say which language they are (the switch does not swap them on load)
    for page in local:
        text = read(ROOT / page)
        if 'data-page-lang=' not in text:
            write(page, text.replace('<html lang="en" ', f'<html lang="en" data-page-lang="{DEFAULT}" ', 1))


def build_sitemap(apps):
    urls = [SITE_URL, SITE_URL + "privacy/"]
    for l in LANGS:
        if l != DEFAULT:
            urls += [page_url(p, l) for p in localized_pages(apps)]
    for a in apps:
        urls.append(SITE_URL + f"apps/{a['slug']}/")
        urls.append(SITE_URL + support_path(a))
        for kind in ("android", "ios"):
            if a["policy"].get(kind):
                urls.append(SITE_URL + policy_path(a, kind))
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")


def main():
    site, apps, chapters = load()
    print(f"[build] {len(apps)} apps, {len(chapters)} showreel chapters")
    dicts = build_langs(site, apps)
    d = dicts[DEFAULT]
    build_home(d, apps, chapters)
    for a in apps:
        build_app(d, a, apps)
    build_privacy_index(d, apps)
    build_404(d)
    build_localized(dicts, apps)
    build_sitemap(apps)
    print("[build] done")


if __name__ == "__main__":
    main()
