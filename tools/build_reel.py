"""Showreel of the apps for the home page: one stage, one look, no burned-in text.

    python tools/build_reel.py

What the reel is (owner's notes of 2026-11-13: the cat is the hero, the company only signs at the end):
  1. Mark the Cat peeks up from the bottom edge, waves and ducks back (2.6 s). No logo at the start.
  2. Every app sits in the same device frame on the site's sky: TwoMeows (a portrait app) in two phones, the other apps
     in one landscape phone. Clips are the RAW gameplay recordings from the project folders, without promo captions,
     so one video serves all four site languages; the app name is the HTML label over the video (translated by the site).
  3. A short end card «Powered by OctoTechnology». It fades back to the empty sky and the clouds move on a loop,
     so the jump from the end to the start is invisible.
The sky never changes between parts, so the cuts feel like one film.

Writes assets/video/showreel.mp4, assets/video/showreel.jpg (poster: Mark waving) and content/showreel.json
(chapters: intro, the apps, outro). Then: python tools/build.py

Needs: ffmpeg/ffprobe in PATH, Pillow, numpy, node (for the SVG of Mark: tools/render_svgs.mjs).
Sources are only read: D:/Octo_Technology_Dev, D:/Mark's_garage, D:/Marks_workshop, D:/mark_game,
D:/Marks_art_studio (resvg), the logo D:/Octo_Technology_Dev/07_OctoTechnology_Logo/final/logo.png.
"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OCTO = Path("D:/Octo_Technology_Dev")
LOGO_DIR = OCTO / "07_OctoTechnology_Logo"
MARK_SVG = Path("D:/Marks_workshop/assets/images/mascot/poses/g/mark_wave.svg")
TW = OCTO / "04_TwoMeows_LinguaStory/video_raw_recordings"
GA = Path("D:/Mark's_garage/tools/promo/clips_raw/phone")
WS = Path("D:/Marks_workshop/tools/promo/clips_raw")
HOME = Path("D:/mark_game/art")

W, H, FPS = 1280, 720, 30
XF = 0.6          # cross-fade between parts, s
SHOT_XF = 0.35    # cross-fade between two shots of one app, s
INTRO, OUTRO = 2.6, 3.0
POSTER_T = 1.15   # постер = кадр, где Марк машет

TW_CROP = (107, 108, 865, 1758)   # TwoMeows phone recording: black side bars, status bar and gesture bar cut off

# (source, start s, length s); the moments are picked by eye from contact sheets of the recordings AND by smoothness:
# the emulator recordings are variable-frame-rate (7-17 fps on average, with gaps up to 0.3 s), so only windows where no
# frame is missing while something moves are used (checked from the packet timestamps: no gap > 75 ms during motion).
# Motion interpolation was tried and rejected: it smears Mark on fast moves.
REEL = [
    {"app": "twomeows", "kind": "phones", "dur": 4.2,   # короче: было 6,5 с почти без движения (замечание ревьюера)
     "phones": [(TW / "1.mp4", 0.8, TW_CROP),           # обложка дня меняется: Danylo -> Elara (лента обложек стоит)
                (TW / "5.mp4", 10.6, TW_CROP)]},        # карточка слова перелистывается: перо -> лес
    {"app": "marks-garage", "kind": "land",
     "shots": [(GA / "assembly_mixer.mp4", 3.4, 4.5),   # wheels, the drum flies in
               (GA / "dig_site.mp4", 2.2, 3.0)]},       # the excavator digs
    {"app": "mark-the-cat", "kind": "land",
     # все записи этого приложения — 8-15 к/с с эмулятора; сцены с прокруткой фона (ракета, лодка) дрожат, поэтому только
     # неподвижная камера, где редкие кадры почти незаметны. Лучшее решение — переснять на телефоне (как «Гараж»).
     "shots": [(WS / "train.mp4", 23.4, 3.2),           # котята в поезде (после белой вспышки игры)
               (WS / "bakery.mp4", 22.3, 3.3)]},        # пекарня: тесто, яйца, духовка
    {"app": "marks-art", "kind": "land",
     "shots": [(OCTO / "06_Mark_Art_Studio/mockups/alive_demo.mp4", 4.4, 7.4)]},   # colour fill, tick, Mark comes alive (30 fps)
    {"app": "marks-home", "kind": "land",
     "shots": [(HOME / "living/demo_living.mp4", 68.3, 2.6),    # домик, Марк машет (27 к/с, без пропусков)
               (HOME / "living/demo_living.mp4", 60.4, 4.6)]},  # Марк прилетает на шаре, конфетти (27 к/с; мытьё пола было 20 к/с)
]

SKY_TOP, SKY_MID, SKY_LOW = (169, 211, 233), (207, 227, 239), (221, 230, 236)
INK_SOFT = (82, 98, 122)
# x, y (share of the frame), width (share), sway amplitude px, phase
CLOUDS = [(0.87, 0.10, 0.17, 18, 0.0), (0.08, 0.91, 0.14, 14, 2.1), (0.62, 0.97, 0.10, 10, 4.0), (0.34, 0.05, 0.09, 12, 1.0)]


def log(*a):
    print(*a, flush=True)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_out_back(x, k=1.5):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"cannot read {p}:\n{r.stderr}")
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


# ── the stage ────────────────────────────────────────────────────────────────
def sky_base():
    t = np.linspace(0, 1, H)[:, None]
    top, mid, low = (np.array(c, float) for c in (SKY_TOP, SKY_MID, SKY_LOW))
    col = np.where(t < 0.45, top + (mid - top) * (t / 0.45), mid + (low - mid) * ((t - 0.45) / 0.55))
    return Image.fromarray(np.repeat(col[:, None, :], W, axis=1).round().astype(np.uint8), "RGB")


def cloud(k):
    """Soft cloud as on the site; k = width in px."""
    pad = 14
    w, h = int(k * 0.95) + 2 * pad, int(k * 0.5) + 2 * pad
    im = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    cx, cy = w / 2, pad + 0.31 * k
    for dx, dy, r in ((-0.30, 0.02, 0.15), (-0.12, -0.08, 0.22), (0.12, -0.05, 0.19), (0.31, 0.03, 0.14)):
        d.ellipse((cx + (dx - r) * k, cy + (dy - r) * k, cx + (dx + r) * k, cy + (dy + r) * k), fill=(255, 255, 255, 150))
    d.rounded_rectangle((cx - 0.40 * k, cy - 0.02 * k, cx + 0.43 * k, cy + 0.14 * k), radius=0.07 * k, fill=(255, 255, 255, 150))
    return im.filter(ImageFilter.GaussianBlur(5))


class Sky:
    def __init__(self, period):
        self.base = sky_base()
        self.period = period
        self.clouds = [(cloud(k * W), x * W, y * H, amp, ph) for x, y, k, amp, ph in CLOUDS]

    def at(self, t):
        im = self.base.copy()
        for c, x, y, amp, ph in self.clouds:
            cx = x + amp * math.sin(2 * math.pi * t / self.period + ph)   # periodic: the loop has no seam
            im.paste(c, (round(cx - c.width / 2), round(y - c.height / 2)), c)
        return im


def rounded_mask(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


class Device:
    """A phone without brand details: dark body, thin light rim, soft shadow; the screen gets the clip."""

    def __init__(self, sw, sh, bezel, r_out):
        self.size = (sw, sh)
        dw, dh = sw + 2 * bezel, sh + 2 * bezel
        p = 46
        spr = Image.new("RGBA", (dw + 2 * p, dh + 2 * p), (0, 0, 0, 0))
        shadow = Image.new("L", spr.size, 0)
        shadow.paste(rounded_mask(dw, dh, r_out), (p, p + 16))
        shadow = shadow.filter(ImageFilter.GaussianBlur(17)).point(lambda v: int(v * 0.32))
        sh_layer = Image.new("RGBA", spr.size, (30, 42, 60, 0))
        sh_layer.putalpha(shadow)
        spr.alpha_composite(sh_layer)
        body = Image.new("RGBA", (dw, dh), (34, 38, 50, 255))
        body.putalpha(rounded_mask(dw, dh, r_out))
        spr.alpha_composite(body, (p, p))
        ss = 4
        rim = Image.new("L", (dw * ss, dh * ss), 0)
        ImageDraw.Draw(rim).rounded_rectangle((ss, ss, dw * ss - 1 - ss, dh * ss - 1 - ss), radius=(r_out - 1) * ss,
                                              outline=255, width=2 * ss)
        rim_layer = Image.new("RGBA", (dw, dh), (120, 130, 152, 0))
        rim_layer.putalpha(rim.resize((dw, dh), Image.LANCZOS).point(lambda v: int(v * 0.85)))
        spr.alpha_composite(rim_layer, (p, p))
        self.sprite = spr
        self.mask = rounded_mask(sw, sh, r_out - bezel + 2)
        self.screen_at = (p + bezel, p + bezel)

    def draw(self, img, screen, cx, cy, scale=1.0, alpha=1.0):
        s = self.sprite.copy()
        s.paste(screen, self.screen_at, self.mask)
        if abs(scale - 1) > 1e-3:
            s = s.resize((round(s.width * scale), round(s.height * scale)), Image.BICUBIC)
        a = s.getchannel("A")
        if alpha < 0.999:
            a = a.point(lambda v: int(v * alpha))
        img.paste(s, (round(cx - s.width / 2), round(cy - s.height / 2)), a)


LAND = Device(1088, 504, 14, 44)           # 2.16:1 like the landscape apps (they are cover-cropped by 1-3 %)
PHONE = Device(276, 561, 12, 40)           # TwoMeows recording after the crop: 865 x 1758
LAND_C = (640, 352)
PHONE_C = [(640 - 168, 352 - 12), (640 + 168, 352 + 12)]


class Shot:
    """Frames of one clip, cropped to the screen's shape and scaled; read from ffmpeg as they are needed."""

    def __init__(self, src, start, dur, size, crop=None):
        self.src, self.start, self.dur, self.size, self.crop = Path(src), start, dur, size, crop
        self.proc, self.n, self.last, self.ended = None, -1, None, False

    def _open(self):
        if not self.src.exists():
            sys.exit(f"missing clip: {self.src}")
        sw, sh = self.size
        if self.crop:
            x, y, w, h = self.crop
        else:
            iw, ih = probe(self.src)
            a = sw / sh
            w, h = (round(ih * a), ih) if iw / ih > a else (iw, round(iw / a))
            x, y = (iw - w) // 2, (ih - h) // 2
        vf = f"fps={FPS},crop={w}:{h}:{x}:{y},scale={sw}:{sh}:flags=lanczos"
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{self.start:.3f}", "-i", str(self.src),
                                      "-t", f"{self.dur + 0.5:.3f}", "-vf", vf, "-an", "-f", "rawvideo",
                                      "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def frame(self, i):
        if self.proc is None:
            self._open()
        nb = self.size[0] * self.size[1] * 3
        while self.n < i and not self.ended:
            buf = self.proc.stdout.read(nb)
            if len(buf) < nb:          # the clip ended early: hold its last frame
                self.ended = True
                break
            self.last = Image.frombytes("RGB", self.size, buf)
            self.n += 1
        if self.last is None:
            sys.exit(f"no frames from {self.src} at {self.start}s")
        return self.last

    def close(self):
        if self.proc:
            self.proc.kill()          # kill first: closing the pipe under a running ffmpeg makes it complain
            self.proc.wait()
            self.proc.stdout.close()
            self.proc = None


# ── parts ────────────────────────────────────────────────────────────────────
class Part:
    kind, app, enter = "", "", False

    def close(self):
        pass


class Phones(Part):
    kind = "phones"

    def __init__(self, spec):
        self.app, self.dur = spec["app"], spec["dur"]
        self.shots = [Shot(src, start, self.dur, PHONE.size, crop) for src, start, crop in spec["phones"]]

    def draw(self, img, tl):
        f = round(tl * FPS)
        for k, (shot, (cx, cy)) in enumerate(zip(self.shots, PHONE_C)):
            u = ease_out((tl - XF / 2 - 0.08 * k) / XF) if self.enter else 1.0   # появляется во второй половине перехода
            PHONE.draw(img, shot.frame(f), cx, cy + 18 * (1 - u), 0.94 + 0.06 * u)

    def close(self):
        for s in self.shots:
            s.close()


class Landscape(Part):
    kind = "land"

    def __init__(self, spec):
        self.app = spec["app"]
        self.shots = [Shot(src, start, dur, LAND.size) for src, start, dur in spec["shots"]]
        self.starts, t = [], 0.0
        for s in self.shots:
            self.starts.append(t)
            t += s.dur - SHOT_XF
        self.dur = t + SHOT_XF

    def screen(self, tl):
        k = max(i for i, t0 in enumerate(self.starts) if tl >= t0 - 1e-9) if tl > 0 else 0
        cur = self.shots[k].frame(round((tl - self.starts[k]) * FPS))
        if k > 0 and tl < self.starts[k] + SHOT_XF:
            prev = self.shots[k - 1].frame(round((tl - self.starts[k - 1]) * FPS))
            cur = Image.blend(prev, cur, smooth((tl - self.starts[k]) / SHOT_XF))
        for j in range(k - 1):        # shots that are over: stop their ffmpeg
            self.shots[j].close()
        return cur

    def draw(self, img, tl):
        u = ease_out((tl - XF / 2) / XF) if self.enter else 1.0
        LAND.draw(img, self.screen(tl), LAND_C[0], LAND_C[1] + 18 * (1 - u), 0.94 + 0.06 * u)

    def close(self):
        for s in self.shots:
            s.close()


def wave_angle(t):
    """Waving arm (degrees around the shoulder): +20 outwards, -6 towards the head."""
    env = smooth((t - 0.25) / 0.3) * (1 - smooth((t - 1.5) / 0.3))
    return env * (7 + 13 * math.sin(2 * math.pi * 1.7 * (t - 0.25)))


class Intro(Part):
    """Mark (the Mark the Cat app host, pose G with the R25 outline) peeks up from the bottom, waves, ducks back."""
    kind, app = "intro", "intro"
    MARK_W, TOP = 720, 118

    def __init__(self, tmp):
        self.dur = INTRO
        src = MARK_SVG.read_text(encoding="utf-8")
        try:
            a0 = src.index('<path d="M664,606 Q756,500 800,418"')    # the raised arm starts here ...
            a1 = src.index('<g transform="translate(0 606)">')       # ... and ends before the bow tie
        except ValueError:
            sys.exit(f"{MARK_SVG}: the arm is no longer where build_reel.py expects it, update the anchors")
        n = round(self.dur * FPS) + 1
        self.angles = [round(wave_angle(f / FPS) * 4) / 4 for f in range(n)]
        jobs, files = [], {}
        for a in sorted(set(self.angles)):
            svg, png = Path(tmp) / f"mark_{a:+.2f}.svg", Path(tmp) / f"mark_{a:+.2f}.png"
            svg.write_text(src[:a0] + f'<g transform="rotate({a} 664 606)">' + src[a0:a1] + "</g>" + src[a1:],
                           encoding="utf-8")
            jobs.append([str(svg), str(png), self.MARK_W])
            files[a] = png
        jf = Path(tmp) / "jobs.json"
        jf.write_text(json.dumps(jobs), encoding="utf-8")
        r = subprocess.run(["node", str(ROOT / "tools" / "render_svgs.mjs"), str(jf)], capture_output=True, text=True)
        if r.returncode:
            sys.exit("Mark render failed:\n" + r.stderr[-1500:])
        self.img = {a: Image.open(p).convert("RGBA") for a, p in files.items()}
        self.bbox = self.img[self.angles[0]].getbbox()
        log(f"  Mark: {len(files)} poses of the waving arm")

    def draw(self, img, tl):
        f = min(round(tl * FPS), len(self.angles) - 1)
        m = self.img[self.angles[f]]
        rise = ease_out_back(tl / 0.55)
        d = min(max((tl - 1.6) / 0.5, 0.0), 1.0)
        duck = 2.2 * d ** 3 - 1.2 * d ** 2          # a tiny lift, then down and away before the phones come in
        dy = 640 * (1 - rise) + 640 * duck
        env = smooth((tl - 0.25) / 0.3) * (1 - smooth((tl - 1.5) / 0.3))
        tilt = 1.3 * env * math.sin(2 * math.pi * 1.7 * (tl - 0.25) + 0.6)     # the body follows the paw a little
        if abs(tilt) > 0.02:
            m = m.rotate(tilt, resample=Image.BICUBIC, center=(m.width / 2, self.bbox[3]))
        img.paste(m, (W // 2 - m.width // 2, round(self.TOP - self.bbox[1] + dy)), m)


class Outro(Part):
    """«Powered by» above the static logo; the logo settles, everything fades back to the sky for the loop."""
    kind, app = "outro", "outro"

    def __init__(self):
        self.dur = OUTRO
        logo = Image.open(LOGO_DIR / "final" / "logo.png").convert("RGBA")
        logo = logo.crop(logo.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
        self.lh = 300
        self.logo = logo.resize((round(logo.width * self.lh / logo.height), self.lh), Image.LANCZOS)
        font = ImageFont.truetype(str(LOGO_DIR / "fonts" / "Nunito-Variable.ttf"), 38)
        font.set_variation_by_axes([800])
        self.txt = Image.new("RGBA", (W, 80), (0, 0, 0, 0))
        ImageDraw.Draw(self.txt).text((W // 2, 40), "Powered by", font=font, fill=INK_SOFT + (255,), anchor="mm")

    def draw(self, img, tl):
        fade = 1 - smooth((tl - (self.dur - 0.6)) / 0.48)     # gone ~4 frames before the end: the loop starts on pure sky
        s = 0.94 + 0.06 * ease_out(tl / 0.9)
        lg = self.logo.resize((round(self.logo.width * s), round(self.logo.height * s)), Image.LANCZOS)
        cy = 420
        img.paste(lg, (W // 2 - lg.width // 2, cy - lg.height // 2), lg.getchannel("A").point(lambda v: int(v * fade)))
        al = ease_out((tl - 0.15) / 0.5) * fade
        img.paste(self.txt, (0, round(cy - self.lh / 2 - 78 + 10 * (1 - al))),
                  self.txt.getchannel("A").point(lambda v: int(v * al)))


# ── the film ─────────────────────────────────────────────────────────────────
def main(argv=None):
    out = ROOT / "assets" / "video" / "showreel.mp4"
    poster = out.with_suffix(".jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        parts = [Intro(tmp)] + [Phones(s) if s["kind"] == "phones" else Landscape(s) for s in REEL] + [Outro()]
        for prev, p in zip(parts, parts[1:]):
            p.enter = prev.kind != p.kind     # a new kind of frame comes in with a small rise; same frame: content cross-fade
        starts, t = [], 0.0
        for p in parts:
            starts.append(t)
            t += p.dur - XF
        total = starts[-1] + parts[-1].dur
        n = round(total * FPS)
        sky = Sky(total)
        log(f"[showreel] {total:.1f}s, {n} frames")
        keys = ",".join(f"{s + XF / 2:.2f}" for s in starts[1:])     # опорные кадры на главах: кнопки приложений
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",  # перематывают сразу
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "26",
                                "-tune", "animation", "-g", str(2 * FPS), "-force_key_frames", keys,
                                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(out)],
                               stdin=subprocess.PIPE)
        done = set()
        for f in range(n):
            t = f / FPS
            bg = sky.at(t)
            frames = []
            for i, p in enumerate(parts):
                if starts[i] - 1e-9 <= t < starts[i] + p.dur:
                    im = bg.copy()
                    p.draw(im, t - starts[i])
                    frames.append((i, im))
                elif t >= starts[i] + p.dur and i not in done:
                    p.close()
                    done.add(i)
            if not frames:
                frame = bg
            elif len(frames) == 1:
                frame = frames[0][1]
            else:
                (_, a), (j, b) = frames[0], frames[-1]
                u = (t - starts[j]) / XF
                if parts[j].enter:
                    # разные рамки (2 вертикальных телефона -> горизонтальный, телефон -> логотип): не наплыв, а через
                    # небо — сначала уходит старое, потом приходит новое, без двойных контуров
                    frame = Image.blend(bg, a, 1 - smooth(u * 2)) if u < 0.5 else Image.blend(bg, b, smooth(u * 2 - 1))
                else:
                    frame = Image.blend(a, b, smooth(u))      # та же рамка: меняется только картинка на экране
            if f == round(POSTER_T * FPS):
                frame.save(poster, quality=86)
            enc.stdin.write(frame.tobytes())
            if f % 150 == 0:
                log(f"  {t:5.1f}s")
        enc.stdin.close()
        if enc.wait():
            sys.exit("ffmpeg encoder failed")
        for p in parts:
            p.close()
    chapters = [{"app": p.app, "t": 0.0 if i == 0 else round(starts[i] + XF / 2, 2)} for i, p in enumerate(parts)]
    chapters[0]["poster"] = POSTER_T    # js/main.js начинает первый показ с этого кадра: постер -> видео без скачка
    (ROOT / "content" / "showreel.json").write_text(json.dumps(chapters, indent=2), encoding="utf-8")
    log(f"  {out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB, poster {poster.stat().st_size // 1024} KB")
    log(f"  chapters: {chapters}")


if __name__ == "__main__":
    main(sys.argv[1:])
