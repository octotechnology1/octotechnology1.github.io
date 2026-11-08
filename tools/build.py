"""Build the OctoTechnology site from content/ + tools/templates/.

    python tools/build.py

Generates:
  index.html, 404.html, privacy/index.html, sitemap.xml, robots.txt
  apps/<slug>/index.html, apps/<slug>/privacy-android.html, apps/<slug>/privacy-ios.html
  lang/en.json, lang/uk.json, lang/ru.json, lang/sk.json

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
import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

SITE_URL = "https://octotechnology1.github.io/"   # change here if the site moves (e.g. own domain)
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
PHONE_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="2" width="12" height="20" rx="3" fill="none" '
              'stroke="currentColor" stroke-width="2"/><circle cx="12" cy="18" r="1.3" fill="currentColor"/></svg>')


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
def status_chip(a):
    s = a["status"]
    return f'<span class="status status-{s}" data-i18n="status.{s}">{{{{status.{s}}}}}</span>'


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
    if not pol.get("android") and not pol.get("ios"):
        return (f'<div class="app-card-privacy"><span data-i18n="apps.privacy">{{{{apps.privacy}}}}</span>'
                f'<span class="muted-pill" data-i18n="privacy.soon">{{{{privacy.soon}}}}</span></div>')
    return (f'<div class="app-card-privacy"><span data-i18n="apps.privacy">{{{{apps.privacy}}}}</span>'
            f'<a href="{root}{policy_path(a, "android")}" data-i18n="apps.android">{{{{apps.android}}}}</a>'
            f'<a href="{root}{policy_path(a, "ios")}" data-i18n="apps.ios">{{{{apps.ios}}}}</a></div>')


def play_button(a, small=False):
    if a.get("play_live") and a.get("play"):
        return (f'<a class="store-btn" href="{esc(a["play"])}" target="_blank" rel="noopener">{GP_ICON}'
                f'<span><small>GET IT ON</small>Google Play</span></a>')
    return (f'<span class="store-btn off">{GP_ICON}<span><small>Google Play</small>'
            f'<span data-i18n="apps.play_soon">{{{{apps.play_soon}}}}</span></span></span>')


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
              <div class="app-card-actions"><a class="btn btn-violet btn-sm" href="{app_url(a, root)}" data-i18n="apps.more">{{{{apps.more}}}}</a>{extra}</div>
              {privacy_links_inline(a, root)}
            </div>
          </article>''')
    return "\n".join(out)


MARK_ROLES = [  # (image, text key prefix, app slug)
    ("apps/twomeows/media/mark.webp", "mark.r1", "twomeows"),
    ("assets/mark/mechanic.webp", "mark.r2", "marks-garage"),
    ("assets/mark/host_fly.svg", "mark.r3", "mark-the-cat"),
    ("assets/mark/artist_hello.svg", "mark.r4", "marks-art"),
    ("assets/mark/home_cheer.webp", "mark.r5", "marks-home"),
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
            <td data-th=""><a class="policy-app" href="{app_url(a, root)}" style="color:inherit;text-decoration:none"><img src="{root}apps/{a["slug"]}/media/icon.webp" alt="" width="40" height="40"><span data-i18n="{k}">{{{{{k}}}}}</span></a></td>
            <td data-th="Android">{policy_cell(a, "android", root)}</td>
            <td data-th="iOS">{policy_cell(a, "ios", root)}</td>
          </tr>''')
    return ('        <table class="policy-table">\n          <thead><tr><th data-i18n="privacy.app">{{privacy.app}}</th>'
            '<th data-i18n="privacy.android">{{privacy.android}}</th><th data-i18n="privacy.ios">{{privacy.ios}}</th></tr></thead>\n'
            '          <tbody>\n' + "\n".join(rows) + '\n          </tbody>\n        </table>')


def head(d, root, title_key, desc_key, canonical, og_image, theme="#a9d3e9", title_override=None, desc_override=None):
    tpl = read(TPL / "_head.html")
    return render(tpl, d, {
        "title_key": title_key, "desc_key": desc_key,
        "title": esc(title_override or d[title_key]), "desc": esc(desc_override or d[desc_key]),
        "canonical": canonical, "og_image": og_image, "theme_color": theme, "root": root, "ver": VER,
    })


def chrome(d, root, home):
    v = {"root": root, "home": home, "ver": VER}
    return render(read(TPL / "_header.html"), d, v), render(read(TPL / "_footer.html"), d, v)


# ── pages ──────────────────────────────────────────────────────────────────
def build_home(d, apps, chapters):
    root = ""
    header, footer = chrome(d, root, "")
    v = {
        "head": head(d, root, "meta.title", "meta.desc", SITE_URL, SITE_URL + "assets/brand/og-cover.jpg"),
        "header": header, "footer": footer,
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
    stores.append(f'<span class="store-btn off">{PHONE_ICON}<span><small>iPhone · iPad</small><span data-i18n="app.appstore_soon">{{{{app.appstore_soon}}}}</span></span></span>')

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

    others = "\n".join(
        f'          <a class="mini-app" href="../{o["slug"]}/index.html"><img src="../{o["slug"]}/media/icon.webp" alt="" width="52" height="52">'
        f'<div><b data-i18n="apps.{o["slug"]}.name">{{{{apps.{o["slug"]}.name}}}}</b><span data-i18n="apps.{o["slug"]}.meta">{{{{apps.{o["slug"]}.meta}}}}</span></div></a>'
        for o in apps if o["slug"] != slug)

    dev_note = ""
    if a["status"] == "dev" or not m["shots"]:
        dev_note = '        <p class="dev-note" data-i18n="app.dev_note">{{app.dev_note}}</p>'

    peek = a.get("peek", "host_wave")
    peek_file = next((p.name for p in (ROOT / "assets/mark").glob(peek + ".*")), "host_wave.svg")
    url = SITE_URL + f"apps/{slug}/"
    name, tagline = d[f"{k}.name"], d[f"{k}.tagline"]
    v = {
        "head": head(d, root, f"{k}.name", f"{k}.tagline", url, SITE_URL + f"apps/{slug}/media/icon-512.png",
                     th["b"], title_override=f"{name} — {tagline} · OctoTechnology"),
        "header": header, "footer": footer,
        "theme_style": f"--app-a:{th['a']};--app-b:{th['b']};--app-ink:{th['ink']}",
        "status_chip": status_chip(a), "age": esc(a["age"]), "store_buttons": "\n".join("            " + s for s in stores),
        "mark_file": m.get("mark") or "mark.webp", "features": "\n".join(feats),
        "shots_section": shots, "video_section": video, "policy_cards": "\n".join(cards), "others": others,
        "dev_note": dev_note, "peek_file": peek_file, "peek_flip": " flip" if a.get("peek_flip") else "",
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
            "head": head(d, root, "policy.title", f"{k}.name", purl, SITE_URL + f"apps/{slug}/media/icon-512.png", th["b"],
                         title_override=f"{name} — {d['policy.title']} ({'Android' if kind == 'android' else 'iOS'})",
                         desc_override=f"{name} — {d['policy.title']}"),
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


def build_sitemap(apps):
    urls = [SITE_URL, SITE_URL + "privacy/"]
    for a in apps:
        urls.append(SITE_URL + f"apps/{a['slug']}/")
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
    build_sitemap(apps)
    print("[build] done")


if __name__ == "__main__":
    main()
