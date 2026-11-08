"""Render tools/og-cover.html to assets/brand/og-cover.jpg (1200x630) with headless Edge/Chrome.

    python tools/render_og.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def main():
    exe = next((c for c in CANDIDATES if Path(c).exists()), None) or shutil.which("msedge") or shutil.which("chrome")
    if not exe:
        sys.exit("Edge/Chrome not found")
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "og.png"
        url = (ROOT / "tools" / "og-cover.html").resolve().as_uri()
        subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        f"--user-data-dir={tmp}", "--virtual-time-budget=4000",
                        "--window-size=1200,630", f"--screenshot={png}", url],
                       check=True, capture_output=True, timeout=90)
        im = Image.open(png).convert("RGB").crop((0, 0, 1200, 630))
        out = ROOT / "assets" / "brand" / "og-cover.jpg"
        im.save(out, "JPEG", quality=86, optimize=True)
        print("wrote", out.relative_to(ROOT), im.size, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
