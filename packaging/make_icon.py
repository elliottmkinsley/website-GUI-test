"""Generate ``packaging/icon.ico`` from a vector-style placeholder.

The icon is intentionally simple - a navy disc with a white "R"
glyph - so it's recognisable in the Windows taskbar at 16x16 and
in Start Menu / Alt-Tab at 256x256. Swap it for the real Radiant
logo before tagging v1.0 by replacing the implementation below
(or by hand-providing a multi-resolution ``packaging/icon.ico``
and deleting this script).

Run:

    python packaging/make_icon.py

Output:

    packaging/icon.ico (multi-resolution: 16, 32, 48, 64, 128, 256 px)

This script is run on demand by a maintainer; CI does not call it.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_PATH = Path(__file__).resolve().parent / "icon.ico"

BRAND_NAVY = (15, 33, 71)
ACCENT_BLUE = (22, 48, 107)
WHITE = (255, 255, 255)

# Per Windows convention - the OS picks the closest size for each
# context. 256 is the modern Vista+ standard; smaller sizes are for
# legacy and very dense UI elements.
SIZES = [16, 32, 48, 64, 128, 256]


def _render_glyph(size: int) -> Image.Image:
    """Render a single-size square ``Image`` with the placeholder
    glyph centered inside a navy disc."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer disc with a 1px-equivalent gradient ring for depth.
    pad = max(1, size // 32)
    draw.ellipse(
        (pad, pad, size - pad, size - pad),
        fill=BRAND_NAVY,
        outline=ACCENT_BLUE,
        width=max(1, size // 64),
    )

    # Centered "R" glyph.
    try:
        # Try several common bold fonts in order of preference.
        for face in (
            "segoeuib.ttf",  # Segoe UI Bold (Windows)
            "arialbd.ttf",
            "Helvetica-Bold.ttf",
            "DejaVuSans-Bold.ttf",
        ):
            try:
                font = ImageFont.truetype(face, int(size * 0.6))
                break
            except OSError:
                continue
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # Compensate for the bbox's offset-from-origin so the glyph
    # really lands in the geometric centre of the disc.
    cx = (size - tw) / 2 - bbox[0]
    cy = (size - th) / 2 - bbox[1]
    draw.text((cx, cy), text, fill=WHITE, font=font)
    return img


def main() -> int:
    frames = [_render_glyph(s) for s in SIZES]
    biggest = frames[-1]
    biggest.save(
        OUT_PATH,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
    )
    print(f"Wrote {OUT_PATH} with sizes {SIZES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
