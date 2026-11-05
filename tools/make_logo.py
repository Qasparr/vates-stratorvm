#!/usr/bin/env python3
# ============================================================================
# 93
#
# VATES STRATORVM · tools/make_logo.py — the SOL seal, drawn in code.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Scientific Illuminism — Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# MECHANISM: a deterministic drawing — PIL primitives only, no external
# assets, no randomness. Purple field, gold rim and lettering, green as
# the third colour of the release livery. The motif is the callsign made
# visible: a radiant sun that is also an eye (SOL, the Seer) above
# concentric layered arcs (the strata). Rim legend above: the name;
# below: the callsign and its gloss.
#
# DOCTRINE: a seal is a claim made visible. It is drawn, not downloaded;
# the same code draws the same seal, byte for byte, on any machine.
#
# Usage:  python3 tools/make_logo.py [output.png]
# ============================================================================

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

PURPLE = (75, 0, 130)        # #4B0082 — the field
DEEP_PURPLE = (46, 0, 79)    # #2E004F — the outer ground
GOLD = (255, 215, 0)         # #FFD700 — rim, rays, lettering
GREEN = (46, 204, 113)       # the third colour — iris ring, strata band
DARK_GREEN = (31, 163, 74)
SIZE = 1200
CENTER = SIZE // 2
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def circular_text(draw, text, radius, center, font, fill,
                  start_deg, end_deg, flip=False):
    """MECHANISM: set a string along a circular arc, one glyph at a
    time, each rotated tangent to the circle. flip=True walks the
    bottom arc so the lettering reads upright left-to-right."""
    n = len(text)
    for i, ch in enumerate(text):
        frac = i / max(n - 1, 1)
        ang = math.radians(start_deg + (end_deg - start_deg) * frac)
        x = center + radius * math.cos(ang)
        y = center + radius * math.sin(ang)
        glyph = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((45, 45), ch, font=font, fill=fill, anchor="mm")
        rotation = -(math.degrees(ang) + 90)
        if flip:
            rotation += 180
        glyph = glyph.rotate(rotation, resample=Image.BICUBIC,
                             center=(45, 45))
        draw._image.paste(glyph, (int(x - 45), int(y - 45)), glyph)


def draw_seal(path):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # The ground and the field: gold rim, purple disc.
    d.ellipse([30, 30, SIZE - 30, SIZE - 30], fill=GOLD)
    d.ellipse([52, 52, SIZE - 52, SIZE - 52], fill=DEEP_PURPLE)
    d.ellipse([78, 78, SIZE - 78, SIZE - 78], fill=PURPLE)
    # A green hairline between rim and field — the third colour seated.
    d.ellipse([66, 66, SIZE - 66, SIZE - 66], outline=GREEN, width=5)

    # -- The strata: concentric layered arcs across the lower half. ----
    # PIL arc angles: 0 at 3 o'clock, increasing clockwise — 0..180 is
    # the bottom semicircle. Bands alternate gold / green / light purple.
    strata_cy = 700
    band_colors = [GOLD, GREEN, (147, 112, 219), GOLD, DARK_GREEN]
    for i, color in enumerate(band_colors):
        r = 330 - i * 52
        box = [CENTER - r, strata_cy - r, CENTER + r, strata_cy + r]
        d.arc(box, start=0, end=180, fill=color, width=30)

    # -- SOL: the sun that is an eye, above the strata. -----------------
    eye_cx, eye_cy = CENTER, 430
    # Rays: twelve gold rays radiating behind the eye.
    for k in range(12):
        ang = math.radians(k * 30 + 15)
        x1 = eye_cx + 215 * math.cos(ang)
        y1 = eye_cy + 150 * math.sin(ang)
        x2 = eye_cx + 268 * math.cos(ang)
        y2 = eye_cy + 192 * math.sin(ang)
        d.line([x1, y1, x2, y2], fill=GOLD, width=13)
    # The eye: a wide almond in gold outline.
    d.ellipse([eye_cx - 205, eye_cy - 105, eye_cx + 205, eye_cy + 105],
              outline=GOLD, width=11)
    # The iris: green ring, gold disc, purple pupil — the sun in the eye.
    d.ellipse([eye_cx - 88, eye_cy - 88, eye_cx + 88, eye_cy + 88],
              fill=GREEN)
    d.ellipse([eye_cx - 66, eye_cy - 66, eye_cx + 66, eye_cy + 66],
              fill=GOLD)
    d.ellipse([eye_cx - 28, eye_cy - 28, eye_cx + 28, eye_cy + 28],
              fill=DEEP_PURPLE)

    # -- Rim legends. ----------------------------------------------------
    font_big = ImageFont.truetype(FONT_PATH, 64)
    font_small = ImageFont.truetype(FONT_PATH, 47)
    circular_text(d, "VATES STRATORVM", 492, CENTER, font_big, GOLD,
                  start_deg=-160, end_deg=-20)
    circular_text(d, "SOL · SEER OF LAYERS", 488, CENTER, font_small,
                  GOLD, start_deg=155, end_deg=25, flip=True)
    # Two gold stars flank the legends at the horizontal diameter.
    for sx in (108, SIZE - 108):
        d.ellipse([sx - 11, CENTER - 11, sx + 11, CENTER + 11],
                  fill=GOLD)

    img.save(path)
    return path


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "logo", "vates-stratorvm-seal.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    draw_seal(out)
    print(f"seal written: {out}")


if __name__ == "__main__":
    main()

# ============================================================================
# 93 — Live, Love, and let Love, Live.
# ============================================================================
