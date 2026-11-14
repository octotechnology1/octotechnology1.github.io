"""Copy and convert app media from the project folders on D: into the site.

Run from the site root:  python tools/import_media.py [--only slug,slug] [--skip-video]

Sources stay where they are (D:\\Octo_Technology_Dev, D:\\Marks_art_studio, D:\\mark_game, ...);
this script only writes web-sized copies into apps/<slug>/media/ and assets/.
Re-run it after new screenshots or videos appear, then run tools/build.py.

Needs: Pillow, ffmpeg in PATH.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OCTO = Path("D:/Octo_Technology_Dev")
SUITE = Path("D:/Spik_for_baby/suite")
CHAR = OCTO / "01_Mark_Character"

# ── what to import for every app ────────────────────────────────────────────
# cover: (source, crop box or None) -> square "book" cover for the home shelf
APPS = {
    "twomeows": {
        "icon": OCTO / "04_TwoMeows_LinguaStory/store_graphics_and_screens/icon_512.png",
        "feature": OCTO / "04_TwoMeows_LinguaStory/store_graphics_and_screens/feature_1024x500.png",
        "cover": (CHAR / "01_TwoMeows_original_teacher/svg/png/welcome_cat.png", (0, 0, 1024, 1024)),
        "shots": [OCTO / f"04_TwoMeows_LinguaStory/store_graphics_and_screens/screen_{i}.png" for i in range(1, 7)]
                 + [OCTO / f"04_TwoMeows_LinguaStory/store_graphics_and_screens/{n}.png"
                    for n in ("tablet_1_catalog", "tablet_2_word", "tablet_3_book")],
        "video": (OCTO / "04_TwoMeows_LinguaStory/video_promo/TwoMeows_promo_v2_UA_16x9.mp4", 13.0),
        "mark": CHAR / "01_TwoMeows_original_teacher/svg/png/mark_linguastory_cheer.png",
    },
    "marks-garage": {
        "icon": OCTO / "02_Marks_Garage/store_graphics/icon_512.png",
        "feature": OCTO / "02_Marks_Garage/store_graphics/feature_graphic_en_1024x500.png",
        "cover": (OCTO / "02_Marks_Garage/screenshots_store/phone/04_dig.png", (300, 0, 1380, 1080)),
        "shots": sorted((OCTO / "02_Marks_Garage/screenshots_store/phone").glob("*.png")),
        "video": (OCTO / "02_Marks_Garage/video_promo/promo.mp4", 14.0),
        "mark": CHAR / "02_Garage_mechanic_and_builder/png/cat_1.png",
    },
    "mark-the-cat": {
        "icon": OCTO / "03_Kotik_Mark_Workshop/store_graphics/icon_512.png",
        "feature": OCTO / "03_Kotik_Mark_Workshop/store_graphics/feature_en_1024x500.jpg",
        "cover": (OCTO / "03_Kotik_Mark_Workshop/screenshots_store/phone_02.jpg", (420, 0, 1500, 1080)),
        "shots": sorted((OCTO / "03_Kotik_Mark_Workshop/screenshots_store").glob("phone_*.jpg")),
        "video": (OCTO / "03_Kotik_Mark_Workshop/video_promo/promo_en_30s.mp4", 9.0),
        "mark": CHAR / "03_Workshop_BimiBoo_style/poses_G_approved/g/mark_wave.svg",
    },
    "marks-art": {
        "icon": OCTO / "06_Mark_Art_Studio/store_graphics/icon_512.png",
        "feature": OCTO / "06_Mark_Art_Studio/store_graphics/feature_1024x500.png",
        "cover": (OCTO / "06_Mark_Art_Studio/store_graphics/feature_1024x500.png", (0, 0, 500, 500)),
        "shots": sorted(Path("D:/Marks_art_studio/store/google_play/screenshots/phone_en").glob("*.png")),
        "video": (OCTO / "06_Mark_Art_Studio/mockups/alive_demo.mp4", 11.0),
        "mark": CHAR / "04_Art_Studio_artist/mark_artist_hello.svg",
    },
    "marks-home": {
        "icon": Path("D:/mark_game/store/google_play/icon_512.png"),
        "feature": Path("D:/mark_game/art/shell/splash_new.png"),
        "cover": (Path("D:/mark_game/store/google_play/icon_512.png"), None),
        "shots": [],
        "video": (Path("D:/mark_game/art/shell/demo_splash.mp4"), 6.5),
        "mark": Path("D:/mark_game/art/mark/mark_wave.png"),
    },
}

# Marks that peek from the sides of the home page (key -> source)
PEEK = {
    "teacher": SUITE / "assets/cats/meows_hello.svg",
    "teacher_heart": SUITE / "assets/cats/meows_heart.svg",
    "mechanic": CHAR / "02_Garage_mechanic_and_builder/png/cat_1.png",
    "builder": CHAR / "02_Garage_mechanic_and_builder/png/cat_2.png",
    "host_wave": CHAR / "03_Workshop_BimiBoo_style/poses_G_approved/g/mark_wave.svg",
    "host_point": CHAR / "03_Workshop_BimiBoo_style/poses_G_approved/g/mark_point.svg",
    "host_thumb": CHAR / "03_Workshop_BimiBoo_style/poses_G_approved/g/mark_thumb.svg",
    "host_cheer": CHAR / "03_Workshop_BimiBoo_style/poses_G_approved/g/mark_cheer.svg",
    "host_fly": CHAR / "03_Workshop_BimiBoo_style/poses_G_approved/g/mark_fly.svg",
    "artist_hello": CHAR / "04_Art_Studio_artist/mark_artist_hello.svg",
    "artist_show": CHAR / "04_Art_Studio_artist/mark_artist_show.svg",
    "artist_wow": CHAR / "04_Art_Studio_artist/mark_artist_wow.svg",
    "home_wave": Path("D:/mark_game/art/mark/mark_wave.png"),
    "home_cheer": Path("D:/mark_game/art/mark/mark_cheer.png"),
}

# The showreel (Mark greets, the apps in one device frame, «Powered by» at the end) is made by tools/build_reel.py.


def log(*a):
    print(*a, flush=True)


def save_webp(im, dst, max_w=None, max_h=None, q=82):
    im = im.copy()
    if max_w or max_h:
        im.thumbnail((max_w or 10**6, max_h or 10**6), Image.LANCZOS)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "WEBP", quality=q, method=6)
    log(f"  {dst.relative_to(ROOT)}  {im.size[0]}x{im.size[1]}  {dst.stat().st_size // 1024} KB")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg failed:\n" + r.stderr[-2000:])


def video_web(src, dst, poster_t):
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-preset", "slow", "-crf", "27",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", str(dst)])
    poster = dst.with_suffix(".jpg")
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(poster_t), "-i", str(src), "-frames:v", "1",
         "-vf", "scale='min(1280,iw)':-2", "-q:v", "4", str(poster)])
    log(f"  {dst.relative_to(ROOT)}  {dst.stat().st_size // 1024} KB  (+ poster)")


def import_app(slug, spec, skip_video):
    log(f"[{slug}]")
    media = ROOT / "apps" / slug / "media"
    media.mkdir(parents=True, exist_ok=True)
    for old in media.glob("shot_*.webp"):  # screenshots may shrink in number
        old.unlink()

    icon = Image.open(spec["icon"]).convert("RGBA")
    save_webp(icon, media / "icon.webp", 256, 256)
    icon.resize((512, 512), Image.LANCZOS).convert("RGB").save(media / "icon-512.png", optimize=True)

    save_webp(Image.open(spec["feature"]).convert("RGB"), media / "feature.webp", 1280)

    src, box = spec["cover"]
    cov = Image.open(src).convert("RGBA")
    if box:
        cov = cov.crop(box)
    w, h = cov.size
    s = min(w, h)
    cov = cov.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    bg = Image.new("RGBA", cov.size, (255, 255, 255, 255))
    bg.alpha_composite(cov)
    save_webp(bg.convert("RGB"), media / "cover.webp", 560, 560)

    shots = []
    for i, p in enumerate(spec["shots"], 1):
        im = Image.open(p).convert("RGB")
        portrait = im.size[1] > im.size[0]
        name = f"shot_{i:02d}.webp"
        save_webp(im, media / name, 640 if portrait else 1280, 1280 if portrait else 720, q=80)
        shots.append({"file": name, "portrait": portrait})

    mark = spec["mark"]
    if mark.suffix == ".svg":
        shutil.copy(mark, media / "mark.svg")
        mark_name = "mark.svg"
    else:
        im = Image.open(mark).convert("RGBA")
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
        save_webp(im, media / "mark.webp", None, 640)
        mark_name = "mark.webp"

    video = None
    if spec.get("video"):
        vsrc, poster_t = spec["video"]
        if not skip_video:
            video_web(vsrc, media / "promo.mp4", poster_t)
        video = "promo.mp4"

    manifest = {"shots": shots, "mark": mark_name, "video": video}
    (media / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def import_peek():
    """Марк выглядывает с боков, плитки, 404: единый облик (тёмный контур R25) делает tools/peek_cats.py."""
    log("[assets/mark] -> tools/peek_cats.py")
    import peek_cats
    peek_cats.main()


def build_showreel():
    log("[assets/video/showreel.mp4] -> tools/build_reel.py")
    import build_reel
    build_reel.main([])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated app slugs")
    ap.add_argument("--skip-video", action="store_true")
    ap.add_argument("--no-showreel", action="store_true")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    for slug, spec in APPS.items():
        if only and slug not in only:
            continue
        import_app(slug, spec, a.skip_video)
    if not only:
        import_peek()
        if not a.no_showreel and not a.skip_video:
            build_showreel()


if __name__ == "__main__":
    main()
