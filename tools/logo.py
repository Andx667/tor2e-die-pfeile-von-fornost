#!/usr/bin/env python3
"""Zeichnet das Logo (Hügel mit rundem Hobbit-Tor unter einem Bogen mit Pfeil) -> assets/logo.svg, logo.png (512), logo.webp (144), logo-print.png (512, rot).

Weiß auf transparent (plus logo-print.png in Titelrot für die PDFs). SVG und Raster stammen aus
denselben Koordinaten (64×64-Raster).
    python3 tools/logo.py
"""
import math, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
os.makedirs(A, exist_ok=True)

GROUND = 54
# Hügel (Mittelpunkt x, y, Radius): zwei niedrige seitlich, der große in der Mitte mit dem runden Tor
HILLS_BACK = [(13, 55, 13, 12), (55, 55, 12, 11)]
HILL = (36, 54, 14, 16)
GAP = 1.3                       # heller Spalt um den vorderen Hügel
DOOR = (36, 49.5, 4.5)          # rundes Tor, sitzt auf dem Boden
KNOB = (38.2, 49.5, 0.8)

# Bogen: Kreisbogen (Bauch rechts), gerade Sehne, Pfeil mit Spitze und Befiederung
BX, BY, BR, BA = 16, 21, 11.5, 70
bow = [(BX + BR * math.cos(math.radians(a)), BY + BR * math.sin(math.radians(a))) for a in range(-BA, BA + 1, 5)]
string_x = BX + BR * math.cos(math.radians(BA))
ARROW_Y, TIP_X = BY, 32.5
head = [(TIP_X + 6, ARROW_Y), (TIP_X, ARROW_Y - 2.4), (TIP_X, ARROW_Y + 2.4)]
fletch = [[(string_x + d, ARROW_Y), (string_x + d - 2.4, ARROW_Y - 2.2)] for d in (0, 2.2)] +          [[(string_x + d, ARROW_Y), (string_x + d - 2.4, ARROW_Y + 2.2)] for d in (0, 2.2)]

# Bogen samt Pfeil um die Mitte drehen (Pfeil zeigt nach rechts oben) und etwas tiefer setzen
ANGLE, CENTER = 38, (32, 21)
_px, _py = (string_x + TIP_X + 6) / 2, ARROW_Y
_ca, _sa = math.cos(math.radians(ANGLE)), math.sin(math.radians(ANGLE))
T = lambda p: (CENTER[0] + (p[0] - _px) * _ca + (p[1] - _py) * _sa,
               CENTER[1] - (p[0] - _px) * _sa + (p[1] - _py) * _ca)
bow = [T(q) for q in bow]
string = [T((string_x, bow_y)) for bow_y in (BY - BR * math.sin(math.radians(BA)), BY + BR * math.sin(math.radians(BA)))]
arrow = [T((string_x, ARROW_Y)), T((TIP_X, ARROW_Y))]
head = [T(q) for q in head]
fletch = [[T(q) for q in f] for f in fletch]

INK = "#f5f3f2"


def pl(p):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in p)


bow_w, string_w, arrow_w, fl_w = 2.4, 1.0, 1.5, 1.2
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <clipPath id="c"><circle cx="32" cy="32" r="29"/></clipPath>
    <clipPath id="g"><rect width="64" height="{GROUND}"/></clipPath>
    <mask id="gap"><rect width="64" height="64" fill="#fff"/><ellipse cx="{HILL[0]}" cy="{HILL[1]}" rx="{HILL[2] + GAP}" ry="{HILL[3] + GAP}" fill="#000"/></mask>
    <mask id="door"><rect width="64" height="64" fill="#fff"/><circle cx="{DOOR[0]}" cy="{DOOR[1]}" r="{DOOR[2]}" fill="#000"/></mask>
  </defs>
  <circle cx="32" cy="32" r="29" fill="none" stroke="{INK}" stroke-width="3"/>
  <g clip-path="url(#c)"><g clip-path="url(#g)" fill="{INK}">
    <g mask="url(#gap)">{"".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>' for x, y, rx, ry in HILLS_BACK)}</g>
    <g mask="url(#door)"><ellipse cx="{HILL[0]}" cy="{HILL[1]}" rx="{HILL[2]}" ry="{HILL[3]}"/></g>
    <circle cx="{KNOB[0]}" cy="{KNOB[1]}" r="{KNOB[2]}"/>
  </g></g>
  <g fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="{pl(bow)}" stroke-width="{bow_w}"/>
    <line x1="{string[0][0]:.2f}" y1="{string[0][1]:.2f}" x2="{string[1][0]:.2f}" y2="{string[1][1]:.2f}" stroke-width="{string_w}"/>
    <line x1="{arrow[0][0]:.2f}" y1="{arrow[0][1]:.2f}" x2="{arrow[1][0]:.2f}" y2="{arrow[1][1]:.2f}" stroke-width="{arrow_w}"/>
    {"".join(f'<polyline points="{pl(f)}" stroke-width="{fl_w}"/>' for f in fletch)}
  </g>
  <polygon points="{pl(head)}" fill="{INK}"/>
</svg>
'''
open(os.path.join(A, "logo.svg"), "w", encoding="utf-8").write(svg)

S = 8 * 64
k = S / 64
sc = lambda p: [(x * k, y * k) for x, y in p]
circ = lambda d, x, y, r, fill: d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=fill)

m = Image.new("L", (S, S), 0)
d = ImageDraw.Draw(m)
d.ellipse([3 * k, 3 * k, 61 * k, 61 * k], outline=255, width=int(3 * k))

# Hügel auf eigener Ebene, dann auf Boden und Ring zuschneiden
h = Image.new("L", (S, S), 0)
hd = ImageDraw.Draw(h)
ell = lambda d, x, y, rx, ry, fill: d.ellipse([(x - rx) * k, (y - ry) * k, (x + rx) * k, (y + ry) * k], fill=fill)
for x, y, rx, ry in HILLS_BACK:
    ell(hd, x, y, rx, ry, 255)
ell(hd, HILL[0], HILL[1], HILL[2] + GAP, HILL[3] + GAP, 0)
ell(hd, *HILL, 255)
circ(hd, *DOOR, 0)
circ(hd, *KNOB, 255)
hd.rectangle([0, GROUND * k, S, S], fill=0)
clip = Image.new("L", (S, S), 0)
ImageDraw.Draw(clip).ellipse([3 * k, 3 * k, 61 * k, 61 * k], fill=255)
h = Image.composite(h, Image.new("L", (S, S), 0), clip)
m.paste(255, mask=h)

line = lambda p, w: d.line(sc(p), fill=255, width=max(1, int(w * k)), joint="curve")
dot = lambda x, y, w: circ(d, x, y, w / 2, 255)
for pts_, w in ((bow, bow_w), (string, string_w), (arrow, arrow_w)):
    line(pts_, w)
    for x, y in (pts_[0], pts_[-1]):
        dot(x, y, w)
for f in fletch:
    line(f, fl_w)
    dot(*f[0], fl_w); dot(*f[1], fl_w)
d.polygon(sc(head), fill=255)

img = Image.new("RGBA", (S, S), (245, 243, 242, 0))
img.putalpha(m)
img.resize((512, 512), Image.LANCZOS).save(os.path.join(A, "logo.png"), optimize=True)
img.resize((144, 144), Image.LANCZOS).save(os.path.join(A, "logo.webp"), quality=90, method=6)
ink = Image.new("RGBA", (S, S), (0x7A, 0x2A, 0x1F, 0))   # fwred aus blaueberge.sty
ink.putalpha(m)
ink.resize((512, 512), Image.LANCZOS).save(os.path.join(A, "logo-print.png"), optimize=True)
print("assets/logo.svg, logo.png, logo.webp, logo-print.png")
