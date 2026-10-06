#!/usr/bin/env python3
"""Draws the adventure maps -> assets/maps/map-<id>.jpg (Loremaster) and map-<id>-players.jpg.

    python3 tools/maps.py            # all maps
    python3 tools/maps.py example    # one map

Style: weathered parchment, wobbly ink walls with hatching, calligraphic labels (TeX Gyre Chorus).
Loremaster versions carry the numbered markers from the text plus secrets (red); player versions
show only the layout. Only Pillow is needed. All coordinates are on a 1600 x 1200 grid.
"""
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "maps")
W, H, S = 1600, 1200, 2          # grid size and supersampling factor

INK = (43, 36, 32)
RED = (122, 42, 31)
GREY = (111, 102, 92)
PARCH = (233, 220, 186)
FLOOR = (246, 239, 217)
HATCH = (112, 92, 66)
WATER = (86, 122, 140)
GOLD = (160, 125, 70)
STONE = (150, 138, 120)


def kpse(name):
    try:
        r = subprocess.run(["kpsewhich", name], capture_output=True, text=True)
        return r.stdout.strip() or None
    except FileNotFoundError:
        return None


_FONTS = {}


def font(kind, size):
    key = (kind, size)
    if key not in _FONTS:
        names = {"chorus": "texgyrechorus-mediumitalic.otf", "bold": "texgyrepagella-bold.otf",
                 "italic": "texgyrepagella-italic.otf"}
        path = kpse(names[kind])
        _FONTS[key] = ImageFont.truetype(path, int(size * S)) if path else ImageFont.load_default()
    return _FONTS[key]


def sc(p):
    return (p[0] * S, p[1] * S)


# ---------------------------------------------------------------- paper
def noise(w, h, grain, blur, sigma=60):
    n = Image.effect_noise((max(1, w // grain), max(1, h // grain)), sigma)
    n = n.resize((w, h), Image.BICUBIC)
    return n.filter(ImageFilter.GaussianBlur(blur)) if blur else n


def parchment(seed):
    rnd = random.Random(seed)
    w, h = W * S, H * S
    big = ImageOps.autocontrast(noise(w, h, 64, 40), cutoff=1)
    mid = ImageOps.autocontrast(noise(w, h, 12, 6), cutoff=1)
    fine = noise(w, h, 1, 0, 30)
    base = ImageOps.colorize(big, (214, 196, 158), (242, 231, 200))
    base = Image.blend(base, ImageOps.colorize(mid, (214, 196, 158), (242, 231, 200)), 0.35)
    base = Image.blend(base, ImageOps.colorize(fine, (222, 206, 170), (240, 229, 198)), 0.12)
    # stains
    st = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(st)
    for _ in range(7):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(80, 240) * S // 2
        sd.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=rnd.randint(25, 55))
    st = st.filter(ImageFilter.GaussianBlur(60))
    base = Image.composite(Image.new("RGB", (w, h), (176, 146, 100)), base, st)
    # vignette
    vg = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vg).ellipse([w * 0.04, h * 0.05, w * 0.96, h * 0.95], fill=255)
    vg = ImageOps.invert(vg.filter(ImageFilter.GaussianBlur(160))).point(lambda v: int(v * 0.5))
    return Image.composite(Image.new("RGB", (w, h), (120, 88, 52)), base, vg)


# ---------------------------------------------------------------- strokes
class Pen:
    def __init__(self, img, seed):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.r = random.Random(seed)

    def wob(self, pts, amp=1.2, step=16):
        out = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
            for i in range(n):
                t = i / n
                out.append((x0 + (x1 - x0) * t + self.r.uniform(-amp, amp),
                            y0 + (y1 - y0) * t + self.r.uniform(-amp, amp)))
        out.append(pts[-1])
        return out

    def line(self, pts, w=2.4, col=INK, amp=1.2, closed=False):
        pts = list(pts) + ([pts[0]] if closed else [])
        wp = [sc(p) for p in self.wob(pts, amp)]
        self.d.line(wp, fill=col, width=max(1, int(w * S)), joint="curve")

    def dashed(self, pts, w=3, col=RED, dash=16, gap=12):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            n = int(L // (dash + gap)) + 1
            ux, uy = (x1 - x0) / (L or 1), (y1 - y0) / (L or 1)
            for i in range(n):
                a = i * (dash + gap)
                b = min(a + dash, L)
                if a >= L:
                    break
                self.d.line([sc((x0 + ux * a, y0 + uy * a)), sc((x0 + ux * b, y0 + uy * b))],
                            fill=col, width=int(w * S))

    def arrow(self, pts, w=3, col=RED, dashed=True, head=16):
        (self.dashed if dashed else self.line)(pts, w=w, col=col) if dashed else self.line(pts, w=w, col=col)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        a = math.atan2(y1 - y0, x1 - x0)
        for da in (2.6, -2.6):
            self.d.line([sc((x1, y1)), sc((x1 + head * math.cos(a + da), y1 + head * math.sin(a + da)))],
                        fill=col, width=int(w * S))

    def circle(self, x, y, r, fill=None, outline=INK, w=2.4):
        self.d.ellipse([sc((x - r, y - r)), sc((x + r, y + r))], fill=fill, outline=outline, width=int(w * S))

    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, w=2.4, amp=0.8):
        if fill:
            self.d.rectangle([sc((x0, y0)), sc((x1, y1))], fill=fill)
        if outline:
            self.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], w=w, col=outline, amp=amp, closed=True)

    def text(self, xy, s, size=40, col=INK, kind="chorus", anchor="mm", halo=True, rot=0, halo_col=FLOOR):
        f = font(kind, size)
        if rot:
            bbox = self.d.textbbox((0, 0), s, font=f, stroke_width=4)
            tw, th = bbox[2] + 20, bbox[3] + 20
            layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            if halo:
                ld.text((10, 10), s, font=f, fill=halo_col + (235,), stroke_width=4, stroke_fill=halo_col + (235,))
            ld.text((10, 10), s, font=f, fill=col + (255,))
            layer = layer.rotate(rot, expand=True, resample=Image.BICUBIC)
            x, y = sc(xy)
            self.img.paste(layer, (int(x - layer.width / 2), int(y - layer.height / 2)), layer)
            return
        if halo:
            self.d.text(sc(xy), s, font=f, fill=col, anchor=anchor, stroke_width=4, stroke_fill=halo_col)
        else:
            self.d.text(sc(xy), s, font=f, fill=col, anchor=anchor)

    def marker(self, xy, n):
        x, y = xy
        self.circle(x, y, 22, fill=RED, outline=INK, w=2.4)
        self.d.text(sc((x, y - 1)), str(n), font=font("bold", 29), fill=PARCH, anchor="mm")


# ---------------------------------------------------------------- cave plan
def warp(img, amp, cell, rnd):
    w, h = img.size
    cell *= S
    nx, ny = w // cell + 1, h // cell + 1
    jit = {(i, j): (rnd.uniform(-amp, amp) * S, rnd.uniform(-amp, amp) * S)
           for i in range(nx + 2) for j in range(ny + 2)}
    mesh = []
    for j in range(ny):
        for i in range(nx):
            x0, y0, x1, y1 = i * cell, j * cell, min(w, (i + 1) * cell), min(h, (j + 1) * cell)
            if x0 >= w or y0 >= h:
                continue
            p = [jit[(i, j)], jit[(i, j + 1)], jit[(i + 1, j + 1)], jit[(i + 1, j)]]
            quad = (x0 + p[0][0], y0 + p[0][1], x0 + p[1][0], y1 + p[1][1],
                    x1 + p[2][0], y1 + p[2][1], x1 + p[3][0], y0 + p[3][1])
            mesh.append(((x0, y0, x1, y1), quad))
    return img.transform(img.size, Image.MESH, mesh, Image.BILINEAR)


class Plan:
    """Floors (rooms, corridors) become one mask; walls, hatching and fill are derived from it."""

    def __init__(self, seed):
        self.seed = seed
        self.mask = Image.new("L", (W * S, H * S), 0)
        self.md = ImageDraw.Draw(self.mask)

    def poly(self, pts):
        self.md.polygon([sc(p) for p in pts], fill=255)

    def rect(self, x0, y0, x1, y1):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def ellipse(self, cx, cy, rx, ry):
        self.md.ellipse([sc((cx - rx, cy - ry)), sc((cx + rx, cy + ry))], fill=255)

    def corridor(self, pts, width):
        sp = [sc(p) for p in pts]
        self.md.line(sp, fill=255, width=int(width * S), joint="curve")
        r = width * S / 2
        for x, y in (sp[0], sp[-1]):
            self.md.ellipse([x - r, y - r, x + r, y + r], fill=255)

    def paint(self, bg):
        rnd = random.Random(self.seed)
        m = warp(self.mask, 3.0, 40, rnd)
        w, h = m.size
        # hatched rock around the floors
        band = m.filter(ImageFilter.GaussianBlur(24 * S // 2)).point(lambda v: 255 if v > 22 else 0)
        band = warp(band, 7.0, 36, rnd)
        band = ImageChops.subtract(band, m)
        pat = Image.new("L", (w, h), 0)
        pd = ImageDraw.Draw(pat)
        step = 11 * S
        for k in range(-h, w, step):
            pd.line([(k, 0), (k + h, h)], fill=255, width=max(1, S))
        inner = m.filter(ImageFilter.GaussianBlur(12 * S // 2)).point(lambda v: 255 if v > 22 else 0)
        inner = ImageChops.subtract(warp(inner, 5.0, 30, rnd), m)
        pat2 = Image.new("L", (w, h), 0)
        pd2 = ImageDraw.Draw(pat2)
        for k in range(0, w + h, step):
            pd2.line([(k, 0), (k - h, h)], fill=255, width=max(1, S))
        bg.paste(Image.new("RGB", (w, h), HATCH), mask=ImageChops.multiply(band, pat.point(lambda v: int(v * 0.55))))
        bg.paste(Image.new("RGB", (w, h), HATCH), mask=ImageChops.multiply(inner, pat2.point(lambda v: int(v * 0.5))))
        # floor fill with a little grain
        grain = ImageOps.colorize(ImageOps.autocontrast(noise(w, h, 3, 1), cutoff=2),
                                  (236, 226, 198), FLOOR)
        bg.paste(grain, mask=m)
        # wall line
        edge = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(7)), m)
        bg.paste(Image.new("RGB", (w, h), INK), mask=edge)
        shadow = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(15)), m.filter(ImageFilter.MaxFilter(7)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(3 * S)).point(lambda v: int(v * 0.35))
        bg.paste(Image.new("RGB", (w, h), (90, 70, 50)), mask=ImageChops.multiply(shadow, ImageOps.invert(m)))
        return m


# ---------------------------------------------------------------- common furniture
def frame(pen):
    pen.rect(22, 22, W - 22, H - 22, outline=INK, w=3.2, amp=0.6)
    pen.rect(34, 34, W - 34, H - 34, outline=GREY, w=1.4, amp=0.5)


def compass(pen, x=1500, y=1090, r=62):
    d = pen.d
    for a, ln in ((0, 1), (90, .6), (180, .6), (270, .6)):
        ang = math.radians(a - 90)
        tip = (x + r * ln * math.cos(ang), y + r * ln * math.sin(ang))
        l = (x + r * .17 * math.cos(ang - 1.57), y + r * .17 * math.sin(ang - 1.57))
        rr = (x + r * .17 * math.cos(ang + 1.57), y + r * .17 * math.sin(ang + 1.57))
        d.polygon([sc(tip), sc(l), sc((x, y)), sc(rr)], fill=INK if a == 0 else GREY)
    pen.circle(x, y, r * .78, outline=GREY, w=1.4)
    pen.text((x, y - r - 22), "N", size=34, col=INK, halo=False)


def scalebar(pen, label, x=90, y=1128, length=240):
    pen.line([(x, y), (x + length, y)], w=3, col=INK, amp=0.3)
    for i in range(5):
        pen.line([(x + length * i / 4, y - 8), (x + length * i / 4, y + 8)], w=2.4, col=INK, amp=0.2)
    pen.text((x + length / 2, y - 26), label, size=30, col=GREY, halo=False)


def cartouche(pen, title, sub):
    pen.rect(60, 60, 60 + 28 * len(title) * 0.62 + 120, 150, fill=PARCH, outline=INK, w=3, amp=0.7)
    pen.rect(68, 68, 52 + 28 * len(title) * 0.62 + 120, 142, outline=GOLD, w=1.4, amp=0.5)
    pen.text((60 + (28 * len(title) * 0.62 + 120) / 2, 94), title, size=46, col=RED, halo=False)
    pen.text((60 + (28 * len(title) * 0.62 + 120) / 2, 128), sub, size=26, col=GREY, halo=False)


def star_door(pen, x, y, horizontal=True, lm=True):
    w, h = (46, 16) if horizontal else (16, 46)
    pen.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill=(70, 62, 58), outline=INK, w=2)
    r = 7
    pts = [(x + (r if i % 2 == 0 else r * 0.4) * math.sin(math.pi * i / 4),
            y - (r if i % 2 == 0 else r * 0.4) * math.cos(math.pi * i / 4)) for i in range(8)]
    pen.d.polygon([sc(p) for p in pts], fill=(236, 226, 190))


def stairs(pen, x0, y0, x1, y1, steps=9, width=70):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    for i in range(steps + 1):
        t = i / steps
        cx, cy = x0 + dx * t, y0 + dy * t
        pen.line([(cx - nx * width / 2, cy - ny * width / 2), (cx + nx * width / 2, cy + ny * width / 2)],
                 w=2, col=INK, amp=0.5)


def waves(pen, x0, y0, x1, y1, rows=4, col=WATER, seed=1):
    r = random.Random(seed)
    layer = Image.new("RGBA", pen.img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for j in range(rows):
        y = y0 + (y1 - y0) * (j + 0.5) / rows
        x = x0 + r.uniform(0, 30)
        while x < x1 - 40:
            ln = r.uniform(34, 70)
            pts = []
            for k in range(13):
                t = k / 12
                pts.append(sc((x + ln * t, y + math.sin(t * 6.28) * 5)))
            ld.line(pts, fill=col + (200,), width=int(2.4 * S))
            x += ln + r.uniform(18, 46)
    pen.img.paste(layer, (0, 0), layer)


def anvil(pen, x, y):
    pen.d.polygon([sc(p) for p in [(x - 20, y - 8), (x + 22, y - 8), (x + 12, y), (x + 8, y + 10), (x - 8, y + 10),
                                    (x - 12, y), (x - 20, y)]], fill=(90, 82, 76), outline=INK)


def forge(pen, x, y):
    pen.rect(x - 24, y - 20, x + 24, y + 20, fill=(120, 108, 98), outline=INK, w=2.4)
    pen.d.polygon([sc(p) for p in [(x, y - 14), (x + 9, y), (x + 4, y + 11), (x - 4, y + 11), (x - 9, y)]], fill=(184, 98, 52))


def bed(pen, x, y, vertical=True):
    w, h = (26, 54) if vertical else (54, 26)
    pen.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill=(222, 208, 176), outline=INK, w=1.8, amp=0.4)
    if vertical:
        pen.rect(x - w / 2 + 3, y - h / 2 + 3, x + w / 2 - 3, y - h / 2 + 15, fill=(240, 232, 208), outline=INK, w=1.2, amp=0.2)
    else:
        pen.rect(x - w / 2 + 3, y - h / 2 + 3, x - w / 2 + 15, y + h / 2 - 3, fill=(240, 232, 208), outline=INK, w=1.2, amp=0.2)


def nugget(pen, x, y, s=1.0):
    r = 9 * s
    pts = [(x - r, y + r * .4), (x - r * .5, y - r * .6), (x + r * .4, y - r * .8), (x + r, y), (x + r * .3, y + r * .7)]
    pen.d.polygon([sc(p) for p in pts], fill=(58, 54, 58), outline=INK)
    pen.d.line([sc((x - r * .3, y - r * .3)), sc((x + r * .2, y - r * .5))], fill=(190, 198, 215), width=S)


def rubble(pen, x, y, n=10, spread=22):
    for _ in range(n):
        px, py = x + pen.r.uniform(-spread, spread), y + pen.r.uniform(-spread * .7, spread * .7)
        r = pen.r.uniform(3, 7)
        pen.d.ellipse([sc((px - r, py - r * .7)), sc((px + r, py + r * .7))], fill=STONE, outline=INK)


def mountain(pen, x, y, s=1.0):
    pts = [(x - 40 * s, y + 24 * s), (x - 8 * s, y - 34 * s), (x + 6 * s, y - 22 * s), (x + 22 * s, y - 40 * s), (x + 46 * s, y + 24 * s)]
    pen.d.polygon([sc(p) for p in pts], fill=(214, 200, 168))
    pen.line(pts, w=2.2, col=INK, amp=0.8)
    for i in range(4):
        pen.line([(x - 4 * s + i * 9 * s, y - 14 * s + i * 2 * s), (x + 6 * s + i * 9 * s, y + 18 * s)], w=1.2, col=GREY, amp=0.3)


def tree(pen, x, y, s=1.0):
    pen.line([(x, y + 14 * s), (x, y)], w=2, amp=0.2)
    pen.d.polygon([sc(p) for p in [(x, y - 24 * s), (x - 12 * s, y + 2 * s), (x + 12 * s, y + 2 * s)]], fill=(138, 140, 100), outline=INK)


def wheel_icon(pen, x, y, r=26):
    pen.circle(x, y, r, fill=(205, 192, 162), outline=INK, w=2.6)
    for a in range(0, 360, 60):
        pen.line([(x, y), (x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a)))], w=2, amp=0.2)
    pen.circle(x, y, 6, fill=INK, outline=INK, w=1)


def seat(pen, x, y, facing="e", s=1.0):
    pen.rect(x - 15 * s, y - 15 * s, x + 15 * s, y + 15 * s, fill=(205, 194, 168), outline=INK, w=1.8, amp=0.3)
    dx, dy = {"e": (7, 0), "w": (-7, 0), "n": (0, -7), "s": (0, 7)}[facing]
    pen.circle(x + dx * s, y + dy * s, 5 * s, fill=(240, 232, 210), outline=INK, w=1.2)



# Side tunnels that collapsed a few paces in: they make every room feel part of something bigger.
def add_stubs(plan, stubs):
    """stubs: list of ([points], width). Call before plan.paint()."""
    for pts, w in stubs:
        plan.corridor(pts, w)


def draw_stubs(pen, stubs):
    """Rubble at the end of every stub. Call after the Pen exists."""
    for pts, w in stubs:
        x, y = pts[-1]
        rubble(pen, x, y, 16, w * 0.55)


# ================================================================ map specs
# Each map function draws one map and returns the finished image. lm=True draws the Loremaster
# version (numbered markers, secrets in red), lm=False the player version (layout only).
# Register the map in MAPS and in src/maps.toml, then run: python3 tools/maps.py <id>

def map_example(lm):
    seed = 7
    bg = parchment(seed)
    plan = Plan(seed)
    plan.rect(300, 400, 700, 700)                      # a room
    plan.corridor([(700, 550), (900, 550)], 60)        # a corridor
    plan.rect(900, 420, 1300, 700)                     # a second room
    plan.corridor([(500, 400), (500, 220)], 60)        # a stair going up
    stubs = [([(300, 600), (210, 600)], 34), ([(1100, 700), (1100, 790)], 34)]
    add_stubs(plan, stubs)
    plan.paint(bg)
    pen = Pen(bg, seed)
    draw_stubs(pen, stubs)
    frame(pen)
    stairs(pen, 500, 240, 500, 390, steps=8, width=70)
    star_door(pen, 800, 550, horizontal=False)
    anvil(pen, 450, 560)
    forge(pen, 600, 470)
    for i in range(4):
        bed(pen, 960 + i * 70, 500, True)
    nugget(pen, 1200, 640)
    pen.text((500, 640), "First Room", size=44)
    pen.text((1100, 600), "Second Room", size=44)
    cartouche(pen, "Example Map", "replace me")
    compass(pen)
    scalebar(pen, "20 paces")
    if lm:
        pen.marker((400, 500), 1)
        pen.marker((1100, 520), 2)
        pen.text((800, 480), "secret door", size=26, col=RED)
        pen.dashed([(700, 600), (900, 600)], w=3, col=RED)
    return bg


# ---------------------------------------------------------------- outdoor helpers
def chaikin(pts, n=3):
    for _ in range(n):
        out = [pts[0]]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            out += [(x0 * .75 + x1 * .25, y0 * .75 + y1 * .25), (x0 * .25 + x1 * .75, y0 * .25 + y1 * .75)]
        out.append(pts[-1])
        pts = out
    return pts


def offset_path(pts, d):
    out = []
    for i, (x, y) in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        out.append((x - dy / L * d, y + dx / L * d))
    return out


def road(pen, pts, width=22):
    pts = chaikin(pts)
    pen.d.line([sc(p) for p in pts], fill=(214, 196, 150), width=int(width * S), joint="curve")
    for d in (-width / 2, width / 2):
        pen.line(offset_path(pts, d), w=1.8, col=GREY, amp=0.8)


def mound(pen, x, y, s=1.0, fill=(220, 207, 174)):
    pts = [(x + 60 * s * math.cos(math.radians(a)), y - 28 * s * math.sin(math.radians(a))) for a in range(0, 181, 15)]
    pen.d.polygon([sc(p) for p in pts], fill=fill)
    pen.line(pts, w=2, col=INK, amp=0.6)
    for i in range(-2, 3):
        pen.line([(x + i * 14 * s, y - 20 * s * (1 - abs(i) / 3.4)), (x + i * 16 * s, y - 2 * s)], w=1.1, col=GREY, amp=0.3)


def blob(pen, pts, fill, outline=INK):
    pts = chaikin(pts, 3)
    pen.d.polygon([sc(p) for p in pts], fill=fill)
    pen.line(pts, w=2, col=outline, amp=0.8, closed=True)


def hollow(pen, x, y, s=1.0):
    pts = [(x - 7 * s * math.cos(math.radians(a)), y + 9 * s * math.sin(math.radians(a))) for a in range(-80, 81, 20)]
    pen.line(pts, w=2, col=RED, amp=0.2)


def ruin_wall(pen, pts, gaps=()):
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        if i in gaps:
            continue
        pen.line([a, b], w=5, col=INK, amp=1.0)
        pen.line([a, b], w=2.5, col=(205, 194, 168), amp=0.4)


def small_tower(pen, x, y, r=16):
    pen.circle(x, y, r, fill=(205, 194, 168), outline=INK, w=3)


def house(pen, x, y, w=60, h=38):
    pen.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill=(205, 194, 168), outline=INK, w=2.6, amp=0.5)
    pen.line([(x - w / 2, y), (x + w / 2, y)], w=1.4, col=GREY, amp=0.3)


def stream(pen, pts, width=16):
    pts = chaikin(pts)
    pen.d.line([sc(p) for p in pts], fill=(150, 176, 186), width=int(width * S), joint="curve")
    for d in (-width / 2, width / 2):
        pen.line(offset_path(pts, d), w=1.8, col=WATER, amp=0.8)


def map_fornost(lm):
    """Region overview: 1 Meile = 300 px. The battle was fought in the fields west of Fornost."""
    seed = 11
    bg = parchment(seed)
    pen = Pen(bg, seed)
    frame(pen)
    # Fornost: city hill with the ruined citadel, bank and ditch (Deadmen's Dike) south of it
    blob(pen, [(1130, 150), (1300, 110), (1460, 150), (1480, 270), (1360, 330), (1200, 330), (1120, 260)], (226, 214, 182))
    for (x0, x1) in ((1040, 1265), (1315, 1560)):
        pen.rect(x0, 428, x1, 446, fill=(196, 182, 148), outline=INK, w=2.4, amp=1.0)
        pen.line([(x0, 462), (x1, 462)], w=1.6, col=GREY, amp=2.0)
    ruin_wall(pen, [(1210, 180), (1390, 180), (1390, 280), (1210, 280), (1210, 180)], gaps=(1, 2))
    small_tower(pen, 1210, 180, 13)
    small_tower(pen, 1390, 280, 13)
    rubble(pen, 1380, 200, 12, 24)
    # Greenway from the south through the gap into the city
    road(pen, [(1100, 1190), (1180, 960), (1250, 780), (1262, 600), (1285, 480), (1296, 380), (1300, 300)], 22)
    # Wegwacht
    house(pen, 1215, 610, 52, 34)
    # barrow-field halfway between the battlefield and Fornost
    rnd = random.Random(5)
    for _ in range(13):
        mound(pen, rnd.randint(840, 1060), rnd.randint(260, 400), rnd.uniform(.4, .65))
    # the battlefield in the western fields: stream with one ford, ridge on its west bank
    stream(pen, [(690, 120), (730, 300), (690, 440), (700, 520), (690, 600), (740, 760), (720, 920), (760, 1100)], 14)
    blob(pen, [(520, 400), (590, 380), (630, 440), (632, 560), (610, 700), (560, 740), (530, 640), (515, 520)], (226, 214, 182))
    for k in range(5):
        pen.line([(540, 440 + k * 55), (572, 432 + k * 55)], w=1.2, col=GREY, amp=0.3)
    pen.rect(684, 523, 704, 543, fill=(214, 196, 150), outline=GREY, w=1.4, amp=0.3)
    # trees
    for tx, ty in ((300, 880), (360, 940), (250, 1010), (900, 980), (980, 1060), (1100, 800), (380, 300), (320, 360)):
        tree(pen, tx, ty, 1.1)
    # labels
    pen.text((1300, 70), "Fornost (Norbury of the Kings)", size=36)
    pen.text((1440, 410), "Deadmen's Dike", size=34)
    pen.text((1330, 800), "Greenway", size=32, rot=80)
    pen.text((1250, 665), "Wegwacht", size=32)
    pen.text((960, 200), "alte Hügelgräber", size=34)
    pen.text((470, 230), "die Felder", size=44, col=GREY)
    pen.text((640, 790), "Westhöhe", size=32, rot=-80)
    pen.text((775, 500), "Furt", size=30)
    pen.text((1140, 1150), "nach Bree", size=32, col=GREY)
    cartouche(pen, "Fornost und die Felder", "Nummern wie in Teil 4")
    compass(pen)
    scalebar(pen, "1 Meile", length=300)
    pen.text((680, 1170), "Entfernungen im Feld nicht maßstäblich", size=24, col=GREY, halo=False)
    if lm:
        # the forgotten path (hint H): ridge straight towards the Brandywine Bridge, crossed by the Hirtenpfad
        pen.dashed([(560, 740), (500, 900), (430, 1050), (360, 1190)], w=3)
        pen.text((420, 960), "vergessener Pfad (H)", size=26, col=RED, rot=70)
        pen.text((300, 1100), "zur Brandywine Bridge", size=24, col=RED, rot=70)
        pen.dashed([(1060, 1100), (900, 1030), (700, 960), (520, 880), (450, 760)], w=2, col=GREY, dash=8, gap=10)
        pen.text((960, 1085), "Hirtenpfad (Short Cut)", size=26, col=GREY, halo=False)
        pen.text((430, 735), "zu den Feldern", size=24, col=GREY, halo=False)
        # sight line from Fornost's hill to the ford
        pen.dashed([(1130, 270), (900, 400), (710, 520)], w=2, col=GREY, dash=8, gap=10)
        pen.text((1010, 470), "Sichtweite", size=26, col=GREY, halo=False)
        # hollows along the ridge crest and the arrows over the ford
        for k in range(10):
            hollow(pen, 610 + (k % 2) * 3, 430 + k * 24, 0.8)
        pen.arrow([(640, 450), (686, 500)], w=2, col=RED, head=9)
        pen.arrow([(640, 500), (686, 530)], w=2, col=RED, head=9)
        pen.arrow([(640, 560), (686, 540)], w=2, col=RED, head=9)
        # the little graves at the west rim of the barrow-field (hint F)
        for i in range(4):
            pen.rect(832 + i * 14, 392, 842 + i * 14, 402, fill=(205, 194, 168), outline=INK, w=1.2, amp=0.2)
            pen.rect(832 + i * 14, 408, 842 + i * 14, 418, fill=(205, 194, 168), outline=INK, w=1.2, amp=0.2)
        pen.text((850, 445), "kleine Gräber (F)", size=24, col=RED)
        for (mx, my), n, hints in (((1150, 590), 1, "E, G"), ((760, 560), 2, "B, I"), ((540, 330), 3, "A, C, (H)"),
                                    ((960, 280), 4, "F"), ((1300, 235), 5, "D")):
            pen.marker((mx, my), n)
            pen.text((mx, my + 38), hints, size=28, col=RED)
        pen.text((850, 1150), "H, J auf der Reise", size=26, col=RED)
    return bg


def map_wegwacht(lm):
    seed = 13
    bg = parchment(seed)
    plan = Plan(seed)
    plan.rect(320, 420, 780, 740)           # Wohnraum
    plan.rect(780, 500, 1020, 740)          # Vorratsraum
    plan.rect(320, 260, 560, 420)           # eingestürzter Anbau
    plan.corridor([(540, 740), (540, 960)], 60)   # Eingang und Greenway
    plan.paint(bg)
    pen = Pen(bg, seed)
    frame(pen)
    # slits in the south wall: the toll keepers watched the road
    for x in (400, 650, 900):
        pen.rect(x - 14, 734, x + 14, 746, fill=INK, outline=INK, w=1)
    pen.text((900, 780), "Schießscharten nach Süden", size=26, col=GREY, halo=False)
    # fireplace on the west wall
    pen.rect(322, 540, 372, 600, fill=(120, 108, 98), outline=INK, w=2.4)
    pen.d.polygon([sc(p) for p in [(347, 556), (358, 574), (352, 590), (342, 590), (336, 574)]], fill=(184, 98, 52))
    # bench under the window and stacked wood
    seat(pen, 650, 705, "n", 0.9)
    seat(pen, 730, 705, "n", 0.9)
    for i in range(4):
        pen.rect(440 + i * 30, 440, 466 + i * 30, 470, fill=(214, 190, 150), outline=INK, w=1.6, amp=0.3)
    pen.text((650, 600), "Wohnraum", size=44)
    pen.text((900, 620), "Nebenraum", size=40)
    pen.text((440, 340), "eingestürzter Anbau", size=34)
    rubble(pen, 480, 300, 22, 50)
    pen.text((540, 900), "Greenway", size=34, rot=90)
    cartouche(pen, "Die Wegwacht", "Ort 1 in Teil 4")
    compass(pen)
    scalebar(pen, "5 Schritt", length=200)
    if lm:
        pen.marker((600, 500), 1)
        # tally marks and verses on the east wall (hint E)
        for i in range(10):
            pen.line([(776, 560 + i * 12), (770, 560 + i * 12 + 8)], w=1.6, col=RED, amp=0.2)
        pen.text((680, 452), "geritzte Verse (E)", size=26, col=RED)
        pen.line([(762, 462), (776, 520)], w=2, col=RED)
        # toll tablet beside the door (hint G)
        pen.rect(436, 728, 496, 748, fill=(220, 190, 170), outline=RED, w=2)
        pen.text((380, 790), "Zolltafel (G)", size=26, col=RED)
    return bg


MAPS = {"example": map_example, "fornost": map_fornost, "wegwacht": map_wegwacht}


def render(name, lm):
    img = MAPS[name](lm)
    img = img.resize((W, H), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"map-{name}{'' if lm else '-players'}.jpg")
    img.save(path, quality=90, optimize=True)
    print("wrote", os.path.relpath(path, ROOT))


def main():
    names = sys.argv[1:] or list(MAPS)
    for n in names:
        for lm in (True, False):
            render(n, lm)


if __name__ == "__main__":
    main()
