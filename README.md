# OctoTechnology — сайт студії 🐙🐱

Сайт студії дитячих застосунків **OctoTechnology**: усі застосунки з котом Марком, відео,
сторінка кожного застосунку та політики конфіденційності для Android і iOS.
Стиль — як у сайту TwoMeows (небо, хмаринки, Марк визирає з боків), мови — EN / UK / RU / SK.

План хостингу: GitHub Pages, репозиторій `octotechnology1/octotechnology1.github.io` →
**https://octotechnology1.github.io/** (адреса задана в `tools/build.py`, константа `SITE_URL`).

## Стек

Статичний HTML + CSS + vanilla JS. Сторінки **генеруються** скриптом з даних — руками
`index.html`, `apps/*/index.html` і сторінки політик не редагувати (перезапишуться).

```
python tools/build.py              # зібрати сайт (потрібен beautifulsoup4)
python -m http.server 8090         # подивитися локально: http://localhost:8090/
```

## Структура

```
content/site/<lang>.json      тексти головної та спільні підписи (en, uk, ru, sk)
content/apps/<slug>.json      один файл на застосунок: статус, посилання, кольори, тексти 4 мовами
content/policies/*.html       ОРИГІНАЛИ політик (копії зі старих місць) — текст переноситься дослівно
content/showreel.json         розділи шоуріла (створює import_media.py)
apps/<slug>/media/            іконка, обкладинка, скриншоти, трейлер (створює import_media.py)
assets/brand/                 логотип-восьминіг (тимчасовий, до 3D-логотипа), og-cover.jpg
assets/mark/                  пози Марка, що визирає з боків
assets/video/showreel.mp4     ролик з усіх застосунків
tools/build.py                збирає сторінки й lang/*.json, перевіряє текст політик
tools/import_media.py         копіює й стискає медіа з папок проєктів на D:
tools/templates/              шаблони сторінок
tools/og-cover.html, render_og.py   прев'ю для месенджерів
```

Згенеровані файли: `index.html`, `404.html`, `privacy/index.html`, `apps/<slug>/index.html`,
`apps/<slug>/privacy-android.html`, `apps/<slug>/privacy-ios.html`, `lang/*.json`, `sitemap.xml`, `robots.txt`.

## Адреси політик (для Google Play і App Store)

| застосунок | Android | iOS |
|---|---|---|
| TwoMeows | `/apps/twomeows/privacy-android.html` | `/apps/twomeows/privacy-ios.html` |
| Гараж Марка | `/apps/marks-garage/privacy-android.html` | `/apps/marks-garage/privacy-ios.html` |
| Котик Марк | `/apps/mark-the-cat/privacy-android.html` | `/apps/mark-the-cat/privacy-ios.html` |
| Малювалка Марка | `/apps/marks-art/privacy-android.html` | `/apps/marks-art/privacy-ios.html` |
| Дім Марка | `/apps/marks-home/privacy-android.html` (заглушка) | `/apps/marks-home/privacy-ios.html` (заглушка) |

Повна адреса = `https://octotechnology1.github.io` + шлях. Після того як адреса потрапить у
магазин — **файли не перейменовувати**. Старі адреси на `twomeows.github.io` теж працюють, їх не чіпаємо.

### Оновити текст політики

1. Покласти новий HTML політики в `content/policies/<slug>-android.html` або `<slug>-ios.html`
   (можна прямо як раніше — повна сторінка з власним `<style>`; скрипт бере лише текст).
2. `python tools/build.py` — він перенесе текст у дизайн сайту і **перевірить**, що жодне слово
   не загубилось (інакше зупиниться з помилкою).

## Додати новий застосунок

1. `content/apps/<slug>.json` — скопіювати будь-який наявний файл і замінити: `slug`, `order`,
   `status` (`play` · `testing` · `soon` · `dev`), `play` + `play_live`, кольори `theme`,
   `age`, `peek` (поза Марка з `assets/mark/`), `policy` (імена файлів або `null`), `emoji` і тексти 4 мовами.
2. У `tools/import_media.py` додати запис у `APPS` (іконка, банер, обкладинка, скриншоти, відео, Марк)
   і, за бажанням, шматок у `SHOWREEL`.
3. `python tools/import_media.py --only <slug>` (без `--only` — переробить усе й шоурил).
4. Політики — у `content/policies/`, далі `python tools/build.py`.

Застосунок з'явиться на полиці, в орбіті, у картках, у таблиці політик і в «Інших застосунках».

### Коли застосунок вийде в Google Play

У його `content/apps/<slug>.json`: `"status": "play"`, `"play_live": true` → `python tools/build.py`.
Кнопка «Скоро в Google Play» стане справжньою кнопкою «Get it on Google Play».

## Тексти й мови

Ключі в `content/site/*.json` прив'язані до елементів через `data-i18n="ключ"`.
Англійська вбудована в HTML (для пошуковиків і без JS), інші мови підвантажуються з `lang/*.json`.
Мова першого візиту — з браузера; вибір користувача запам'ятовується.

## Деплой

```
git add -A && git commit -m "update site" && git push
```

GitHub Pages: гілка `main`, корінь. Пуш — від акаунта `octotechnology1`.
