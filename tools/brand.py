"""Brand assets of OctoTechnology from the octopus logo sources.

    python tools/brand.py

Sources (found 2026-11-08):
  E:\\рабочий стол\\octo\\octo.png                       — static octopus 2304x1792 (+ parts: head, eyes, tentacles)
  D:\\botCryptoAlonnn_MT5ERROR\\app\\assets\\logo.webp   — animated octopus with transparent background (loading screen)

Writes to assets/brand/:
  octo.webp           static logo, square, transparent (header, footer, 404)
  octo-anim.webp      animated logo for the hero (lighter re-encode of the loading animation)
  favicon.png         64x64
  apple-touch-icon.png 180x180 on the sky colour (iOS fills transparency with black)
When the 3D (Blender) version is ready, point STATIC/ANIM to its renders and run again.
"""
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "brand"
STATIC = Path("E:/рабочий стол/octo/octo.png")
ANIM = Path("D:/botCryptoAlonnn_MT5ERROR/app/assets/logo.webp")
SKY_TOP, SKY_LOW = (169, 211, 233), (221, 230, 236)


def square(im, pad=0.08):
    im = im.crop(im.getbbox())
    w, h = im.size
    s = int(max(w, h) * (1 + 2 * pad))
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out.alpha_composite(im, ((s - w) // 2, (s - h) // 2))
    return out


def sky(size):
    bg = Image.new("RGBA", (size, size))
    for y in range(size):
        t = y / (size - 1)
        c = tuple(int(SKY_TOP[i] + (SKY_LOW[i] - SKY_TOP[i]) * t) for i in range(3)) + (255,)
        bg.paste(c, (0, y, size, y + 1))
    return bg


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    logo = square(Image.open(STATIC).convert("RGBA"))
    logo.resize((512, 512), Image.LANCZOS).save(OUT / "octo.webp", "WEBP", quality=88, method=6)
    logo.resize((64, 64), Image.LANCZOS).save(OUT / "favicon.png", optimize=True)
    icon = sky(180)
    icon.alpha_composite(square(Image.open(STATIC).convert("RGBA"), pad=0.12).resize((180, 180), Image.LANCZOS))
    icon.convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)

    # animated: crop to the union of all frames, scale, keep every 2nd frame (twice the duration)
    src = Image.open(ANIM)
    frames, durs = [], []
    for i, f in enumerate(ImageSequence.Iterator(src)):
        frames.append(f.convert("RGBA"))
        durs.append(f.info.get("duration", 40) or 40)
    box = None
    for f in frames:
        b = f.getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    keep = list(range(0, len(frames), 2))
    out_frames, out_durs = [], []
    for i in keep:
        f = frames[i].crop(box)
        f.thumbnail((360, 360), Image.LANCZOS)
        out_frames.append(f)
        out_durs.append(sum(durs[i:i + 2]))
    out_frames[0].save(OUT / "octo-anim.webp", "WEBP", save_all=True, append_images=out_frames[1:], duration=out_durs,
                       loop=0, quality=72, method=3, lossless=False, minimize_size=False)
    for n in ("octo.webp", "octo-anim.webp", "favicon.png", "apple-touch-icon.png"):
        p = OUT / n
        print(f"  {p.relative_to(ROOT)}  {p.stat().st_size // 1024} KB")
    print(f"  animation: {len(out_frames)} frames, {sum(out_durs) / 1000:.1f}s, size {out_frames[0].size}")


if __name__ == "__main__":
    main()
