/* OctoTechnology — анімації та інтерактив */
(function () {
  "use strict";
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── Меню на вузьких екранах: кнопка відкриває панель з пунктами; закривається пунктом, Esc або дотиком поза нею ── */
  var siteHeader = document.querySelector(".site-header");
  var navBtn = siteHeader && siteHeader.querySelector(".nav-toggle");
  if (navBtn) {
    var setNav = function (open) {
      siteHeader.classList.toggle("nav-open", open);
      navBtn.setAttribute("aria-expanded", open ? "true" : "false");
    };
    navBtn.addEventListener("click", function () { setNav(!siteHeader.classList.contains("nav-open")); });
    siteHeader.querySelectorAll(".main-nav a").forEach(function (a) { a.addEventListener("click", function () { setNav(false); }); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setNav(false); });
    document.addEventListener("click", function (e) { if (!siteHeader.contains(e.target)) setNav(false); });
  }

  /* ── Поява секцій при прокрутці ── */
  if ("IntersectionObserver" in window) {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("shown"); revealObserver.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll(".reveal").forEach(function (el) { revealObserver.observe(el); });
    // запобіжник: якщо спостерігач запізнився, усе, що вже на екрані, показуємо одразу
    setTimeout(function () {
      document.querySelectorAll(".reveal:not(.shown)").forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) el.classList.add("shown");
      });
    }, 1200);
  } else {
    document.querySelectorAll(".reveal").forEach(function (el) { el.classList.add("shown"); });
  }

  /* ── Марк визирає з боків: секція data-cat-section="x" ↔ картинка data-cat="x" ── */
  var cats = document.querySelectorAll(".cat[data-cat]");
  var catSections = document.querySelectorAll("[data-cat-section]");
  if (cats.length && catSections.length) {
    var showCatFor = function () {
      var vh = window.innerHeight, center = vh / 2, best = null, bestDist = Infinity;
      catSections.forEach(function (sec) {
        var r = sec.getBoundingClientRect();
        if (r.bottom < vh * 0.2 || r.top > vh * 0.8) return;
        var dist = Math.abs(r.top + r.height / 2 - center);
        if (dist < bestDist) { bestDist = dist; best = sec; }
      });
      var active = best ? best.getAttribute("data-cat-section") : null;
      cats.forEach(function (c) { c.classList.toggle("visible", c.getAttribute("data-cat") === active); });
    };
    var lastRun = 0, trailing = null;
    var onScroll = function () {
      var now = Date.now();
      if (now - lastRun > 80) { lastRun = now; showCatFor(); }
      else if (!trailing) trailing = setTimeout(function () { trailing = null; lastRun = Date.now(); showCatFor(); }, 90);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    showCatFor();
  }

  /* ── 3D-орбіта: легкий нахил за курсором ── */
  var stage = document.querySelector(".orbit-stage");
  var tilt = stage && stage.querySelector(".orbit-tilt");
  if (stage && tilt && !reduced && window.matchMedia("(hover: hover)").matches) {
    var hero = document.querySelector(".hero") || stage;
    hero.addEventListener("pointermove", function (e) {
      var r = stage.getBoundingClientRect();
      var x = (e.clientX - (r.left + r.width / 2)) / r.width;
      var y = (e.clientY - (r.top + r.height / 2)) / r.height;
      tilt.style.transform = "rotateY(" + (x * 14).toFixed(2) + "deg) rotateX(" + (-y * 10).toFixed(2) + "deg)";
    });
    hero.addEventListener("pointerleave", function () { tilt.style.transform = ""; });
  }

  /* ── Восьминіг у центрі орбіти: один файл-петля («привіт» + плаває, 9,9 с), браузер крутить його сам.
        Раніше скрипт перемикав два файли за таймером, але браузер зупиняє анімацію поза екраном і запускає її
        із затримкою після оновлення — перемикання потрапляло на середину руху, і поза стрибала. Тепер перемикань немає.
        Без руху (prefers-reduced-motion) — статична поза. ── */
  var octo = document.getElementById("octo-hero");
  if (octo && reduced) octo.src = "assets/brand/octo.webp";

  /* ── Логотип у розділі «Студія»: анімація грає один раз, коли з'являється на екрані; без руху — статичний кадр ── */
  var studioLogo = document.getElementById("studio-logo");
  if (studioLogo && "IntersectionObserver" in window && !reduced) {
    studioLogo.setAttribute("data-wait", "");
    var logoStarted = false;
    var startLogo = function () {
      if (logoStarted) return;
      logoStarted = true;
      var pre = new Image();
      var go = function () { studioLogo.src = studioLogo.getAttribute("data-anim"); studioLogo.removeAttribute("data-wait"); };
      pre.onload = go;
      pre.onerror = function () { studioLogo.removeAttribute("data-wait"); };
      pre.src = studioLogo.getAttribute("data-anim");
    };
    new IntersectionObserver(function (entries, ob) {
      entries.forEach(function (e) { if (e.isIntersecting) { startLogo(); ob.disconnect(); } });
    }, { threshold: 0.5 }).observe(studioLogo);
    setTimeout(function () { if (!logoStarted) studioLogo.removeAttribute("data-wait"); }, 15000);   // запобіжник
  }

  /* ── Шоурил: розділи по застосунках, автозапуск коли видно ── */
  var reel = document.querySelector(".reel");
  if (reel) {
    var video = reel.querySelector("video");
    var label = reel.querySelector(".reel-label");
    var labelImg = label.querySelector("img");
    var labelTxt = label.querySelector("span");
    var playBtn = reel.querySelector(".reel-play");
    var chips = Array.prototype.slice.call(document.querySelectorAll(".reel-chip"));
    var chapters = [];
    try { chapters = JSON.parse(reel.getAttribute("data-chapters") || "[]"); } catch (e) { chapters = []; }
    var activeApp = null;

    var setActive = function (app) {
      if (app === activeApp) return;
      activeApp = app;
      chips.forEach(function (c) { c.classList.toggle("active", c.getAttribute("data-app") === app); });
      var chip = chips.filter(function (c) { return c.getAttribute("data-app") === app; })[0];
      if (chip) {
        labelImg.src = chip.querySelector("img").getAttribute("src");
        labelTxt.setAttribute("data-i18n", "apps." + app + ".name");
        labelTxt.textContent = chip.querySelector("span").textContent;
        label.style.opacity = 1;
      } else {
        label.style.opacity = 0;   /* привітання Марка й фінальна картка — без підпису застосунку */
      }
    };
    var onTime = function () {
      var t = video.currentTime, cur = chapters.length ? chapters[0].app : null;
      chapters.forEach(function (c) { if (t >= c.t) cur = c.app; });
      setActive(cur);
    };
    video.addEventListener("timeupdate", onTime);
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        video.currentTime = parseFloat(c.getAttribute("data-t")) || 0;
        video.play().catch(function () {});
        onTime();
      });
    });
    var syncBtn = function () { playBtn.textContent = video.paused ? "▶" : "❚❚"; };
    video.addEventListener("play", syncBtn);
    video.addEventListener("pause", syncBtn);
    playBtn.addEventListener("click", function () { if (video.paused) video.play().catch(function () {}); else video.pause(); });
    video.addEventListener("click", function () { if (video.paused) video.play().catch(function () {}); else video.pause(); });
    document.addEventListener("octo:lang", function () {
      var chip = chips.filter(function (c) { return c.getAttribute("data-app") === activeApp; })[0];
      if (chip) labelTxt.textContent = chip.querySelector("span").textContent;
    });
    if (chapters.length) setActive(chapters[0].app);
    /* Постер — кадр, где Марк уже машет. Первый показ начинаем с него же, иначе при старте Марк исчезает и
       выпрыгивает снова; со второго круга ролик идёт целиком с начала. */
    var posterT = chapters.length && chapters[0].poster ? +chapters[0].poster : 0;
    if (posterT) {
      var toPoster = function () { if (video.currentTime < 0.05) video.currentTime = posterT; };
      if (video.readyState >= 1) toPoster(); else video.addEventListener("loadedmetadata", toPoster, { once: true });
    }
    syncBtn();
    if ("IntersectionObserver" in window && !reduced) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) video.play().catch(function () {});
          else video.pause();
        });
      }, { threshold: 0.35 }).observe(reel);
    }
  }

  /* ── Галерея скриншотів + лайтбокс ── */
  var lb = document.querySelector(".lightbox");
  var shots = Array.prototype.slice.call(document.querySelectorAll(".gallery button[data-full]"));
  if (lb && shots.length) {
    var lbImg = lb.querySelector("img"), idx = 0, opener = null;
    var show = function (i) { idx = (i + shots.length) % shots.length; lbImg.src = shots[idx].getAttribute("data-full"); };
    var open = function (i) { opener = shots[i]; show(i); lb.classList.add("open"); lb.querySelector(".lb-close").focus(); };
    var close = function () { lb.classList.remove("open"); if (opener) opener.focus(); };
    shots.forEach(function (b, i) { b.addEventListener("click", function () { open(i); }); });
    lb.querySelector(".lb-close").addEventListener("click", close);
    lb.querySelector(".lb-prev").addEventListener("click", function () { show(idx - 1); });
    lb.querySelector(".lb-next").addEventListener("click", function () { show(idx + 1); });
    lb.addEventListener("click", function (e) { if (e.target === lb) close(); });
    document.addEventListener("keydown", function (e) {
      if (!lb.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(idx - 1);
      if (e.key === "ArrowRight") show(idx + 1);
    });
  }

  /* ── Копіювання посилань на політики ── */
  document.querySelectorAll(".copy-btn[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var url = btn.getAttribute("data-copy");
      var done = function () {
        var t = window.octoI18n ? window.octoI18n.t("privacy.copied") : "✓";
        btn.textContent = t; btn.classList.add("done");
        setTimeout(function () {
          btn.classList.remove("done");
          btn.textContent = window.octoI18n ? window.octoI18n.t("privacy.copy") : "Copy";
        }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () { window.prompt("", url); });
      else window.prompt("", url);
    });
  });

  /* ── Лічильники в «Про студію» ── */
  var counters = document.querySelectorAll(".stat b[data-count]");
  if (counters.length && "IntersectionObserver" in window && !reduced) {
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        co.unobserve(e.target);
        var el = e.target, end = parseInt(el.getAttribute("data-count"), 10), t0 = null;
        var step = function (ts) {
          if (!t0) t0 = ts;
          var p = Math.min(1, (ts - t0) / 1100);
          el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(step);
        };
        el.textContent = "0";
        requestAnimationFrame(step);
      });
    }, { threshold: 0.5 });
    counters.forEach(function (c) { co.observe(c); });
  }
})();
