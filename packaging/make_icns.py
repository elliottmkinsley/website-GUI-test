"""Generate ``packaging/icon.icns`` from the same placeholder used
by ``make_icon.py`` (the Windows icon).

Why the duplication? Apple's ``.icns`` and Microsoft's ``.ico`` are
different container formats; PyInstaller picks the right one per
target OS. By keeping the *visual design* identical we avoid two
divergent brand assets while the project is still in placeholder-
logo territory. When the real Radiant logo is ready, replace the
``_render_glyph`` implementation in *both* scripts (or, simpler,
drop hand-authored ``icon.ico`` + ``icon.icns`` into ``packaging/``
and delete both generator scripts).

Run:

    python packaging/make_icns.py

Output:

    packaging/icon.icns

The script is platform-independent: it uses Pillow's built-in ICNS
writer rather than Apple's ``iconutil``, so the maintainer can
regenerate the icon from any OS. Sizes match Apple's recommended
``icns`` ladder (16-1024 px) so the icon looks crisp from Dock
through Finder Preview through high-DPI Launchpad.

This script is run on demand by a maintainer; CI does not call it.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_PATH = Path(__file__).resolve().parent / "icon.icns"

# Same brand palette as make_icon.py - keep these in sync.
BRAND_NAVY = (15, 33, 71)
ACCENT_BLUE = (22, 48, 107)
WHITE = (255, 255, 255)

# Apple's recommended ICNS sizes. Pillow writes whichever of these
# are present in the image stack. Including all eight covers every
# context from the Dock badge (16) up to Launchpad/Quick Look
# (1024). The retina variants (32, 64, 256, 512) are auto-handled
# by macOS once the matching @2x is present.
SIZES = [16, 32, 64, 128, 256, 512, 1024]


def _render_glyph(size: int) -> Image.Image:
    """Render a single-size square ``Image`` with the placeholder
    glyph centered inside a navy disc. Mirrors ``make_icon.py``."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = max(1, size // 32)
    draw.ellipse(
        (pad, pad, size - pad, size - pad),
        fill=BRAND_NAVY,
        outline=ACCENT_BLUE,
        width=max(1, size // 64),
    )

    try:
        # Same font preference order as the Windows icon. On macOS
        # the Helvetica family is preferred; on Windows Segoe UI is
        # available. The fallback chain keeps the script working
        # from any maintainer's box.
        for face in (
            "Helvetica-Bold.ttf",
            "HelveticaNeue.ttc",
            "segoeuib.ttf",
            "arialbd.ttf",
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
    cx = (size - tw) / 2 - bbox[0]
    cy = (size - th) / 2 - bbox[1]
    draw.text((cx, cy), text, fill=WHITE, font=font)
    return img


def main() -> int:
    # Pillow's ICNS writer expects the *biggest* image to be passed
    # as the primary, with the smaller sizes appended via the
    # ``append_images`` argument. Without that argument only the
    # primary size lands in the file and macOS falls back to fuzzy
    # scaling at every other size.
    frames = [_render_glyph(s) for s in SIZES]
    primary = frames[-1]
    others = frames[:-1]
    primary.save(
        OUT_PATH,
        format="ICNS",
        append_images=others,
    )
    print(f"Wrote {OUT_PATH} with sizes {SIZES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
