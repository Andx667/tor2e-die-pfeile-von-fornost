#!/usr/bin/env python3
"""Draws the GitHub social preview (1280x640) -> assets/social-preview.png.

Uses TeX Gyre Pagella. Title and subtitle come from adventure.toml.
    python3 tools/social.py
"""
import glob, os, tomllib
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1280, 640
INK, GOLD, PARCH = (29, 23, 20), (184, 156, 108), (247, 241, 230)
with open(os.path.join(ROOT, "adventure.toml"), "rb") as _f:
    CFG = tomllib.load(_f)


def font(style, size):
    for base in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\fonts"),
                 "/usr/share/texlive/texmf-dist/fonts", "/usr/share/texmf/fonts"):
        hit = glob.glob(os.path.join(base, f"**/texgyrepagella-{style}.otf"), recursive=True)
        if hit:
            return ImageFont.truetype(hit[0], size)
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), INK)
d = ImageDraw.Draw(img)
d.rectangle([28, 28, W - 29, H - 29], outline=GOLD, width=3)
d.rectangle([40, 40, W - 41, H - 41], outline=GOLD, width=1)

x = 90
d.text((x, 150), "THE ONE RING · 2. EDITION", font=font("bold", 26), fill=GOLD)
d.text((x, 200), CFG["title"], font=font("bolditalic", 92), fill=PARCH)
d.line([x, 345, x + 380, 335], fill=GOLD, width=2)
d.text((x, 360), CFG.get("tagline", "A TOR 2e adventure"), font=font("italic", 38), fill=(226, 212, 184))
d.text((x, 430), CFG.get("edition", "Print edition"), font=font("regular", 24), fill=(190, 176, 150))

logo = Image.open(os.path.join(ROOT, "assets", "logo.png")).convert("RGBA").resize((300, 300), Image.LANCZOS)
img.paste(logo, (W - 300 - 130, (H - 300) // 2), logo)

out = os.path.join(ROOT, "assets", "social-preview.png")
img.save(out, optimize=True)
print(out)
