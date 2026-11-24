"""Mark the Cat images for the site (cats peeking from the sides, Mark tiles, 404, contact) in ONE look.

    python tools/peek_cats.py

Since 01.11.2026 (decision R25 in D:/Octo_Technology_Dev/01_Mark_Character/04_Art_Studio_artist/README.md) Mark has a dark
outline #22181A around the whole figure. Sources:
  * host (Mark the Cat app)  - D:/Marks_workshop/assets/images/mascot/poses/g/*.svg   (updated 01.11, outline built in;
    the copies in 01_Mark_Character/03_Workshop_BimiBoo_style are the OLD 18.10 version without the outline)
  * artist (Mark's Art)      - 01_Mark_Character/04_Art_Studio_artist/*.svg           (outline built in)
  * home (Mark's Home)       - D:/mark_game/art/mark/*.png                             (outline built in)
  * teacher (TwoMeows), mechanic/builder (Mark's Garage) are older art of those apps without the outline:
    the same dark outline is added here, so every cat on the site reads the same.
Every image is trimmed to the figure and scaled to the same height, so cats look the same size in their slots.
SVGs are rasterised with resvg from D:/Marks_art_studio/tools/assetgen (node).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "mark"
CHAR = Path("D:/Octo_Technology_Dev/01_Mark_Character")
SUITE = Path("D:/Spik_for_baby/suite")
WS = Path("D:/Marks_workshop/assets/images/mascot/poses/g")
RENDER = Path("D:/Marks_art_studio/tools/assetgen/preview_svg.mjs")
LINE = (0x22, 0x18, 0x1A)
HEIGHT = 520                       # высота всех картинок, px
OUTLINE = 0.0085                   # толщина добавляемого контура от высоты фигуры (как ~7 ед. на холсте 1024 у R25)

# key: (source, add outline?, destination relative to the site root)
CATS = {
    "teacher": (SUITE / "assets/cats/meows_hello.svg", True, "assets/mark/teacher.webp"),
    "teacher_heart": (SUITE / "assets/cats/meows_heart.svg", True, "assets/mark/teacher_heart.webp"),
    "mechanic": (CHAR / "02_Garage_mechanic_and_builder/png/cat_1.png", True, "assets/mark/mechanic.webp"),
    "builder": (CHAR / "02_Garage_mechanic_and_builder/png/cat_2.png", True, "assets/mark/builder.webp"),
    "host_wave": (WS / "mark_wave.svg", False, "assets/mark/host_wave.webp"),
    "host_point": (WS / "mark_point.svg", False, "assets/mark/host_point.webp"),
    "host_thumb": (WS / "mark_thumb.svg", False, "assets/mark/host_thumb.webp"),
    "host_cheer": (WS / "mark_cheer.svg", False, "assets/mark/host_cheer.webp"),
    "host_fly": (WS / "mark_fly.svg", False, "assets/mark/host_fly.webp"),
    "artist_hello": (CHAR / "04_Art_Studio_artist/mark_artist_hello.svg", False, "assets/mark/artist_hello.webp"),
    "artist_show": (CHAR / "04_Art_Studio_artist/mark_artist_show.svg", False, "assets/mark/artist_show.webp"),
    "artist_wow": (CHAR / "04_Art_Studio_artist/mark_artist_wow.svg", False, "assets/mark/artist_wow.webp"),
    "home_wave": (Path("D:/mark_game/art/mark/mark_wave.png"), False, "assets/mark/home_wave.webp"),
    "home_cheer": (Path("D:/mark_game/art/mark/mark_cheer.png"), False, "assets/mark/home_cheer.webp"),
    "trains_wave": (Path("D:/Marks_trains/art/mark/engineer_A_wave.png"), False, "assets/mark/trains_wave.webp"),
    "trains_cheer": (Path("D:/Marks_trains/art/mark/engineer_A_cheer.png"), False, "assets/mark/trains_cheer.webp"),
    # плитка «Марк в TwoMeows» в разделе про Марка
    "tile_twomeows": (CHAR / "01_TwoMeows_original_teacher/svg/png/mark_linguastory_cheer.png", True,
                      "apps/twomeows/media/mark.webp"),
}


def load(src, tmp):
    if src.suffix.lower() == ".svg":
        png = Path(tmp) / (src.stem + ".png")
        r = subprocess.run(["node", str(RENDER), str(src), str(png), "1600"], capture_output=True, text=True)
        if r.returncode or not png.exists():
            sys.exit("render failed for %s:\n%s" % (src, r.stderr[-1500:]))
        return Image.open(png).convert("RGBA")
    return Image.open(src).convert("RGBA")


def trim(im, pad=6):
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > 8)
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad + 1, im.width), min(ys.max() + pad + 1, im.height))
    return im.crop(box)


def add_outline(im):
    """Тёмный контур по краю фигуры (полупрозрачная тень на полу не обводится — порог альфы 0.5)."""
    a = np.asarray(im, np.float32) / 255.0
    solid = a[..., 3] > 0.5
    ys = np.nonzero(solid.any(axis=1))[0]
    w = max(2.0, OUTLINE * (ys.max() - ys.min()))
    pad = int(w) + 4
    big = np.zeros((a.shape[0] + 2 * pad, a.shape[1] + 2 * pad, 4), np.float32)
    big[pad:-pad, pad:-pad] = a
    soft = a[..., 3] > 0.08                           # у края картинки обрез бывает сглажен: там фигурой считаем и полупрозрачное
    for sl in (np.s_[:, :2], np.s_[:, -2:], np.s_[:2, :], np.s_[-2:, :]):
        solid[sl] |= soft[sl]
    solid = np.pad(solid, pad, mode="edge")           # фигура, обрезанная краем картинки (выглядывает), вдоль обреза без контура
    dist = ndimage.distance_transform_edt(~solid)
    ring = np.clip(w - dist + 0.5, 0, 1) * (~solid)
    src_a = big[..., 3:4]
    line = np.array(LINE, np.float32) / 255.0
    rgb = big[..., :3] * src_a + line * ring[..., None] * (1 - src_a)
    al = src_a + ring[..., None] * (1 - src_a)
    rgb = np.where(al > 1e-6, rgb / np.maximum(al, 1e-6), 0)
    out = np.concatenate([rgb, al], -1)
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for key, (src, outline, dst) in CATS.items():
            if not src.exists():
                sys.exit("missing source %s" % src)
            im = trim(load(src, tmp), pad=0 if outline else 6)   # без полей: обрез фигуры остаётся на краю, контур вдоль него не рисуется
            if outline:
                im = trim(add_outline(im))
            w = round(im.width * HEIGHT / im.height)
            im = im.resize((w, HEIGHT), Image.LANCZOS)
            out = ROOT / dst
            out.parent.mkdir(parents=True, exist_ok=True)
            im.save(out, "WEBP", quality=90, method=6)
            old = out.with_suffix(".svg")
            if old.exists():
                old.unlink()
            print("  %-34s %dx%d %s %d KB" % (dst, im.width, im.height, "+контур" if outline else "        ", out.stat().st_size // 1024))


if __name__ == "__main__":
    main()
