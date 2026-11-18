# OctoTechnology — сайт студії 🐙

Сайт студії дитячих застосунків **OctoTechnology**: застосунки студії, відео, сторінка кожного застосунку
та політики конфіденційності для Android і iOS. Мови — EN / UK / RU / SK.

**Бренд-архітектура: студія → серії → застосунки.** Обличчя сайту — студія і її символ, восьминіг (шапка, hero,
«Про студію», «Батькам», підвал, 404, мета-теги). Кіт Марк — герой першої серії застосунків «Пригоди кота Марка»:
у нього своя секція `#mark` з підписом «Серія застосунків», він визирає з боків лише в секціях про його застосунки
(полиця, відео, картки), а на сторінках застосунків серії над назвою стоїть посилання на серію.
Загальні обіцянки й цифри — від імені студії, не одного героя. Наступні застосунки без кота не ламають сайт:
у їхньому JSON `"line"` не `"mark"` — тоді на сторінці немає ні кота, ні підпису серії.

План хостингу: GitHub Pages, репозиторій `octotechnology1/octotechnology1.github.io` →
**https://octotechnology1.github.io/** (адреса задана в `tools/build.py`, константа `SITE_URL`).

## Стек

Статичний HTML + CSS + vanilla JS. Сторінки **генеруються** скриптом з даних — руками
`index.html`, `apps/*/index.html` і сторінки політик не редагувати (перезапишуться).

```
python tools/build.py              # зібрати сайт (потрібен beautifulsoup4)
python .claude/serve.py 8090       # подивитися локально: http://localhost:8090/ (з Range — відео перемотується;
                                   # python -m http.server цього не вміє)
```

## Структура

```
content/site/<lang>.json      тексти головної та спільні підписи (en, uk, ru, sk)
content/apps/<slug>.json      один файл на застосунок: статус, посилання, кольори, тексти 4 мовами
content/policies/*.html       ОРИГІНАЛИ політик (копії зі старих місць) — текст переноситься дослівно
content/showreel.json         розділи шоуріла: intro, застосунки, outro (створює tools/build_reel.py)
apps/<slug>/media/            іконка, обкладинка, скриншоти, трейлер (створює import_media.py)
assets/brand/                 3D-логотип і восьминіг, фавіконки, маніфест, og-cover.jpg (з набору 07_OctoTechnology_Logo, `python tools/brand.py`)
assets/mark/                  пози Марка, що визирає з боків
assets/video/showreel.mp4     ролик з усіх застосунків (+ showreel.jpg — постер: Марк махає лапою)
tools/build.py                збирає сторінки й lang/*.json, перевіряє текст політик
tools/import_media.py         копіює й стискає медіа з папок проєктів на D:
tools/templates/              шаблони сторінок
tools/og-cover.html, render_og.py   прев'ю для месенджерів
tools/brand.py                копіює з набору логотипа (D:/Octo_Technology_Dev/07_OctoTechnology_Logo/final) іконки, восьминога і анімацію (--intro swim|dot)
tools/build_reel.py          шоуріл: Марк визирає й махає, усі застосунки в одній рамці телефона на небі сайту, «Powered by» в кінці
tools/render_svgs.mjs        растеризує SVG пачкою (кадри Марка для шоуріла; resvg з D:/Marks_art_studio/tools/assetgen)
tools/peek_cats.py            усі картинки Марка на сайті в одному вигляді: темний контур #22181A (рішення R25), однакова висота
```

Згенеровані файли: `index.html`, `404.html`, `privacy/index.html`, `apps/<slug>/index.html`,
`apps/<slug>/privacy-android.html`, `apps/<slug>/privacy-ios.html`, `lang/*.json`, `sitemap.xml`, `robots.txt`.

## Адреси для Google Play і App Store

| застосунок | Privacy (Android) | Privacy (iOS) | Support URL (App Store Connect) |
|---|---|---|---|
| TwoMeows | `/apps/twomeows/privacy-android.html` | `/apps/twomeows/privacy-ios.html` | `/apps/twomeows/support.html` |
| Гараж Марка | `/apps/marks-garage/privacy-android.html` | `/apps/marks-garage/privacy-ios.html` | `/apps/marks-garage/support.html` |
| Котик Марк | `/apps/mark-the-cat/privacy-android.html` | `/apps/mark-the-cat/privacy-ios.html` | `/apps/mark-the-cat/support.html` |
| Малювалка Марка | `/apps/marks-art/privacy-android.html` | `/apps/marks-art/privacy-ios.html` | `/apps/marks-art/support.html` |
| Дім Марка | `/apps/marks-home/privacy-android.html` | `/apps/marks-home/privacy-ios.html` | `/apps/marks-home/support.html` |

App Store Connect вимагає для кожного застосунку і Privacy Policy URL, і **Support URL** —
сторінка `support.html` (пошта з темою листа, керування підписками Apple/Google, повернення коштів, політики).
Marketing URL (необов'язковий) = сторінка застосунку `/apps/<slug>/`.

Повна адреса = `https://octotechnology1.github.io` + шлях. Після того як адреса потрапить у
магазин — **файли не перейменовувати**. Старі адреси на `twomeows.github.io` теж працюють, їх не чіпаємо.

### Оновити текст політики

1. Покласти новий HTML політики в `content/policies/<slug>-android.html` або `<slug>-ios.html`
   (можна прямо як раніше — повна сторінка з власним `<style>`; скрипт бере лише текст).
2. `python tools/build.py` — він перенесе текст у дизайн сайту і **перевірить**, що жодне слово
   не загубилось (інакше зупиниться з помилкою).

## Додати новий застосунок

1. `content/apps/<slug>.json` — скопіювати будь-який наявний файл і замінити: `slug`, `order`,
   `status` — Android (`play` · `testing` · `soon` · `dev`), `ios_status` — iOS (`live` · `testing` · `soon` · `dev`),
   `play` + `play_live`, `appstore` + `appstore_live` + `apple_id`, кольори `theme`,
   `line` — серія (`"mark"` = «Пригоди кота Марка»: кіт визирає і є посилання на серію; для застосунку без кота —
   інше значення, напр. `"studio"`), `age`, `peek` (поза Марка з `assets/mark/`, лише для серії `mark`),
   `policy` (імена файлів або `null`), `emoji` і тексти 4 мовами (`price` — показується і на картці на головній).
2. У `tools/import_media.py` додати запис у `APPS` (іконка, банер, обкладинка, скриншоти, відео, Марк)
   і, за бажанням, шматок у `SHOWREEL`.
3. `python tools/import_media.py --only <slug>` (без `--only` — переробить усе й шоурил).
4. Політики — у `content/policies/`, далі `python tools/build.py`.

Застосунок з'явиться на полиці, в орбіті, у картках, у таблиці політик і в «Інших застосунках».

### Коли застосунок вийде в Google Play

У його `content/apps/<slug>.json`: `"status": "play"`, `"play_live": true` → `python tools/build.py`.
Кнопка «Скоро в Google Play» стане справжньою кнопкою «Get it on Google Play».

### Коли застосунок вийде в App Store

`"ios_status": "live"`, `"appstore": "https://apps.apple.com/app/id<число>"`, `"appstore_live": true`,
`"apple_id": "<число>"` → `python tools/build.py`. З'явиться кнопка App Store, а на сторінці застосунку —
Smart App Banner (Safari на iPhone/iPad сам показує смужку «Відкрити / Завантажити»). Для TestFlight —
`"ios_status": "testing"`.

## Логотип

3D-логотип і восьминіг зроблені в Blender: `D:/Octo_Technology_Dev/07_OctoTechnology_Logo/` (там README, сцени та скрипти).
`python tools/brand.py [--intro swim|dot]` копіює звідти в `assets/brand/`: `octo.webp` (іконка шапки/підвалу), `octo-hero.webp`
(восьминіг у центрі орбіти: ОДНА нескінченна петля 9,9 с — вітається, потім плаває, і знову; без перемикання файлів
скриптом — браузер зупиняє анімацію поза екраном і запускає її із затримкою, тож перемикання за таймером давало ривки), `logo-intro.webp` (анімація логотипа, грає один раз у розділі «Студія»), `logo.webp`
(її останній кадр), фавіконки, `apple-touch-icon-180.png`, `android-chrome-*`, `maskable-512.png`, `site.webmanifest`.
Варіанти анімації: `swim` (підпливає крізь «O» і обіймає її) та `dot` (вилуплюється з бірюзової точки); обирається прапорцем.
`python tools/build_reel.py` збирає шоуріл (його також викликає `import_media.py`): кіт Марк (ведучий застосунку «Котик Марк»)
визирає знизу й махає лапою — логотипа на початку немає; далі кожен застосунок у тій самій рамці телефона на тому самому небі
(TwoMeows — у двох вертикальних телефонах); кліпи — «сирі» записи гри без промо-написів, тож ролик однаковий для всіх
чотирьох мов, а назву застосунку показує HTML-підпис над відео (перекладається сайтом); у кінці коротка картка
«Powered by OctoTechnology», яка тане в небо, тож повтор ролика без стику. Моменти кліпів задаються в `REEL` у скрипті.
У підвалі кожної сторінки — «© 2026 OctoTechnology» (сайт і є студія, тому без «Powered by»).
Прев'ю для месенджерів: `python tools/render_og.py`.

## Тексти й мови

**Окремі адреси для кожної мови (для пошуку).** Головна і сторінки застосунків мають копії з уже вписаним текстом:
`/uk/`, `/ru/`, `/sk/` і `/<мова>/apps/<slug>/` (англійська — у корені). Їх створює `tools/build.py` з англійських
сторінок: підставляє тексти з `lang/<мова>.json`, перераховує відносні шляхи (картинки, стилі, політики — спільні файли;
посилання на головну й інші застосунки лишаються в тій самій мовній папці), ставить `lang`, `canonical`, `og:url`
і посилання `hreflang` на всі мови (+ `x-default` = англійська). Усі адреси — у `sitemap.xml`.
Кнопки мов на цих сторінках ведуть на сторінку обраною мовою (вибір запам'ятовується); англійська сторінка одразу
відкриває збережену мову (або мову браузера при першому візиті). Політики й сторінки підтримки — одна адреса
(текст політики — оригінал), там мова, як і раніше, перемикається на місці.
Руками мовні папки не редагувати — їх перезаписує `build.py`.

Ключі в `content/site/*.json` прив'язані до елементів через `data-i18n="ключ"`.
Англійська вбудована в HTML (для пошуковиків і без JS), інші мови підвантажуються з `lang/*.json`.
Мова першого візиту — з браузера; вибір користувача запам'ятовується.

## Свій домен

`python tools/switch_domain.py <домен>` — пробний прогін: покаже, що зміниться (SITE_URL у `tools/build.py`, файл `CNAME`,
посилання на політику всередині ігор у `D:/Mark's_garage`, `D:/Marks_workshop`, `D:/Marks_art_studio`, `D:/mark_game`)
і які адреси вписати в Play Console / App Store Connect. З `--write` — записує. Далі `python tools/build.py`, push сайту,
у налаштуваннях Pages — домен і Enforce HTTPS; в іграх — нова збірка з versionCode +1. DNS: A-записи 185.199.108–111.153, `www` → CNAME `octotechnology1.github.io`.

## Деплой

```
git add -A && git commit -m "update site" && git push
```

GitHub Pages: гілка `main`, корінь. Пуш — від акаунта `octotechnology1`.
