"""Перенос сайта на свой домен одной командой.

    python tools/switch_domain.py octotechnology.com          # показать, что поменяется (ничего не пишет)
    python tools/switch_domain.py octotechnology.com --write  # записать

Что делает:
  1. tools/build.py: SITE_URL = https://<домен>  (canonical, hreflang, sitemap, адреса политик на страницах)
  2. CNAME в корне сайта — GitHub Pages по нему отдаёт сайт на домене
  3. ссылки на политику конфиденциальности ВНУТРИ игр (текущая ветка каждого репозитория) — на страницы этого сайта
  4. печатает, какие поля в Play Console / App Store Connect поменять руками

Потом: python tools/build.py, коммит и push сайта; в играх — коммит, новая сборка (versionCode +1) и загрузка в Play.
DNS у регистратора: для корня домена — A-записи 185.199.108.153 / .109.153 / .110.153 / .111.153,
для www — CNAME octotechnology1.github.io. В настройках Pages репозитория указать домен и включить Enforce HTTPS.
Старые адреса octotechnology1.github.io GitHub сам перенаправит на домен.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (репозиторий, файл, страница политики на сайте) — ссылка, которую игра открывает из раздела для родителей
APP_LINKS = [
    ("D:/Mark's_garage", "composeApp/src/commonMain/kotlin/com/marksgarage/app/game/ProfileDialog.kt", "apps/marks-garage/privacy-android.html"),
    ("D:/Marks_workshop", "composeApp/src/commonMain/kotlin/com/markthecat/games/ShellCore.kt", "apps/mark-the-cat/privacy-android.html"),
    ("D:/Marks_art_studio", "composeApp/src/androidMain/kotlin/com/markthecat/coloring/BillingShop.kt", "apps/marks-art/privacy-android.html"),
    ("D:/Marks_art_studio", "iosApp/iosApp/StoreKitShop.swift", "apps/marks-art/privacy-ios.html"),
    ("D:/mark_game", "composeApp/src/androidMain/kotlin/com/markthecat/home/BillingShop.kt", "apps/marks-home/privacy-android.html"),
    ("D:/Marks_trains", "composeApp/src/androidMain/kotlin/com/markthecat/trains/BillingShop.kt", "apps/marks-trains/privacy-android.html"),
]
# любая прежняя ссылка на политику: старый сайт twomeows.github.io/<игра>/privacy*.html или этот сайт до домена
OLD_POLICY = re.compile(r'https://(?:twomeows\.github\.io/[a-z]+|octotechnology1\.github\.io/apps/[a-z-]+)/privacy[a-z-]*\.html')

STORE_FIELDS = [
    ("Mark's Garage", "marks-garage"), ("Mark the Cat", "mark-the-cat"), ("Mark's Art", "marks-art"),
    ("Mark's Home", "marks-home"), ("Mark's Trains", "marks-trains"), ("TwoMeows / LinguaStory", "twomeows"),
]


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    domain = argv[0].strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
    if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", domain):
        sys.exit(f"не похоже на домен: {domain}")
    write = "--write" in argv
    site = f"https://{domain}"
    changes = []

    build = ROOT / "tools" / "build.py"
    s = build.read_text(encoding="utf-8")
    # со слешем в конце, как было: build.py дописывает пути без ведущего слеша (SITE_URL + "apps/...")
    s2, n = re.subn(r'^SITE_URL = "[^"]*"', f'SITE_URL = "{site}/"', s, count=1, flags=re.M)
    if n != 1:
        sys.exit("SITE_URL не найден в tools/build.py")
    changes.append((build, s, s2))
    cname = ROOT / "CNAME"
    changes.append((cname, cname.read_text(encoding="utf-8") if cname.exists() else "", domain + "\n"))

    for repo, rel, page in APP_LINKS:
        f = Path(repo) / rel
        if not f.exists():
            print(f"  ! нет файла {f}")
            continue
        s = f.read_text(encoding="utf-8")
        s2, n = OLD_POLICY.subn(f"{site}/{page}", s)
        if n == 0 and f"{site}/{page}" not in s:
            print(f"  ! в {f} не найдена ссылка на политику — проверить руками")
        changes.append((f, s, s2))

    for f, old, new in changes:
        if old == new:
            print(f"  = {f}")
            continue
        print(f"  ~ {f}")
        for a, b in zip(old.splitlines(), new.splitlines()):
            if a != b:
                print(f"      - {a.strip()}\n      + {b.strip()}")
        if f.name == "CNAME" and not old:
            print(f"      + {domain}")
        if write:
            f.write_text(new, encoding="utf-8", newline="")

    print("\nPlay Console → Контент приложения → Политика конфиденциальности (и App Store Connect → Privacy Policy URL):")
    for name, slug in STORE_FIELDS:
        print(f"  {name:24} Android {site}/apps/{slug}/privacy-android.html")
        print(f"  {'':24} iOS     {site}/apps/{slug}/privacy-ios.html   Support {site}/apps/{slug}/support.html")
    print(f"  TwoMeows: адрес удаления аккаунта (Безопасность данных) → {site}/apps/twomeows/privacy-android.html#delete")
    print("\nВетки ios-port (Mac) этим скриптом не меняются: там ссылки поправить на Mac так же.")
    if not write:
        print("\nЭто пробный прогон. Записать: добавить --write")


if __name__ == "__main__":
    main(sys.argv[1:])
