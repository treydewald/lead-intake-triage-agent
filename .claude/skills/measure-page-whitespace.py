#!/usr/bin/env python3
"""
Measures the fraction of empty vertical space below a page's real content,
by scanning a screenshot from the bottom row up until a row's colors stop
matching the page background. Excludes the bottom-right "Updated" timestamp
watermark region, which is present on every page regardless of content.

Introduced Step 11 Round 5 (2026-09-05) to replace visual estimation of the
"empty void below sparse content" composition finding with a reproducible
measurement. Reused by Step 12 Round 5 to verify the fix.

Usage: python measure-page-whitespace.py <screenshots-dir> [--bg R,G,B]
"""
import sys
from pathlib import Path
from PIL import Image

# The app's page background (bg-slate-50).
DEFAULT_BG = (248, 250, 252)
BG_TOLERANCE = 6

# Bottom-right corner reserved for the "Updated" timestamp watermark on every page.
WATERMARK_WIDTH = 260
WATERMARK_HEIGHT = 40

# The persistent left sidebar (Layout.tsx `aside`, Tailwind w-60 = 240px) is present at
# every row regardless of page content and must be excluded from the scan, or every row
# would register as "content" via the sidebar's own background alone. Desktop only (this
# script is intended for the 1920x1080 desktop screenshots) - mobile screenshots have no
# sidebar (collapses to a top bar) so the full width is scanned there.
SIDEBAR_WIDTH_DESKTOP = 240
DESKTOP_MIN_WIDTH = 1200


def measure(image_path: Path, bg=DEFAULT_BG):
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    pixels = img.load()
    watermark_y_start = height - WATERMARK_HEIGHT
    watermark_x_start = width - WATERMARK_WIDTH
    scan_x_start = SIDEBAR_WIDTH_DESKTOP if width >= DESKTOP_MIN_WIDTH else 0

    first_content_row_from_bottom = None
    for y in range(height - 1, -1, -1):
        in_watermark_band = y >= watermark_y_start
        is_bg = True
        for x in range(scan_x_start, width, 4):
            if in_watermark_band and x >= watermark_x_start:
                continue  # skip the watermark region entirely
            px = pixels[x, y]
            r, g, b = px[0], px[1], px[2]
            if abs(r - bg[0]) > BG_TOLERANCE or abs(g - bg[1]) > BG_TOLERANCE or abs(b - bg[2]) > BG_TOLERANCE:
                is_bg = False
                break
        if not is_bg:
            first_content_row_from_bottom = y
            break

    if first_content_row_from_bottom is None:
        empty_px = height
    else:
        empty_px = height - 1 - first_content_row_from_bottom
    empty_fraction = empty_px / height
    return empty_px, height, empty_fraction


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    directory = Path(sys.argv[1])
    bg = DEFAULT_BG
    for arg in sys.argv[2:]:
        if arg.startswith("--bg"):
            bg = tuple(int(v) for v in arg.split("=", 1)[1].split(","))

    for path in sorted(directory.glob("*.png")):
        empty_px, height, frac = measure(path, bg)
        print(f"{path.name:28s} empty={empty_px:4d}px / {height}px  ({frac*100:5.1f}%)")


if __name__ == "__main__":
    main()
