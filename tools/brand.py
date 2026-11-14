"""Brand assets of OctoTechnology from the 3D logo kit (Blender).

    python tools/brand.py [--intro swim|dot]

Source: D:\\Octo_Technology_Dev\\07_OctoTechnology_Logo\\final   (render scripts and README live in that folder)
  final/brand-kit/icons/*      favicon.ico, favicon-16/32, apple-touch-icon-180, android-chrome-192/512, maskable-512, mstile, manifest
  final/brand-kit/logo/*       octopus-512.png (portrait, transparent)
  final/octo-hero.webp         hero octopus: ONE endless loop "hello" + calm swim (9.9 s). One file, no switching by
                               JS timers: the browser pauses off-screen animations and starts them late on reload, so
                               timer-driven swaps between two files landed mid-motion and the pose jumped.
  final/logo-anim-<intro>.webp animated logo, plays once (swim: swims through the O and hugs it; dot: hatches from a cyan dot)

Writes to assets/brand/:
  octo.webp           octopus portrait 512 px (header, footer, 404, reduced-motion hero)
  octo-hero.webp      hero octopus (endless loop)
  logo-intro.webp     animated logo (plays once, holds the last frame)
  logo.webp           last frame of the animation on the same canvas (shown before the animation and without JS)
  favicon.ico, favicon-16.png, favicon-32.png, apple-touch-icon-180.png, android-chrome-192.png, android-chrome-512.png,
  maskable-512.png, mstile-150.png, site.webmanifest, browserconfig.xml
og-cover.jpg is made separately: python tools/render_og.py
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "brand"
SRC = Path("D:/Octo_Technology_Dev/07_OctoTechnology_Logo/final")
KIT = SRC / "brand-kit"
ICONS = ["favicon.ico", "favicon-16.png", "favicon-32.png", "apple-touch-icon-180.png", "android-chrome-192.png",
         "android-chrome-512.png", "maskable-512.png", "mstile-150.png", "site.webmanifest", "browserconfig.xml"]
OLD = ["octo-anim.webp", "favicon.png", "apple-touch-icon.png", "octo-calm.webp", "octo-wave.webp"]


def need(p):
    if not p.exists():
        sys.exit(f"missing {p}: render the logo first (see 07_OctoTechnology_Logo/README.md, brand_kit.py)")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--intro", default="swim", choices=("swim", "dot"))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for n in ICONS:
        shutil.copy(need(KIT / "icons" / n), OUT / n)
    portrait = Image.open(need(KIT / "logo" / "octopus-512.png")).convert("RGBA")
    portrait.save(OUT / "octo.webp", "WEBP", quality=90, method=6)
    shutil.copy(need(SRC / "octo-hero.webp"), OUT / "octo-hero.webp")
    anim = need(SRC / f"logo-anim-{a.intro}.webp")
    shutil.copy(anim, OUT / "logo-intro.webp")
    im = Image.open(anim)
    im.seek(im.n_frames - 1)
    im.convert("RGBA").save(OUT / "logo.webp", "WEBP", quality=92, method=6)
    wave = Image.open(OUT / "octo-hero.webp")
    (ROOT / "content" / "brand.json").write_text(json.dumps(
        {"logo_w": im.width, "logo_h": im.height, "octo_w": wave.width, "octo_h": wave.height, "intro": a.intro}, indent=2),
        encoding="utf-8")
    for n in OLD:
        if (OUT / n).exists():
            (OUT / n).unlink()
    for p in sorted(OUT.iterdir()):
        print(f"  {p.relative_to(ROOT)}  {p.stat().st_size // 1024} KB")
    print(f"intro variant: {a.intro}")


if __name__ == "__main__":
    main()
