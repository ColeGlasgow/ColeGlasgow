#!/usr/bin/env python3
"""Build the pixel-art SVG assets for the profile README.

One dark trainer card sized to the profile column (846 px), short enough to
read without scrolling: a night scene with Cole and his Gengar, the trainer
rows, two Pokedex entries, the stack as badges and a typewriter dialogue
line. Plus the link buttons that sit under it.

Text is rasterized from Press Start 2P into shared SVG glyph defs at build
time, so nothing depends on fonts loading at view time; all animation is
plain CSS transform/opacity that survives GitHub's image proxy.
"""

import base64
import io
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "src")
OUT = os.path.join(ROOT, "assets")

# ---- palette
CARD_BG = "#16161e"      # card panel
CARD_BD = "#c8a040"      # gold border
GOLD = "#e8c048"         # section titles
SUB = "#8890a8"          # muted label text
VAL = "#f0f0f4"          # value text
INNER_BG = "#20202c"     # inset sprite/portrait box
INNER_BD = "#3a3a48"
RED = "#e04838"
RULE_D = "#3a3a48"

TYPE_COLORS = {
    "GRASS": ("#78c850", "#ffffff"),
    "ELECTRIC": ("#f8d030", "#605010"),
    "WATER": ("#6890f0", "#ffffff"),
    "STEEL": ("#b8b8d0", "#404058"),
}

FONT = ImageFont.truetype(os.path.join(SRC, "PressStart2P.ttf"), 8)

_glyph_cache = {}


def glyph_runs(ch):
    """Rasterize one Press Start 2P glyph to horizontal pixel runs on an 8x8 grid."""
    if ch in _glyph_cache:
        return _glyph_cache[ch]
    img = Image.new("L", (16, 16), 0)
    ImageDraw.Draw(img).text((0, 0), ch, font=FONT, fill=255)
    px_ = img.load()
    runs = []
    for y in range(16):
        x = 0
        while x < 16:
            if px_[x, y] >= 128:
                x0 = x
                while x < 16 and px_[x, y] >= 128:
                    x += 1
                runs.append((x0, y, x - x0))
            else:
                x += 1
    _glyph_cache[ch] = runs
    return runs


def fnum(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


class Doc:
    def __init__(self, w, h, ns=""):
        self.w, self.h = w, h
        self.ns = ns
        self.body = []
        self.css = []
        self.defs = []
        self.glyphs = {}

    def add(self, s):
        self.body.append(s)

    def rect(self, x, y, w, h, fill, cls=None, extra=""):
        c = f' class="{cls}"' if cls else ""
        self.add(
            f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" fill="{fill}"{c}{extra}/>'
        )

    def _glyph(self, ch):
        if ch not in self.glyphs:
            gid = f"c{ord(ch):x}"
            body = "".join(
                f'<rect x="{x}" y="{y}" width="{w}" height="1"/>' for x, y, w in glyph_runs(ch)
            )
            self.glyphs[ch] = (gid, f'<g id="{gid}">{body}</g>')
        return self.glyphs[ch][0]

    def text(self, x, y, s, scale=1, fill=VAL, cls=None):
        """Place a text run; (x, y) is the top-left corner in final units."""
        uses = []
        cx = 0
        for ch in s:
            if ch != " ":
                gid = self._glyph(ch)
                uses.append(f'<use href="#{gid}" xlink:href="#{gid}" x="{cx}"/>')
            cx += 8
        c = f' class="{cls}"' if cls else ""
        self.add(
            f'<g transform="translate({fnum(x)},{fnum(y)}) scale({fnum(scale)})" fill="{fill}"{c}>{"".join(uses)}</g>'
        )
        return len(s) * 8 * scale

    def tri_right(self, x, y, s, fill=VAL, cls=None):
        c = f' class="{cls}"' if cls else ""
        rows = [1, 2, 3, 4, 3, 2, 1]
        body = "".join(
            f'<rect x="0" y="{i}" width="{w}" height="1"/>' for i, w in enumerate(rows)
        )
        self.add(f'<g transform="translate({fnum(x)},{fnum(y)}) scale({fnum(s)})" fill="{fill}"{c}>{body}</g>')

    def tri_down(self, x, y, s, fill=VAL, cls=None):
        c = f' class="{cls}"' if cls else ""
        rows = [(0, 7), (1, 5), (2, 3), (3, 1)]
        body = "".join(
            f'<rect x="{3 - w // 2}" y="{i}" width="{w}" height="1"/>' for i, w in rows
        )
        self.add(f'<g transform="translate({fnum(x)},{fnum(y)}) scale({fnum(s)})" fill="{fill}"{c}>{body}</g>')

    def grad(self, gid, c1, c2, vertical=True):
        gid = f"{self.ns}{gid}"
        x2, y2 = ("0", "1") if vertical else ("1", "0")
        self.defs.append(
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>'
        )
        return f"url(#{gid})"

    def save(self, name, crisp=True):
        defs = "".join(d for _, d in self.glyphs.values()) + "".join(self.defs)
        css = "".join(self.css)
        attr = ' shape-rendering="crispEdges"' if crisp else ""
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}"{attr}>'
            f"<style>{css}</style><defs>{defs}</defs>{''.join(self.body)}</svg>"
        )
        path = os.path.join(OUT, name)
        with open(path, "w") as f:
            f.write(svg)
        print(f"  {name}  ({len(svg) // 1024} KB)")


# ---------------------------------------------------------------- helpers


def px(doc, s, x, y, w, h, fill, cls=None):
    doc.rect(x * s, y * s, w * s, h * s, fill, cls=cls)


CORNER = [3, 2, 1, 1]


def rpath(s, x, y, w, h, corner=CORNER):
    """Pixel-rounded rectangle as one path (multi-subpath, one per row)."""
    n = len(corner)
    parts = []
    for iy in range(h):
        if iy < n:
            inset = corner[iy]
        elif h - 1 - iy < n:
            inset = corner[h - 1 - iy]
        else:
            inset = 0
        parts.append(
            f"M{fnum((x + inset) * s)} {fnum((y + iy) * s)}h{fnum((w - 2 * inset) * s)}v{fnum(s)}h-{fnum((w - 2 * inset) * s)}z"
        )
    return "".join(parts)


def rbox(doc, s, x, y, w, h, fill, border=None, b=2, cls=None):
    """D/P-style rounded panel: optional border color + fill (may be a gradient url)."""
    c = f' class="{cls}"' if cls else ""
    if border:
        doc.add(f'<path d="{rpath(s, x, y, w, h)}" fill="{border}"{c}/>')
        doc.add(f'<path d="{rpath(s, x + b, y + b, w - 2 * b, h - 2 * b)}" fill="{fill}"/>')
    else:
        doc.add(f'<path d="{rpath(s, x, y, w, h)}" fill="{fill}"{c}/>')


def blit_map(doc, s, x, y, art, colors):
    for j, row in enumerate(art):
        i = 0
        while i < len(row):
            ch = row[i]
            if ch in colors:
                i0 = i
                while i < len(row) and row[i] == ch:
                    i += 1
                px(doc, s, x + i0, y + j, i - i0, 1, colors[ch])
            else:
                i += 1


# ---------------------------------------------------------------- sprites


def load_sprite(path):
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def b64uri(im, upscale=6):
    im = im.resize((im.width * upscale, im.height * upscale), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def image_tag(uri, x, y, w, h, cls=None):
    c = f' class="{cls}"' if cls else ""
    return (
        f'<image x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
        f'href="{uri}" xlink:href="{uri}" preserveAspectRatio="none" '
        f'style="image-rendering:pixelated"{c}/>'
    )


# ---------------------------------------------------------------- pixel art

GEAR = [
    "....#..#....",
    ".#..####..#.",
    ".##########.",
    "..########..",
    ".###+++###..",
    "####+--+####",
    "####+--+####",
    ".###+++###..",
    "..########..",
    ".##########.",
    ".#..####..#.",
    "....#..#....",
]

TERMINAL = [
    "############",
    "#----------#",
    "#-#--------#",
    "#--#-------#",
    "#-#--------#",
    "#----------#",
    "#---####---#",
    "#----------#",
    "#----------#",
    "############",
    "............",
    "............",
]

def shape_badge(pred, n=12):
    grid = [[pred(x, y) for x in range(n)] for y in range(n)]
    art = []
    for y in range(n):
        row = ""
        for x in range(n):
            if not grid[y][x]:
                row += "."
                continue
            edge = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= n or ny >= n or not grid[ny][nx]:
                    edge = True
            row += "#" if edge else "+"
        art.append(row)
    return art


BADGE_CIRCLE = shape_badge(lambda x, y: (x - 5.5) ** 2 + (y - 5.5) ** 2 <= 30)
BADGE_DIAMOND = shape_badge(lambda x, y: abs(x - 5.5) + abs(y - 5.5) <= 5.5)
BADGE_TRIANGLE = shape_badge(lambda x, y: y >= 2 and abs(x - 5.5) <= (y - 1) * 0.55)
BADGE_HEX = shape_badge(lambda x, y: abs(x - 5.5) <= 5.5 - abs(y - 5.5) * 0.5 and 0 <= y < 12)


GENGAR = load_sprite(os.path.join(SRC, "gengar-dp.png"))    # 58x53
COLE = load_sprite(os.path.join(SRC, "volkner.png"))        # 38x78

# ---------------------------------------------------------------- card

S = 2
W, H = 423, 218           # 846 x 436: the profile README column is 846 px wide
SCENE = (12, 35, 160, 144)
X1, XR = 184, 411         # right column

BLINK = "@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}.blink{animation:blink 1.1s steps(1,end) infinite}"

ROWS = [("NAME", "COLE"), ("JOB", "FULL-STACK SOFTWARE ENGINEER")]

DEX = [
    ("No.001", "HAYWIRE", ["GRASS", "ELECTRIC"], "Hay market intelligence."),
    ("No.002", "WELLMARK", ["WATER", "STEEL"], "Software engineer."),
]

BADGES = [
    (GEAR, "CI/CD", "#88a0b8", "#40506a"),
    (BADGE_CIRCLE, "PYTHON", "#e0b84c", "#806020"),
    (BADGE_HEX, "JAVASCRIPT", "#78c8b0", "#2a6a58"),
    (BADGE_TRIANGLE, "AWS", "#c08850", "#6a4420"),
    (TERMINAL, "GIT", "#404a58", "#40d060"),
    (BADGE_DIAMOND, "POSTGRES", "#c0c8d0", "#606870"),
]
BADGE_COLS = (0, 72, 151)  # JAVASCRIPT needs the wide last column

PHASES = [
    (5.5, "Cole is a full-stack software engineer at Wellmark."),
    (5.5, "He also builds HayWire, a weekly hay-price newsletter."),
    (5.0, "I get $1 Caseys coffee every morning :)."),
]

STARS = [(152, 12), (136, 34), (148, 62), (118, 18), (100, 8), (76, 16), (56, 10), (10, 14),
         (6, 40), (154, 90), (28, 24), (140, 6), (110, 44), (14, 78), (128, 52)]


def blob(doc, s, cx, cy, rx, ry, fill):
    """Pixel ellipse, one run per row, so curves sit on the same grid as the sprites."""
    parts = []
    for j in range(-ry, ry):
        half = round(rx * (1 - ((j + 0.5) / ry) ** 2) ** 0.5)
        if half:
            parts.append(f"M{fnum((cx - half) * s)} {fnum((cy + j) * s)}h{fnum(2 * half * s)}v{fnum(s)}h-{fnum(2 * half * s)}z")
    doc.add(f'<path d="{"".join(parts)}" fill="{fill}"/>')


def night_scene(d, s, x0, y0, w, h):
    """Gengar and Cole side by side on a battle platform under a rising moon."""
    d.defs.append(f'<clipPath id="{d.ns}scene"><path d="{rpath(s, 0, 0, w, h)}"/></clipPath>')
    d.add(f'<path d="{rpath(s, x0 - 1, y0 - 1, w + 2, h + 2)}" fill="{INNER_BD}"/>')
    d.add(f'<g transform="translate({x0 * s},{y0 * s})" clip-path="url(#{d.ns}scene)">')
    d.rect(0, 0, w * s, h * s, d.grad("sky", "#0a0c20", "#3a2c68"))

    d.css.append(
        "@keyframes twk{0%,60%{opacity:1}61%,90%{opacity:.2}91%,100%{opacity:1}}"
        ".tw0{animation:twk 3.1s steps(1,end) infinite}"
        ".tw1{animation:twk 4.3s steps(1,end) infinite;animation-delay:-1.7s}"
    )
    for i, (sx, sy) in enumerate(STARS):
        cls = (None, "tw0", "tw1")[i % 3]
        px(d, s, sx, sy, 1, 1, "#e8eaff" if cls else "#7c82b8", cls=cls)

    mx, my, mr = 68, 68, 30
    blob(d, s, mx, my, mr + 8, mr + 8, "rgba(240,236,208,.05)")
    blob(d, s, mx, my, mr + 4, mr + 4, "rgba(240,236,208,.08)")
    blob(d, s, mx, my, mr, mr, "#f0ecd0")
    for cx, cy, r in ((12, -10, 5), (-9, -16, 3), (-15, 0, 5), (18, 6, 2)):
        blob(d, s, mx + cx, my + cy, r, r, "#dcd6b6")

    blob(d, s, 28, 122, 84, 22, "#1a1b40")
    blob(d, s, 146, 126, 70, 20, "#141634")
    d.rect(0, 118 * s, w * s, (h - 118) * s, "#101228")
    blob(d, s, 82, 130, 70, 12, "#17403c")
    blob(d, s, 82, 129, 62, 9, "#1f5248")

    blob(d, s, 111, 131, 15, 3, "rgba(0,0,0,.35)")
    d.add(image_tag(b64uri(COLE), 86 * s, (132 - COLE.height) * s, COLE.width * s, COLE.height * s))
    blob(d, s, 69, 136, 24, 4, "rgba(0,0,0,.35)")
    d.css.append(
        f"@keyframes bob{{0%,49.9%{{transform:translateY(0)}}50%,100%{{transform:translateY(-{s}px)}}}}"
        ".bob{animation:bob 1.6s steps(1,end) infinite}"
    )
    d.add(f'<g class="bob">{image_tag(b64uri(GENGAR), 40 * s, (137 - GENGAR.height) * s, GENGAR.width * s, GENGAR.height * s)}</g>')
    d.add("</g>")


def type_chips(doc, s, xr, y, types):
    """Type badges, right-aligned to xr."""
    x = xr - sum(len(t) * 6 + 12 for t in types) - 4 * (len(types) - 1)
    for t in types:
        cbg, ctx = TYPE_COLORS[t]
        w = len(t) * 6 + 12
        rbox(doc, s, x, y, w, 12, cbg)
        doc.text((x + 6) * s, (y + 3) * s, t, scale=s * 0.75, fill=ctx)
        x += w + 4


def dialogue(d, s, phases, box, bg):
    """One-line typewriter dialogue: each phase types out, holds, then clears."""
    bx, by, bw, bh = box
    tx, ty = bx + 10, by + (bh - 6) // 2
    cycle = sum(dur for dur, _ in phases)
    pct = lambda t: fnum(t / cycle * 100)
    rbox(d, s, bx, by, bw, bh, bg, border=INNER_BD, b=1)
    d.css.append(BLINK)
    t0 = 0.0
    for i, (dur, line) in enumerate(phases):
        t1, n = t0 + dur, len(line)
        assert tx + n * 6 <= bx + bw - 18, f"dialogue line too long: {line}"
        ts = t0 + 0.3
        te = ts + n * 0.033
        d.css.append(
            f".ph{i}{{opacity:0;animation:ph{i} {fnum(cycle)}s linear infinite}}"
            f"@keyframes ph{i}{{0%,{pct(t0)}%{{opacity:0}}"
            f"{pct(t0 + 0.02)}%,{pct(t1 - 0.02)}%{{opacity:1}}{pct(t1)}%,100%{{opacity:0}}}}"
            f".tp{i}{{transform-box:fill-box;transform-origin:100% 50%;animation:tp{i} {fnum(cycle)}s linear infinite}}"
            f"@keyframes tp{i}{{0%{{transform:scaleX(1)}}"
            f"{pct(ts)}%{{transform:scaleX(1);animation-timing-function:steps({n},end)}}"
            f"{pct(te)}%,100%{{transform:scaleX(0)}}}}"
        )
        d.add(f'<g class="ph{i}">')
        d.text(tx * s, ty * s, line, scale=s * 0.75)
        d.rect(tx * s, (ty - 1) * s, (n * 6 + 2) * s, 8.5 * s, bg, cls=f"tp{i}")
        d.add("</g>")
        t0 = t1
    d.tri_down((bx + bw - 14) * s, (by + bh - 10) * s, s * 0.9, fill=RED, cls="blink")


def build_card():
    d = Doc(W * S, H * S, ns="card_")
    rbox(d, S, 0, 0, W, H, CARD_BG, border=CARD_BD, b=2)
    d.defs.append(f'<clipPath id="card_in"><path d="{rpath(S, 2, 2, W - 4, H - 4)}"/></clipPath>')

    d.text(14 * S, 11 * S, "TRAINER CARD", scale=S, fill=GOLD)
    d.text(126 * S, 13 * S, "IDNo.00094", scale=S * 0.75, fill=SUB)
    px(d, S, 10, 28, W - 20, 1, CARD_BD)
    for x, y, c in ((W - 80, 40, "#b02838"), (W - 58, 30, "#d84048")):  # red corner sweep
        d.add(f'<path d="M{x * S} {2 * S}H{(W - 2) * S}V{y * S}Z" fill="{c}" clip-path="url(#card_in)"/>')

    night_scene(d, S, *SCENE)

    y = 39
    for label, value in ROWS:
        d.text(X1 * S, y * S, label, scale=S * 0.75, fill=SUB)
        d.text((X1 + 42) * S, y * S, value, scale=S * 0.75)
        y += 14

    px(d, S, X1, 68, XR - X1, 1, RULE_D)
    d.text(X1 * S, 75 * S, "POKéDEX", scale=S * 0.75, fill=GOLD)
    y = 90
    for no, name, types, line in DEX:
        assert len(line) * 6 <= XR - X1, f"dex line too long: {line}"
        d.text(X1 * S, y * S, no, scale=S * 0.75, fill=SUB)
        d.text((X1 + 42) * S, y * S, name, scale=S * 0.75)
        type_chips(d, S, XR, y - 3, types)
        d.text(X1 * S, (y + 12) * S, line, scale=S * 0.75, fill=SUB)
        y += 29

    px(d, S, X1, 144, XR - X1, 1, RULE_D)
    for i, (art, label, fill_c, edge_c) in enumerate(BADGES):
        bx, by = X1 + BADGE_COLS[i % 3], 151 + (i // 3) * 15
        if art is TERMINAL:
            blit_map(d, S, bx, by, art, {"#": fill_c, "-": "#181c24"})
            for ox, oy, ow in ((2, 2, 1), (3, 3, 1), (2, 4, 1), (4, 6, 4)):  # prompt
                px(d, S, bx + ox, by + oy, ow, 1, edge_c)
        else:
            blit_map(d, S, bx, by, art, {"#": edge_c, "+": fill_c, "-": fill_c})
        assert bx + 16 + len(label) * 6 <= XR, f"badge label too long: {label}"
        d.text((bx + 16) * S, (by + 3) * S, label, scale=S * 0.75)

    dialogue(d, S, PHASES, (12, 186, W - 24, 24), INNER_BG)
    d.save("card.svg")


def build_link(name, label):
    w = len(label) * 8 + 38
    d = Doc(w * S, 24 * S)
    rbox(d, S, 0, 0, w, 24, CARD_BG, border=CARD_BD, b=2)
    d.css.append(BLINK)
    d.tri_right(12 * S, 9 * S, S * 0.875, fill=GOLD, cls="blink")
    d.text(24 * S, 8 * S, label, scale=S)
    d.save(f"btn-{name}.svg")


def main():
    print("building assets:")
    build_card()
    build_link("site", "HAYWIREAG.COM")
    build_link("email", "EMAIL")
    print("done.")


if __name__ == "__main__":
    main()
