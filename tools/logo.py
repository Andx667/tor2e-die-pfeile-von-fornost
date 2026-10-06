#!/usr/bin/env python3
"""Zeichnet das Logo (Berggipfel unter einem Stern) -> assets/logo.svg, logo.png (512), logo.webp (144), logo-print.png (512, rot).

Weiß auf transparent (plus logo-print.png in Titelrot für die PDFs). SVG und Raster stammen aus
denselben Koordinaten (64×64-Raster).
    python3 tools/logo.py
"""
import math, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
os.makedirs(A, exist_ok=True)

# Stern: 8 Strahlen, schlank
SX, SY, RO, RI, N = 32, 14.5, 7, 2.3, 8
star = [(SX + (RO if i % 2 == 0 else RI) * math.sin(math.pi * i / N),
         SY - (RO if i % 2 == 0 else RI) * math.cos(math.pi * i / N)) for i in range(2 * N)]
# Gebirge: hoher Gipfel in der Mitte, zwei niedrigere seitlich
peaks = [(12, 52), (24, 34), (29, 40), (38, 27), (49, 44), (53, 40), (58, 52)]
# Stolleneingang: Rechteck + Halbrund oben
door = (28.5, 44, 35.5, 52)


def pts(p):
    return "M" + " L".join(f"{x:g} {y:g}" for x, y in p) + "Z"


svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <circle cx="32" cy="32" r="29" fill="none" stroke="#f5f3f2" stroke-width="3"/>
  <path fill="#f5f3f2" fill-rule="evenodd" d="{pts(star)} {pts(peaks)} M28.5 52V47.5a3.5 3.5 0 0 1 7 0V52Z"/>
</svg>
'''
open(os.path.join(A, "logo.svg"), "w", encoding="utf-8").write(svg)

S = 8 * 64
k = S / 64
m = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(m)
sc = lambda p: [(x * k, y * k) for x, y in p]
d.ellipse([3 * k, 3 * k, 61 * k, 61 * k], outline=255, width=int(3 * k))
for poly in (star, peaks):
    d.polygon(sc(poly), fill=255)
x0, y0, x1, y1 = door
d.rectangle([x0 * k, (y0 + 3.5) * k, x1 * k, y1 * k], fill=0)
d.pieslice([x0 * k, y0 * k, x1 * k, (y0 + 7) * k], 180, 360, fill=0)

img = Image.new("RGBA", (S, S), (245, 243, 242, 0))
img.putalpha(m)
img.resize((512, 512), Image.LANCZOS).save(os.path.join(A, "logo.png"), optimize=True)
img.resize((144, 144), Image.LANCZOS).save(os.path.join(A, "logo.webp"), quality=90, method=6)
ink = Image.new("RGBA", (S, S), (0x7A, 0x2A, 0x1F, 0))   # fwred aus blaueberge.sty
ink.putalpha(m)
ink.resize((512, 512), Image.LANCZOS).save(os.path.join(A, "logo-print.png"), optimize=True)
print("assets/logo.svg, logo.png, logo.webp, logo-print.png")
