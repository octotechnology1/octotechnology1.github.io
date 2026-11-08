/* OctoTechnology — перемикач мов (EN / UK / RU / SK).
   Англійська вже в HTML; інші мови довантажуються з lang/*.json.
   Перший візит: мова береться з браузера, далі — з вибору користувача. */
(function () {
  "use strict";

  var STORAGE_KEY = "octo_lang";
  var DEFAULT_LANG = "en";
  var LANGS = ["en", "uk", "ru", "sk"];
  var HTML_LANG = { en: "en", uk: "uk", ru: "ru", sk: "sk" };
  var root = document.documentElement.getAttribute("data-root") || "";
  var cache = {};
  var current = DEFAULT_LANG;

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  function detect() {
    var saved = store(STORAGE_KEY);
    if (saved && LANGS.indexOf(saved) !== -1) return saved;
    var list = navigator.languages || [navigator.language || ""];
    for (var i = 0; i < list.length; i++) {
      var l = (list[i] || "").toLowerCase();
      if (l.indexOf("uk") === 0) return "uk";
      if (l.indexOf("ru") === 0 || l.indexOf("be") === 0) return "ru";
      if (l.indexOf("sk") === 0 || l.indexOf("cs") === 0) return "sk";
      if (l.indexOf("en") === 0) return "en";
    }
    return DEFAULT_LANG;
  }

  function load(lang) {
    if (cache[lang]) return Promise.resolve(cache[lang]);
    return fetch(root + "lang/" + lang + ".json").then(function (r) {
      if (!r.ok) throw new Error("lang " + lang);
      return r.json();
    }).then(function (d) { cache[lang] = d; return d; });
  }

  function apply(d) {
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var v = d[el.getAttribute("data-i18n")];
      if (v != null) el.textContent = v;
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      var v = d[el.getAttribute("data-i18n-html")];
      if (v != null) el.innerHTML = v;
    });
    document.querySelectorAll("[data-i18n-content]").forEach(function (el) {
      var v = d[el.getAttribute("data-i18n-content")];
      if (v != null) el.setAttribute("content", v);
    });
  }

  function setLang(lang, remember) {
    return load(lang).then(function (d) {
      apply(d);
      current = lang;
      document.documentElement.lang = HTML_LANG[lang] || lang;
      if (remember) store(STORAGE_KEY, lang);
      document.querySelectorAll(".lang-switch button").forEach(function (b) {
        b.classList.toggle("active", b.getAttribute("data-lang") === lang);
        b.setAttribute("aria-pressed", b.getAttribute("data-lang") === lang ? "true" : "false");
      });
      document.dispatchEvent(new CustomEvent("octo:lang", { detail: { lang: lang } }));
    }).catch(function (e) { console.error(e); });
  }

  window.octoI18n = {
    t: function (key) { var d = cache[current]; return (d && d[key]) || key; },
    lang: function () { return current; }
  };

  document.querySelectorAll(".lang-switch button").forEach(function (b) {
    b.addEventListener("click", function () { setLang(b.getAttribute("data-lang"), true); });
  });

  var start = detect();
  // англійський словник потрібен і для підказок у JS (кнопка «Скопійовано»)
  load(DEFAULT_LANG).then(function () { if (start !== DEFAULT_LANG) setLang(start, false); });
})();
