#!/usr/bin/env python3
"""Build the pixel-art SVG assets for the profile README.

Everything is drawn on an authentic Game Boy (DMG-01) grid in the four-shade
green palette. Text is rasterized from Press Start 2P into shared SVG glyph
defs at build time, so nothing depends on fonts loading at view time, and all
animation is plain CSS transform/opacity — safe inside GitHub's image proxy.
"""

import base64
import io
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "src")
OUT = os.path.join(ROOT, "assets")

# DMG palette
G0 = "#0f380f"  # darkest
G1 = "#306230"
G2 = "#8bac0f"
G3 = "#9bbc0f"  # lightest / screen background
PALETTE = [(15, 56, 15, 255), (48, 98, 48, 255), (139, 172, 15, 255), (155, 188, 15, 255)]

# console shell
SHELL = "#4d4956"
SHELL_D = "#39363f"
SHELL_L = "#5f5b6a"
INK = "#c9c6bf"
STRIPE_M = "#8b3a62"
STRIPE_N = "#3f3f7a"
LED = "#e8404a"

FONT = ImageFont.truetype(os.path.join(SRC, "PressStart2P.ttf"), 8)

_glyph_cache = {}


def glyph_runs(ch):
    """Rasterize one Press Start 2P glyph to horizontal pixel runs on an 8x8 grid."""
    if ch in _glyph_cache:
        return _glyph_cache[ch]
    img = Image.new("L", (16, 16), 0)
    ImageDraw.Draw(img).text((0, 0), ch, font=FONT, fill=255)
    px = img.load()
    runs = []
    for y in range(16):
        x = 0
        while x < 16:
            if px[x, y] >= 128:
                x0 = x
                while x < 16 and px[x, y] >= 128:
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
    def __init__(self, w, h):
        self.w, self.h = w, h
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

    def text(self, x, y, s, scale=1, fill=G0, cls=None):
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

    def tri_right(self, x, y, s, fill=G0, cls=None):
        """Right-pointing menu cursor, 4px tall half then mirrored (7 rows)."""
        c = f' class="{cls}"' if cls else ""
        rows = [1, 2, 3, 4, 3, 2, 1]
        body = "".join(
            f'<rect x="0" y="{i}" width="{w}" height="1"/>' for i, w in enumerate(rows)
        )
        self.add(f'<g transform="translate({fnum(x)},{fnum(y)}) scale({fnum(s)})" fill="{fill}"{c}>{body}</g>')

    def tri_down(self, x, y, s, fill=G0, cls=None):
        c = f' class="{cls}"' if cls else ""
        rows = [(0, 7), (1, 5), (2, 3), (3, 1)]
        body = "".join(
            f'<rect x="{3 - w // 2}" y="{i}" width="{w}" height="1"/>' for i, w in rows
        )
        self.add(f'<g transform="translate({fnum(x)},{fnum(y)}) scale({fnum(s)})" fill="{fill}"{c}>{body}</g>')

    def save(self, name):
        defs = "".join(d for _, d in self.glyphs.values()) + "".join(self.defs)
        css = "".join(self.css)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" shape-rendering="crispEdges">'
            f"<style>{css}</style><defs>{defs}</defs>{''.join(self.body)}</svg>"
        )
        path = os.path.join(OUT, name)
        with open(path, "w") as f:
            f.write(svg)
        print(f"  {name}  ({len(svg) // 1024} KB)")


# ---------------------------------------------------------------- pixel helpers


def px(doc, s, x, y, w, h, fill, cls=None):
    doc.rect(x * s, y * s, w * s, h * s, fill, cls=cls)


def dbox(doc, s, x, y, w, h, fg=G0, bg=G3):
    """Gen-1 style double-bordered dialogue box, logical units."""
    px(doc, s, x, y, w, h, bg)
    # outer line (with notched corners for the rounded look)
    px(doc, s, x + 2, y, w - 4, 2, fg)
    px(doc, s, x + 2, y + h - 2, w - 4, 2, fg)
    px(doc, s, x, y + 2, 2, h - 4, fg)
    px(doc, s, x + w - 2, y + 2, 2, h - 4, fg)
    px(doc, s, x + 1, y + 1, 1, 1, fg)
    px(doc, s, x + w - 2, y + 1, 1, 1, fg)
    px(doc, s, x + 1, y + h - 2, 1, 1, fg)
    px(doc, s, x + w - 2, y + h - 2, 1, 1, fg)
    # inner hairline
    px(doc, s, x + 4, y + 3, w - 8, 1, fg)
    px(doc, s, x + 4, y + h - 4, w - 8, 1, fg)
    px(doc, s, x + 3, y + 4, 1, h - 8, fg)
    px(doc, s, x + w - 4, y + 4, 1, h - 8, fg)


def hpbar(doc, s, x, y, w, frac=1.0, cls=None):
    """HP container + fill, logical units, 5px tall."""
    px(doc, s, x, y, w, 5, G0)
    px(doc, s, x + 1, y + 1, w - 2, 3, G3)
    fill_w = max(1, round((w - 2) * frac))
    px(doc, s, x + 1, y + 1, fill_w, 3, G1, cls=cls)


def blit_map(doc, s, x, y, art, colors=None):
    colors = colors or {"#": G0, "o": G1, "+": G2, "-": G3}
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


def to_dmg(path, drop_white=False):
    im = Image.open(path).convert("RGBA")
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    src = im.load()
    dst = out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = src[x, y]
            if a < 128:
                continue
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if drop_white and lum > 235:
                continue
            idx = 0 if lum < 64 else 1 if lum < 140 else 2 if lum < 215 else 3
            dst[x, y] = PALETTE[idx]
    bbox = out.getbbox()
    return out.crop(bbox) if bbox else out


def silhouette(path, color=(15, 56, 15, 255)):
    im = Image.open(path).convert("RGBA")
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    src = im.load()
    dst = out.load()
    for y in range(im.height):
        for x in range(im.width):
            if src[x, y][3] >= 128:
                dst[x, y] = color
    bbox = out.getbbox()
    return out.crop(bbox) if bbox else out


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


GENGAR = to_dmg(os.path.join(SRC, "gengar-front.png"))
PIKACHU_BACK = to_dmg(os.path.join(SRC, "pikachu-back.png"), drop_white=True)
GENGAR_SHADOW = silhouette(os.path.join(SRC, "gengar-front.png"))
GENGAR_URI = b64uri(GENGAR)
PIKA_URI = b64uri(PIKACHU_BACK)
GENGAR_SHADOW_URI = b64uri(GENGAR_SHADOW)

# ---------------------------------------------------------------- pixel art

POKEBALL = [
    "....####....",
    "..##++++##..",
    ".#++++++++#.",
    ".#++++--++#.",
    "#+++++--+++#",
    "#++++++++++#",
    "############",
    "#oooo##oooo#",
    ".#oo#--#oo#.",
    ".#oo#--#oo#.",
    "..##o##o##..",
    "....####....",
]

WHEAT = [
    "......#.....",
    "...#..#..#..",
    "...#.###.#..",
    "....#####...",
    ".....###....",
    "...#..#..#..",
    "...#.###.#..",
    "....#####...",
    ".....###....",
    "......#.....",
    "......#.....",
    "......#.....",
]

ROBOT = [
    "....####....",
    "...######...",
    "...#o##o#...",
    "...######...",
    "....####....",
    "..########..",
    ".#.######.#.",
    ".#.######.#.",
    "...######...",
    "...##..##...",
    "...##..##...",
    "..###..###..",
]

GRASS = [
    ".#...#....#...#.",
    ".#.#.#..#.#.#.#.",
    ".#.#.#..#.#.#.#.",
    ".###.#..#.###.#.",
    "..##.##.#.##.##.",
    "..#####.#.#####.",
    "...###..#..###..",
    "....#...#...#...",
]

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

STAR = [
    ".....##.....",
    ".....##.....",
    "....#++#....",
    "####+++#####",
    "#++++++++++#",
    ".##++++++##.",
    "...#++++#...",
    "...#++++#...",
    "..#++##++#..",
    "..#+#..#+#..",
    ".##......##.",
    "............",
]


def shape_badge(pred, n=12):
    """Build a 12x12 map from a predicate: border where edge, fill inside."""
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
BADGE_SQUARE = shape_badge(lambda x, y: 1 <= x <= 10 and 1 <= y <= 10)

# terminal badge: square with a prompt caret inside
BASH_BADGE = [
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


# ---------------------------------------------------------------- assets


def build_hero():
    S = 3  # screen pixel scale
    SX, SY = 72, 46  # screen origin
    SW, SH = 160 * S, 144 * S
    W, H = SX + SW + 30, SY + SH + 40
    d = Doc(W, H)

    # ---- console bezel
    d.rect(0, 0, W, H, SHELL_D, extra=' rx="18"')
    d.rect(2, 2, W - 4, H - 4, SHELL, extra=' rx="16"')
    # pinstripes across the top
    d.rect(16, 16, W - 32, 3, STRIPE_M)
    d.rect(16, 23, W - 32, 3, STRIPE_N)
    label = "DOT MATRIX WITH STEREO SOUND"
    lw = len(label) * 8 * 0.75
    d.rect((W - lw) / 2 - 10, 12, lw + 20, 18, SHELL)
    d.text((W - lw) / 2, 18, label, scale=0.75, fill=INK)
    # battery LED
    d.defs.append(
        '<filter id="ledglow" x="-120%" y="-120%" width="340%" height="340%">'
        '<feGaussianBlur stdDeviation="5"/></filter>'
    )
    d.css.append(
        "@keyframes led{0%,100%{opacity:.45}50%{opacity:1}}"
        ".led{animation:led 2.6s ease-in-out infinite}"
    )
    d.add(f'<circle cx="38" cy="{SY + 96}" r="9" fill="{LED}" opacity=".5" filter="url(#ledglow)" class="led"/>')
    d.add(f'<circle cx="38" cy="{SY + 96}" r="4" fill="{LED}"/>')
    d.text(38 - 3.5 * 8 * 0.5, SY + 112, "BATTERY", scale=0.5, fill=INK)
    # branding under the screen
    brand = "COLE BOY"
    bw = len(brand) * 8 * 1
    d.text((SX + SW / 2) - bw / 2 - 8, SY + SH + 14, brand, scale=1, fill=INK)
    d.text((SX + SW / 2) + bw / 2 + 4, SY + SH + 12, "TM", scale=0.4, fill=INK)
    # screen frame + screen
    d.rect(SX - 6, SY - 6, SW + 12, SH + 12, "#23212a", extra=' rx="4"')
    d.rect(SX, SY, SW, SH, G3)

    # ---- screen content group
    d.add(f'<g transform="translate({SX},{SY})">')
    s = S

    # enemy (wild COLE) stat box, top-left
    d.text(8 * s, 6 * s, "COLE", scale=s, fill=G0)
    d.text(48 * s, 6 * s, ":L28", scale=s, fill=G0)
    d.text(8 * s, 17 * s, "HP", scale=s, fill=G0)
    hpbar(d, s, 26, 18, 62, 1.0)
    px(d, s, 6, 26, 88, 1, G0)
    px(d, s, 93, 23, 1, 3, G0)

    # gengar, top-right (idle bob)
    d.css.append(
        "@keyframes bob{0%,49.9%{transform:translateY(0)}50%,100%{transform:translateY(-2px)}}"
        f".bob{{animation:bob 1.4s steps(1,end) infinite}}"
    )
    gw, gh = GENGAR.width, GENGAR.height  # ~47x47
    d.add(f'<g class="bob">{image_tag(GENGAR_URI, (150 - gw) * s, 5 * s, gw * s, gh * s)}</g>')

    # player (YOU) stat box, bottom-right of field
    d.text(76 * s, 58 * s, "YOU", scale=s, fill=G0)
    d.text(108 * s, 58 * s, ":L??", scale=s, fill=G0)
    d.text(76 * s, 69 * s, "HP", scale=s, fill=G0)
    hpbar(d, s, 94, 70, 58, 1.0)
    px(d, s, 74, 78, 82, 1, G0)
    px(d, s, 74, 75, 1, 3, G0)

    # pikachu back sprite, bottom-left, sitting on the dialogue box line
    pw, ph = PIKACHU_BACK.width, PIKACHU_BACK.height
    d.add(image_tag(PIKA_URI, 10 * s, (96 - ph * 2) * s, pw * 2 * s, ph * 2 * s))

    # dialogue box
    dbox(d, s, 0, 96, 160, 48)

    # ---- dialogue phases
    CYCLE = 28.0

    def pct(t):
        return fnum(t / CYCLE * 100)

    phases = [
        ("A wild COLE", "appeared!"),
        ("COLE is a FULL-", "STACK BUILDER!"),
        ("He writes the", "scraper, the CI,"),
        ("and reads the", "postmortem."),
        ("GENGAR is", "loafing around!"),
    ]
    d.css.append(
        "@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}"
        ".blink{animation:blink 1.1s steps(1,end) infinite}"
    )
    for i, (l1, l2) in enumerate(phases):
        t0, t1 = i * 4.0, i * 4.0 + 4.0
        cls = f"ph{i}"
        d.css.append(
            f".{cls}{{opacity:0;animation:{cls} {fnum(CYCLE)}s linear infinite}}"
            f"@keyframes {cls}{{0%,{pct(t0)}%{{opacity:0}}"
            f"{pct(t0 + 0.02)}%,{pct(t1 - 0.02)}%{{opacity:1}}"
            f"{pct(t1)}%,100%{{opacity:0}}}}"
        )
        d.add(f'<g class="{cls}">')
        for li, line in enumerate((l1, l2)):
            y = 104 + li * 14
            d.text(8 * s, y * s, line, scale=s, fill=G0)
            # typewriter cover
            n = len(line)
            ts = t0 + 0.35 + (0 if li == 0 else len(l1) * 0.05 + 0.35)
            te = ts + n * 0.05
            tid = f"tp{i}_{li}"
            d.css.append(
                f".{tid}{{transform-box:fill-box;transform-origin:100% 50%;"
                f"animation:{tid} {fnum(CYCLE)}s linear infinite}}"
                f"@keyframes {tid}{{0%{{transform:scaleX(1)}}"
                f"{pct(ts)}%{{transform:scaleX(1);animation-timing-function:steps({n},end)}}"
                f"{pct(te)}%,100%{{transform:scaleX(0)}}}}"
            )
            d.rect(8 * s, (y - 1) * s, n * 8 * s + s, 10 * s, G3, cls=tid)
        d.tri_down(148 * s, 136 * s, s, fill=G0, cls="blink")
        d.add("</g>")

    # ---- menu phase (20s..28s)
    t0, t1 = 20.0, 28.0
    d.css.append(
        f".ph5{{opacity:0;animation:ph5 {fnum(CYCLE)}s linear infinite}}"
        f"@keyframes ph5{{0%,{pct(t0)}%{{opacity:0}}"
        f"{pct(t0 + 0.02)}%,{pct(t1 - 0.05)}%{{opacity:1}}100%{{opacity:0}}}}"
    )
    d.add('<g class="ph5">')
    d.text(8 * s, 104 * s, "What will", scale=s, fill=G0)
    d.text(8 * s, 118 * s, "YOU do?", scale=s, fill=G0)
    dbox(d, s, 92, 78, 68, 66)
    items = ["FIGHT", "ITEM", "PKMN", "RUN"]
    for i, it in enumerate(items):
        d.text(112 * s, (86 + i * 14) * s, it, scale=s, fill=G0)
    # cursor cycles down the menu, 2s per row
    steps_css = []
    for i in range(4):
        a, b = t0 + i * 2.0, t0 + (i + 1) * 2.0
        steps_css.append(f"{pct(a)}%,{pct(min(b, CYCLE) - 0.02)}%{{transform:translateY({i * 14 * s}px)}}")
    d.css.append(
        f".mcur{{animation:mcur {fnum(CYCLE)}s linear infinite}}"
        f"@keyframes mcur{{0%{{transform:translateY(0)}}{''.join(steps_css)}100%{{transform:translateY(0)}}}}"
    )
    d.add('<g class="mcur">')
    d.tri_right(101 * s, 86 * s, s, fill=G0)
    d.add("</g></g>")

    # ---- screen overlays: dot-matrix grid + vignette
    d.defs.append(
        f'<pattern id="dots" width="{s}" height="{s}" patternUnits="userSpaceOnUse">'
        f'<rect x="{s - 0.5}" y="0" width="0.5" height="{s}" fill="rgba(15,56,15,0.07)"/>'
        f'<rect x="0" y="{s - 0.5}" width="{s}" height="0.5" fill="rgba(15,56,15,0.07)"/>'
        f"</pattern>"
        '<radialGradient id="vig" cx="50%" cy="46%" r="72%">'
        '<stop offset="62%" stop-color="rgba(15,56,15,0)"/>'
        '<stop offset="100%" stop-color="rgba(15,56,15,0.16)"/></radialGradient>'
    )
    d.add(f'<rect x="0" y="0" width="{SW}" height="{SH}" fill="url(#dots)"/>')
    d.add(f'<rect x="0" y="0" width="{SW}" height="{SH}" fill="url(#vig)"/>')
    d.add(f'<polygon points="0,0 {SW * 0.28},0 0,{SH * 0.5}" fill="rgba(255,255,255,0.045)"/>')
    d.add("</g>")

    d.save("gameboy.svg")


def build_button(name, label, w_log=76):
    S = 4
    d = Doc(w_log * S, 18 * S)
    dbox(d, S, 0, 0, w_log, 18)
    tw = len(label) * 8
    x = (w_log - tw - 10) // 2 + 10
    d.css.append("@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}.blink{animation:blink 1.1s steps(1,end) infinite}")
    d.tri_right(int(x - 10) * S, 6 * S, S, fill=G0, cls="blink")
    d.text(int(x) * S, 5 * S, label, scale=S, fill=G0)
    d.save(f"menu-{name}.svg")


def build_header(name, label):
    S = 4
    d = Doc(160 * S, 20 * S)
    d.rect(0, 0, 160 * S, 20 * S, G0)
    px(d, S, 1, 1, 158, 18, G3)
    px(d, S, 3, 3, 154, 14, G0)
    d.tri_right(8 * S, 6 * S, S, fill=G3)
    d.text(16 * S, 5 * S, label, scale=S, fill=G3)
    tw = 16 + len(label) * 8 + 6
    for x in range(tw, 136, 4):
        px(d, S, x, 9, 2, 2, G2)
    blit_map(d, S, 142, 4, POKEBALL, colors={"#": G3, "o": G2, "+": G3, "-": G0})
    d.save(f"h-{name}.svg")


def _typed_line(d, S, x, y, text, phase_dur, start, fill=G0, bg=G3, cps=28.0, gs=0.75):
    """One-shot looping typewriter line for cards. gs = glyph scale (of 8px)."""
    n = len(text)
    d.text(x * S, y * S, text, scale=S * gs, fill=fill)
    ts, te = start, start + n / cps
    tid = f"t{int(x)}_{int(y)}"
    p = lambda t: fnum(t / phase_dur * 100)
    d.css.append(
        f".{tid}{{transform-box:fill-box;transform-origin:100% 50%;"
        f"animation:{tid} {fnum(phase_dur)}s linear infinite}}"
        f"@keyframes {tid}{{0%{{transform:scaleX(1)}}"
        f"{p(ts)}%{{transform:scaleX(1);animation-timing-function:steps({n},end)}}"
        f"{p(te)}%,100%{{transform:scaleX(0)}}}}"
    )
    d.rect(x * S, (y - 0.5) * S, (n * 8 * gs + 1) * S, (8 * gs + 1.5) * S, bg, cls=tid)


def build_card(fname, move, flavor, chips, pp, rows, link_label, icon, icon_colors=None):
    S = 4
    H = 40 + len(rows) * 7 + 22
    d = Doc(160 * S, H * S)
    dbox(d, S, 0, 0, 160, H)

    head_gs = 0.75 if len(move) * 6 <= 128 else 0.625
    _typed_line(d, S, 8, 7, move, 10.0, 0.4, gs=head_gs)
    d.css.append(
        "@keyframes fadein{0%,24%{opacity:0}26%,100%{opacity:1}}"
        ".fdin{animation:fadein 10s linear infinite}"
        "@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}"
        ".blink{animation:blink 1.1s steps(1,end) infinite}"
    )
    d.add('<g class="fdin">')
    d.text(8 * S, 17 * S, flavor, scale=S * 0.625, fill=G1)
    d.add("</g>")
    blit_map(d, S, 140, 5, icon, colors=icon_colors or {"#": G0, "o": G1, "+": G2, "-": G3})

    px(d, S, 6, 27, 148, 1, G1)

    # type chips + PP
    cx = 8
    for chip in chips:
        w = len(chip) * 5 + 8
        px(d, S, cx, 31, w, 11, G0)
        px(d, S, cx + 1, 32, w - 2, 9, G3)
        d.text((cx + 4) * S, 34 * S, chip, scale=S * 0.625, fill=G0)
        cx += w + 4
    pp_txt = f"PP {pp}"
    d.text((152 - len(pp_txt) * 5) * S, 34 * S, pp_txt, scale=S * 0.625, fill=G0)

    y = 48
    for label, value in rows:
        d.text(10 * S, y * S, label, scale=S * 0.5, fill=G1)
        d.text(44 * S, y * S, value, scale=S * 0.5, fill=G0)
        y += 7
    px(d, S, 6, y + 1, 148, 1, G1)
    d.tri_right(8 * S, (y + 6) * S, S * 0.625, fill=G0, cls="blink")
    d.text(15 * S, (y + 5) * S, link_label, scale=S * 0.625, fill=G0)
    d.save(fname)


def build_bag():
    S = 4
    items = [
        ("PYTHON", "x99"),
        ("POSTGRES", "x64"),
        ("SUPABASE", "x32"),
        ("GH-ACTIONS", "x24"),
        ("NETLIFY", "x16"),
        ("BASH", "x255"),
        ("CANCEL", ""),
    ]
    H = 20 + len(items) * 12 + 10
    d = Doc(160 * S, H * S)
    dbox(d, S, 0, 0, 160, H)
    d.text(10 * S, 8 * S, "COLE checked the BAG...", scale=S * 0.75, fill=G1)
    px(d, S, 6, 19, 148, 1, G1)
    for i, (name, qty) in enumerate(items):
        y = 25 + i * 12
        d.text(24 * S, y * S, name, scale=S, fill=G0)
        if qty:
            d.text((150 - len(qty) * 8) * S, y * S, qty, scale=S, fill=G0)
    # cursor steps through the items
    n = len(items)
    cyc = n * 1.1
    p = lambda t: fnum(t / cyc * 100)
    frames = []
    for i in range(n):
        a, b = i * 1.1, (i + 1) * 1.1
        frames.append(f"{p(a)}%,{p(b - 0.02)}%{{transform:translateY({i * 12 * S}px)}}")
    d.css.append(
        f".bcur{{animation:bcur {fnum(cyc)}s linear infinite}}"
        f"@keyframes bcur{{0%{{transform:translateY(0)}}{''.join(frames)}100%{{transform:translateY(0)}}}}"
    )
    d.add('<g class="bcur">')
    d.tri_right(12 * S, 25 * S, S, fill=G0)
    d.add("</g>")
    d.save("bag.svg")


def build_trainer():
    S = 4
    H = 116
    d = Doc(160 * S, H * S)
    dbox(d, S, 0, 0, 160, H)
    d.text(10 * S, 8 * S, "TRAINER CARD", scale=S * 0.875, fill=G0)
    d.text(102 * S, 9 * S, "IDNo.00094", scale=S * 0.625, fill=G1)
    px(d, S, 6, 19, 148, 1, G1)

    gw, gh = GENGAR.width, GENGAR.height
    d.add(f'<g class="bob">{image_tag(GENGAR_URI, 10 * S, 24 * S, gw * S, gh * S)}</g>')
    d.css.append(
        "@keyframes bob{0%,49.9%{transform:translateY(0)}50%,100%{transform:translateY(-2px)}}"
        ".bob{animation:bob 1.4s steps(1,end) infinite}"
    )

    rows = [("NAME/", "COLE"), ("CLASS/", "FULL-STACK"), ("MONEY/", "$?,???,???"), ("TIME/", "999:59")]
    y = 26
    for label, value in rows:
        d.text(66 * S, y * S, label, scale=S * 0.625, fill=G1)
        d.text(100 * S, y * S, value, scale=S * 0.625, fill=G0)
        y += 12

    px(d, S, 6, 76, 148, 1, G1)
    d.text(10 * S, 81 * S, "BADGES", scale=S * 0.75, fill=G1)

    badges = [
        (BADGE_CIRCLE, "PYTHN"),
        (BADGE_DIAMOND, "PGSQL"),
        (BADGE_TRIANGLE, "SUPBS"),
        (GEAR, "ACTNS"),
        (BADGE_HEX, "NTLFY"),
        (BASH_BADGE, "BASH"),
        (None, "????"),
        (None, "????"),
    ]
    d.css.append(
        "@keyframes glint{0%,88%{opacity:0}90%,94%{opacity:.85}96%,100%{opacity:0}}"
    )
    for i, (art, label) in enumerate(badges):
        bx = 10 + i * 18
        if art is not None:
            blit_map(d, S, bx, 91, art)
            d.css.append(
                f".gl{i}{{animation:glint 9s linear infinite;animation-delay:{fnum(i * 0.9)}s}}"
            )
            d.rect(bx * S, 91 * S, 12 * S, 12 * S, G3, cls=f"gl{i}")
        else:
            for xx in range(0, 12, 2):
                px(d, S, bx + xx, 91, 1, 1, G2)
                px(d, S, bx + xx, 102, 1, 1, G2)
                px(d, S, bx, 91 + xx, 1, 1, G2)
                px(d, S, bx + 11, 91 + xx, 1, 1, G2)
        lw = len(label) * 8 * 0.375
        d.text((bx + 6) * S - lw * S / 2, 106 * S, label, scale=S * 0.375, fill=G1 if art else G2)
    d.save("trainer-card.svg")


def build_divider():
    S = 4
    d = Doc(160 * S, 20 * S)
    d.css.append(
        "@keyframes rustle{0%,46%{transform:translateX(0)}50%,96%{transform:translateX(1px)}100%{transform:translateX(0)}}"
        ".rus{animation:rustle 1.3s steps(1,end) infinite}"
        "@keyframes ghost{0%,70%{transform:translateY(19px);opacity:0}"
        "75%,88%{transform:translateY(0);opacity:1}93%,100%{transform:translateY(19px);opacity:0}}"
        ".gho{animation:ghost 11s steps(7) infinite}"
    )
    gh = 16
    gw = GENGAR_SHADOW.width * gh / GENGAR_SHADOW.height
    d.add(f'<g class="gho">{image_tag(GENGAR_SHADOW_URI, 80 * S - gw * S / 2, 2 * S, gw * S, gh * S)}</g>')
    for i in range(10):
        cls = "rus" if i in (2, 7) else None
        if cls:
            d.add(f'<g class="{cls}">')
        blit_map(d, S, i * 16, 11, GRASS, colors={"#": G1 if i % 2 else G0})
        if cls:
            d.add("</g>")
    d.save("divider.svg")


def build_save():
    S = 4
    d = Doc(160 * S, 40 * S)
    dbox(d, S, 0, 0, 160, 40)
    d.text(8 * S, 9 * S, "Would you like to", scale=S * 0.75, fill=G0)
    d.text(8 * S, 21 * S, "SAVE the game?", scale=S * 0.75, fill=G0)
    dbox(d, S, 112, 3, 44, 34)
    d.text(126 * S, 9 * S, "YES", scale=S, fill=G0)
    d.text(126 * S, 23 * S, "NO", scale=S, fill=G0)
    d.css.append("@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}.blink{animation:blink 1.1s steps(1,end) infinite}")
    d.tri_right(118 * S, 10 * S, S, fill=G0, cls="blink")
    d.save("save.svg")


def build_contact(name, label):
    S = 4
    w_log = max(len(label) * 8 + 28, 60)
    d = Doc(w_log * S, 16 * S)
    dbox(d, S, 0, 0, w_log, 16)
    d.tri_right(8 * S, 5 * S, S * 0.75, fill=G0, cls="blink")
    d.css.append("@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}.blink{animation:blink 1.1s steps(1,end) infinite}")
    d.text(16 * S, 4 * S, label, scale=S, fill=G0)
    d.save(f"btn-{name}.svg")


def main():
    os.makedirs(OUT, exist_ok=True)
    print("building assets:")
    build_hero()
    build_button("fight", "FIGHT")
    build_button("bag", "BAG")
    build_button("pokemon", "POKéMON")
    build_button("run", "RUN")
    build_header("fight", "FIGHT")
    build_header("bag", "BAG")
    build_header("pokemon", "POKéMON")
    build_header("run", "RUN")
    build_card(
        "card-haywire.svg",
        "COLE used HAYWIRE!",
        "It's super effective!",
        ["GRASS", "ELECTRIC"],
        "16/16",
        [
            ("pipeline", "Python scrape/publish cron"),
            ("data", "Supabase Postgres, RLS lock"),
            ("frontend", "static site + Netlify fns"),
            ("email", "Beehiiv newsletter"),
            ("tests", "policy tests, 16x5 verdicts"),
            ("ci", "ruff + eslint, 0 findings"),
        ],
        "haywireag.com",
        WHEAT,
    )
    build_card(
        "card-agentfusion.svg",
        "COLE used AGENT-FUSION!",
        "Wild AI agents cooperated!",
        ["GHOST", "PSYCHIC"],
        "24/24",
        [
            ("routing", "Claude Code + OpenAI Codex"),
            ("skills", "MD+YAML task profiles"),
            ("language", "Python 3.11+"),
            ("license", "MIT"),
        ],
        "ColeGlasgow/agent-fusion",
        ROBOT,
    )
    build_bag()
    build_trainer()
    build_divider()
    build_save()
    build_contact("email", "EMAIL")
    build_contact("site", "HAYWIREAG.COM")
    print("done.")


if __name__ == "__main__":
    main()
