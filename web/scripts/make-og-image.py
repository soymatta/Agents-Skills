#!/usr/bin/env python3
"""Generate web/public/og-image.png (1200x630 social card) deterministically.

Open Graph consumers do not render SVG, so the card ships as a PNG. Regenerate
after changing the palette or the tagline:

    python3 web/scripts/make-og-image.py

Requires Pillow and the DejaVu fonts (present on Debian/Ubuntu images). The
output is byte-stable for a given Pillow version, so a rebuild is reviewable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (10, 10, 11)
ACCENT = (99, 102, 241)
ACCENT_LIGHT = (129, 140, 248)
TEXT = (250, 250, 250)
MUTED = (161, 161, 170)

TITLE = "Agents & Skills"
SUBTITLE = (
    "AI agent, skill and plugin definitions for OpenCode, "
    "Claude Code, Cursor and Windsurf"
)
FOOTER = "github.com/soymatta/Agents-Skills"
TAGS = "MIT License  ·  OpenCode  ·  Claude Code  ·  Cursor  ·  Windsurf"

OUT = Path(__file__).resolve().parents[1] / "public" / "og-image.png"

FONT_DIRS = (
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/dejavu"),
)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        path = directory / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise SystemExit(f"font not found: {name} in {[str(d) for d in FONT_DIRS]}")


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=fnt) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def main() -> int:
    image = Image.new("RGB", (W, H), BG)

    # Soft accent glow, top-left: a radial gradient tinted with the accent color.
    glow = (
        Image.radial_gradient("L")
        .resize((W, H), Image.LANCZOS)
        .point(lambda v: max(0, 150 - v))
    )
    tint = Image.new("RGB", (W, H), ACCENT)
    image = Image.composite(tint, image, glow.point(lambda v: v // 3))

    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, W, 6), fill=ACCENT)

    title_font = font("DejaVuSans-Bold.ttf", 96)
    body_font = font("DejaVuSans.ttf", 34)
    small_font = font("DejaVuSans.ttf", 26)
    mono_font = font("DejaVuSansMono-Bold.ttf", 28)

    x, width = 80, W - 160
    draw.text((x, 170), TITLE, font=title_font, fill=TEXT)

    y = 320
    for line in wrap(draw, SUBTITLE, body_font, width):
        draw.text((x, y), line, font=body_font, fill=MUTED)
        y += 46

    draw.line((x, 500, x + 220, 500), fill=ACCENT, width=4)
    draw.text((x, 528), FOOTER, font=mono_font, fill=ACCENT_LIGHT)
    draw.text((x, 578), TAGS, font=small_font, fill=MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, format="PNG", optimize=True)
    print(f"{OUT} {image.size[0]}x{image.size[1]} {OUT.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
