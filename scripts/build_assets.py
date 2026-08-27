#!/usr/bin/env python3
"""Build the pixel-art SVG assets for the profile README.

Nintendo DS / Pokemon Diamond & Pearl era style: a two-screen DS Lite hero
playing a Gen-4 battle, and section panels styled after D/P's touch UI —
white rounded dialogue panels, navy headers, color-coded touch buttons,
Gen-4 type badges, and a D/P trainer card.

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

# ---- Diamond/Pearl palette
NAVY = "#405078"        # panel borders
NAVY_D = "#2c3a58"
PANEL = "#f8f8f6"       # dialogue/panel white
PANEL_ALT = "#f0ede4"
TXT = "#383840"         # body text
MUT = "#7890b0"         # muted label text
LINK = "#2860c0"
RED = "#e04838"
CREAM = "#f0f0e0"

# ---- trainer-card palette (shared by the trainer card and the dex entries)
CARD_BG = "#16161e"      # card panel
CARD_BD = "#c8a040"      # gold border
GOLD = "#e8c048"         # section titles
SUB = "#8890a8"          # muted label text
VAL = "#f0f0f4"          # value text
INNER_BG = "#20202c"     # inset sprite/portrait box
INNER_BD = "#3a3a48"
RULE_D = "#3a3a48"
LINK_D = "#78a8f0"

TYPE_COLORS = {
    "GRASS": ("#78c850", "#ffffff"),
    "ELECTRIC": ("#f8d030", "#605010"),
    "GHOST": ("#705898", "#ffffff"),
    "PSYCHIC": ("#f85888", "#ffffff"),
}

# DS Lite shell
SHELL = "#ececf0"
SHELL_HI = "#fafafc"
SHELL_LO = "#c6c6d0"
SHELL_EDGE = "#a8a8b4"
BEZEL = "#1a1a20"

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

    def text(self, x, y, s, scale=1, fill=TXT, cls=None):
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

    def text_shadow(self, x, y, s, scale=1, fill="#ffffff", shadow="rgba(0,0,0,.35)", dy=None):
        d = dy if dy is not None else scale
        self.text(x + d, y + d, s, scale=scale, fill=shadow)
        self.text(x, y, s, scale=scale, fill=fill)

    def tri_right(self, x, y, s, fill=TXT, cls=None):
        c = f' class="{cls}"' if cls else ""
        rows = [1, 2, 3, 4, 3, 2, 1]
        body = "".join(
            f'<rect x="0" y="{i}" width="{w}" height="1"/>' for i, w in enumerate(rows)
        )
        self.add(f'<g transform="translate({fnum(x)},{fnum(y)}) scale({fnum(s)})" fill="{fill}"{c}>{body}</g>')

    def tri_down(self, x, y, s, fill=TXT, cls=None):
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


def hpbar(doc, s, x, y, w, frac=1.0, fill="#48c060"):
    px(doc, s, x, y, w, 7, "#404048")
    px(doc, s, x + 1, y + 1, w - 2, 5, "#e8e8e0")
    px(doc, s, x + 1, y + 1, 14, 5, "#404048")
    doc.text((x + 3) * s, (y + 1.2) * s, "HP", scale=s * 0.55, fill="#f8c838")
    bar_x, bar_w = x + 16, w - 18
    fill_w = max(1, round(bar_w * frac))
    px(doc, s, bar_x, y + 2, fill_w, 3, fill)


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


def silhouette(path, color=(74, 58, 94, 255)):
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


GENGAR = load_sprite(os.path.join(SRC, "gengar-dp.png"))          # ~58x53
VOLKNER = load_sprite(os.path.join(SRC, "volkner.png"))           # ~38x78
PIKACHU = load_sprite(os.path.join(SRC, "pikachu-dp-back.png"))   # ~70x69
GENGAR_SHADOW = silhouette(os.path.join(SRC, "gengar-dp.png"))
GENGAR_URI = b64uri(GENGAR)
VOLKNER_URI = b64uri(VOLKNER)
PIKA_URI = b64uri(PIKACHU)
GENGAR_SHADOW_URI = b64uri(GENGAR_SHADOW)

# ---------------------------------------------------------------- pixel art

POKEBALL = [
    "....####....",
    "..##++++##..",
    ".#++++++++#.",
    ".#+++++--+#.",
    "#++++++--++#",
    "#++++++++++#",
    "############",
    "#oooo##oooo#",
    ".#oo#--#oo#.",
    ".#oo#--#oo#.",
    "..##o##o##..",
    "....####....",
]
POKEBALL_COLORS = {"#": "#303038", "+": "#e84838", "o": "#f0f0f4", "-": "#f8f8f8"}

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

DIAMOND_GEM = [
    "....#....",
    "..##+##..",
    ".#+++++#.",
    "#+++++++#",
    ".#+++++#.",
    "..##+##..",
    "....#....",
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




# ---------------------------------------------------------------- hero (DS Lite)

# screen logical size 256x192 at scale 2
SS = 2
SCR_W, SCR_H = 256 * SS, 192 * SS  # 512 x 384
MARG = 64
W_HERO = SCR_W + 2 * MARG          # 640


def _dialogue_phases(d, s, cycle, phases, box, text_xy, cover_bg):
    """Typewriter dialogue phases inside an already-drawn box."""
    bx, by, bw, bh = box
    tx, ty0, line_h = text_xy

    def pct(t):
        return fnum(t / cycle * 100)

    d.css.append(
        "@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}"
        ".blink{animation:blink 1.1s steps(1,end) infinite}"
    )
    t0 = 0.0
    for i, (dur, lines) in enumerate(phases):
        t1 = t0 + dur
        cls = f"ph{i}"
        d.css.append(
            f".{cls}{{opacity:0;animation:{cls} {fnum(cycle)}s linear infinite}}"
            f"@keyframes {cls}{{0%,{pct(t0)}%{{opacity:0}}"
            f"{pct(t0 + 0.02)}%,{pct(t1 - 0.02)}%{{opacity:1}}"
            f"{pct(t1)}%,100%{{opacity:0}}}}"
        )
        d.add(f'<g class="{cls}">')
        prev_len = 0
        for li, line in enumerate(lines):
            y = ty0 + li * line_h
            d.text(tx * s, y * s, line, scale=s * 0.75, fill=TXT)
            n = len(line)
            ts = t0 + 0.3 + prev_len * 0.033 + (0.3 if li else 0)
            te = ts + n * 0.033
            prev_len += n
            tid = f"tp{i}_{li}"
            d.css.append(
                f".{tid}{{transform-box:fill-box;transform-origin:100% 50%;"
                f"animation:{tid} {fnum(cycle)}s linear infinite}}"
                f"@keyframes {tid}{{0%{{transform:scaleX(1)}}"
                f"{pct(ts)}%{{transform:scaleX(1);animation-timing-function:steps({n},end)}}"
                f"{pct(te)}%,100%{{transform:scaleX(0)}}}}"
            )
            d.rect(tx * s, (y - 1) * s, (n * 6 + 2) * s, 8.5 * s, cover_bg, cls=tid)
        d.tri_down((bx + bw - 14) * s, (by + bh - 10) * s, s * 0.9, fill=RED, cls="blink")
        d.add("</g>")
        t0 = t1


def build_hero():
    top_h = 456
    hinge_h = 26
    bot_h = 460
    H = top_h + hinge_h + bot_h  # 942
    d = Doc(W_HERO, H, ns="hero_")

    shell_g = d.grad("shg", SHELL_HI, SHELL)
    shell_g2 = d.grad("shg2", SHELL, "#dcdce2")

    # ---- shells
    d.add(f'<rect x="0" y="0" width="{W_HERO}" height="{top_h}" rx="30" fill="{shell_g}" stroke="{SHELL_EDGE}" stroke-width="2"/>')
    d.add(f'<rect x="0" y="{top_h + hinge_h}" width="{W_HERO}" height="{bot_h}" rx="30" fill="{shell_g2}" stroke="{SHELL_EDGE}" stroke-width="2"/>')
    # hinge
    d.add(f'<rect x="14" y="{top_h - 8}" width="{W_HERO - 28}" height="{hinge_h + 16}" rx="12" fill="#c9c9d2" stroke="{SHELL_EDGE}" stroke-width="1.5"/>')
    for hx in (110, W_HERO - 110):
        d.add(f'<rect x="{hx - 26}" y="{top_h - 4}" width="52" height="{hinge_h + 8}" rx="9" fill="#b8b8c2"/>')
    d.add(f'<circle cx="{W_HERO / 2}" cy="{top_h + hinge_h / 2 + 4}" r="3.5" fill="#8a8a96"/>')  # mic

    d.defs.append(f'<clipPath id="hero_scr"><rect width="{SCR_W}" height="{SCR_H}"/></clipPath>')
    # ---- top screen bezel + screen
    d.add(f'<rect x="{MARG - 14}" y="24" width="{SCR_W + 28}" height="{SCR_H + 28}" rx="10" fill="{BEZEL}"/>')
    TX, TY = MARG, 38
    d.add(f'<g transform="translate({TX},{TY})" clip-path="url(#hero_scr)" shape-rendering="crispEdges">')
    s = SS

    sky = d.grad("sky", "#78b8e8", "#d0ecf8")
    d.add(f'<rect width="{SCR_W}" height="{SCR_H}" fill="{sky}"/>')
    # distant hills
    d.add(f'<ellipse cx="{60 * s}" cy="{120 * s}" rx="{110 * s}" ry="{18 * s}" fill="#a8d890"/>')
    d.add(f'<ellipse cx="{210 * s}" cy="{124 * s}" rx="{120 * s}" ry="{20 * s}" fill="#98cc80"/>')
    d.add(f'<rect y="{124 * s}" width="{SCR_W}" height="{68 * s}" fill="#8cc474"/>')

    # enemy platform + gengar
    plat = d.grad("plat", "#70b858", "#4e9040")
    d.add(f'<ellipse cx="{186 * s}" cy="{122 * s}" rx="{60 * s}" ry="{15 * s}" fill="{plat}"/>')
    # Cole stands behind his Gengar
    vw, vh = VOLKNER.width, VOLKNER.height
    scale_v = 64 / vh
    d.add(image_tag(VOLKNER_URI, 120 * s, (112 - 64) * s, vw * scale_v * s, 64 * s))
    gw, gh = GENGAR.width, GENGAR.height
    scale_g = 70 / gh
    d.css.append(
        "@keyframes bob{0%,49.9%{transform:translateY(0)}50%,100%{transform:translateY(-3px)}}"
        ".bob{animation:bob 1.6s steps(1,end) infinite}"
    )
    d.add(f'<g class="bob">{image_tag(GENGAR_URI, (186 - gw * scale_g / 2) * s, (126 - 70) * s, gw * scale_g * s, 70 * s)}</g>')

    # player platform + pikachu (back)
    d.add(f'<ellipse cx="{62 * s}" cy="{146 * s}" rx="{62 * s}" ry="{13 * s}" fill="{plat}"/>')
    pw, ph = PIKACHU.width, PIKACHU.height
    scale_p = 74 / ph
    d.add(image_tag(PIKA_URI, (62 - pw * scale_p / 2) * s, (150 - 74) * s, pw * scale_p * s, 74 * s))

    # enemy info box
    rbox(d, s, 8, 10, 116, 34, CREAM, border="#586890", b=2)
    d.text(16 * s, 16 * s, "COLE", scale=s * 0.75, fill="#303038")
    d.text(88 * s, 16 * s, "L28", scale=s * 0.625, fill="#303038")
    hpbar(d, s, 16, 27, 100 - 8, 1.0)

    # player info box
    rbox(d, s, 140, 100, 108, 40, CREAM, border="#586890", b=2)
    d.text(147 * s, 106 * s, "PIKACHU", scale=s * 0.625, fill="#303038")
    d.text(216 * s, 106 * s, "L5", scale=s * 0.625, fill="#303038")
    hpbar(d, s, 147, 117, 94, 1.0)
    px(d, s, 147, 128, 94, 3, "#c8c8c0")
    px(d, s, 147, 128, 62, 3, "#3890f0")

    # dialogue box
    rbox(d, s, 4, 148, 248, 40, PANEL, border=NAVY, b=2)
    phases = [
        (4.0, ["A wild COLE appeared!"]),
        (4.0, ["COLE is a FULL-STACK BUILDER!"]),
        (5.0, ["He writes the scraper, the CI,", "and reads the postmortem."]),
        (5.0, ["He wrangles ENTERPRISE DATA at", "WELLMARK. Runs on coffee."]),
        (4.0, ["GENGAR is loafing around!"]),
        (4.5, ["What will YOU do?"]),
    ]
    _dialogue_phases(d, s, 26.5, phases, (4, 148, 248, 40), (14, 157, 13), PANEL)
    d.add("</g>")

    # speakers on the top half
    for sx in (34, W_HERO - 34):
        for i, (ox, oy) in enumerate([(0, 0), (-7, 12), (7, 12), (-11, 25), (0, 25), (11, 25)]):
            d.add(f'<circle cx="{sx + ox}" cy="{392 + oy}" r="2.6" fill="#b0b0bc"/>')

    # ---- bottom screen bezel + touch UI
    BY = top_h + hinge_h + 34
    d.add(f'<rect x="{MARG - 14}" y="{BY - 14}" width="{SCR_W + 28}" height="{SCR_H + 28}" rx="10" fill="{BEZEL}"/>')
    d.add(f'<g transform="translate({MARG},{BY})" clip-path="url(#hero_scr)" shape-rendering="crispEdges">')

    touch_bg = d.grad("tbg", "#2c405e", "#16243c")
    d.add(f'<rect width="{SCR_W}" height="{SCR_H}" fill="{touch_bg}"/>')
    for gy in range(0, 192, 16):
        px(d, s, 0, gy, 256, 1, "rgba(255,255,255,0.03)")

    fight_g = d.grad("fg", "#f05848", "#b82c28")
    bag_g = d.grad("bg2", "#f0a030", "#c07818")
    pkm_g = d.grad("pg", "#50b068", "#268048")
    run_g = d.grad("rg", "#5088d8", "#2c5ca8")

    rbox(d, s, 28, 18, 200, 84, fight_g, border="#801c1c", b=2)
    d.add(f'<path d="{rpath(s, 32, 22, 192, 12)}" fill="rgba(255,255,255,0.22)"/>')
    blit_map(d, s, 74, 48, POKEBALL, POKEBALL_COLORS)
    d.text_shadow(98 * s, 48 * s, "FIGHT", scale=s * 1.5, shadow="rgba(80,10,10,.6)")

    row = [("BAG", bag_g, "#8a5410", 28), ("PKMN", pkm_g, "#175830", 98), ("RUN", run_g, "#1c3c78", 168)]
    for label, g, bd, bx in row:
        rbox(d, s, bx, 116, 60, 44, g, border=bd, b=2)
        d.add(f'<path d="{rpath(s, bx + 3, 119, 54, 8)}" fill="rgba(255,255,255,0.2)"/>')
        tw = len(label) * 8
        d.text_shadow((bx + 30) * s - tw * s / 2, 131 * s, label, scale=s, shadow="rgba(0,0,0,.4)")

    # stylus taps cycling FIGHT -> BAG -> PKMN -> RUN
    taps = [(128, 60), (58, 138), (128, 138), (198, 138)]
    cyc = 8.0

    def pctc(t):
        return fnum(t / cyc * 100)

    for i, (cx, cy) in enumerate(taps):
        w0 = i * 2.0
        d.css.append(
            f".tapo{i}{{opacity:0;animation:tapo{i} {fnum(cyc)}s linear infinite}}"
            f"@keyframes tapo{i}{{0%,{pctc(w0)}%{{opacity:0}}"
            f"{pctc(w0 + 0.02)}%{{opacity:.85}}{pctc(w0 + 0.55)}%,100%{{opacity:0}}}}"
            f".taps{i}{{transform-box:fill-box;transform-origin:50% 50%;"
            f"animation:taps{i} {fnum(cyc)}s linear infinite}}"
            f"@keyframes taps{i}{{0%,{pctc(w0)}%{{transform:scale(.35)}}"
            f"{pctc(w0 + 0.55)}%,100%{{transform:scale(1.6)}}}}"
        )
        d.add(
            f'<g class="tapo{i}"><circle cx="{cx * s}" cy="{cy * s}" r="{14 * s}" '
            f'fill="none" stroke="#ffffff" stroke-width="3" class="taps{i}"/></g>'
        )
    d.add("</g>")

    # ---- bottom shell controls
    cy_ctrl = BY + SCR_H / 2 - 10
    # d-pad
    dp = 26
    d.add(f'<g fill="#3c3c46">'
          f'<rect x="{dp - 8}" y="{cy_ctrl - 23}" width="16" height="46" rx="4"/>'
          f'<rect x="{dp - 23}" y="{cy_ctrl - 8}" width="46" height="16" rx="4"/></g>')
    d.add(f'<circle cx="{dp}" cy="{cy_ctrl}" r="6" fill="#33333c"/>')
    # abxy
    ab = W_HERO - 26
    for (ox, oy, letter) in [(0, -14, "X"), (-13, 0, "Y"), (13, 0, "A"), (0, 14, "B")]:
        d.add(f'<circle cx="{ab + ox}" cy="{cy_ctrl + oy}" r="7" fill="#3c3c46"/>')
        d.text(ab + ox - 2.6, cy_ctrl + oy - 3, letter, scale=0.65, fill="#9a9aa8")
    # start/select
    for i, lbl in enumerate(("START", "SELECT")):
        yy = cy_ctrl + 40 + i * 22
        d.add(f'<rect x="{ab - 13}" y="{yy}" width="24" height="7" rx="3.5" fill="#3c3c46"/>')
        d.text(ab - 13, yy + 9, lbl, scale=0.4, fill="#8a8a96")
    # power led
    d.add(f'<circle cx="22" cy="{BY - 26}" r="4" fill="#40d060"/>')
    d.add(f'<circle cx="22" cy="{BY - 26}" r="7" fill="#40d060" opacity=".25"/>')

    # branding + gems
    label = "COLE DS"
    lw = len(label) * 8 * 0.75
    bx0 = (W_HERO - lw) / 2
    d.text(bx0, H - 20, label, scale=0.75, fill="#8a8a96")
    blit_map(d, 1, bx0 - 18, H - 21, DIAMOND_GEM, {"#": "#3858a8", "+": "#6890e0"})
    d.add(f'<circle cx="{bx0 + lw + 12}" cy="{H - 16.5}" r="4" fill="#e8a8c8"/>')
    d.add(f'<circle cx="{bx0 + lw + 10.6}" cy="{H - 18}" r="1.4" fill="#f8e0ec"/>')

    d.save("console.svg", crisp=False)


# ---------------------------------------------------------------- nav + headers

NAV_STYLES = {
    "dex": ("POKéDEX", "#f05848", "#b82c28", "#801c1c", "rgba(80,10,10,.6)"),
    "bag": ("BAG", "#f0a030", "#c07818", "#8a5410", "rgba(90,50,0,.55)"),
    "trainer": ("TRAINER CARD", "#50b068", "#268048", "#175830", "rgba(10,60,30,.55)"),
    "save": ("SAVE", "#5088d8", "#2c5ca8", "#1c3c78", "rgba(10,30,80,.55)"),
}


def build_button(name):
    label, c1, c2, bd, sh = NAV_STYLES[name]
    S = 2
    w_log, h_log = 150, 36
    d = Doc(w_log * S, h_log * S, ns=f"m{name}_")
    g = d.grad("g", c1, c2)
    rbox(d, S, 0, 0, w_log, h_log, g, border=bd, b=2)
    d.add(f'<path d="{rpath(S, 3, 3, w_log - 6, 9)}" fill="rgba(255,255,255,0.22)"/>')
    tw = len(label) * 8 * 1.25
    d.text_shadow((w_log * S - tw * S) / 2, 12 * S, label, scale=S * 1.25, shadow=sh, dy=S)
    d.save(f"menu-{name}.svg")


def build_header(name):
    label = NAV_STYLES[name][0]
    S = 2
    d = Doc(320 * S, 34 * S, ns=f"h{name}_")
    g = d.grad("g", "#31446a", "#1d2a44")
    rbox(d, S, 0, 0, 320, 32, g, border="#141c2e", b=1)
    d.add(f'<path d="{rpath(S, 2, 2, 316, 8)}" fill="rgba(255,255,255,0.10)"/>')
    blit_map(d, S, 10, 12, DIAMOND_GEM, {"#": "#2c6ea8", "+": "#58c8f0"})
    d.text_shadow(26 * S, 11 * S, label, scale=S * 1.25, shadow="rgba(0,0,0,.5)")
    cy = d.grad("cy", "#58c8f0", "#1d2a44", vertical=False)
    px(d, S, 26, 25, 180, 1, cy)
    blit_map(d, S, 296, 10, POKEBALL, POKEBALL_COLORS)
    d.save(f"h-{name}.svg")


# ---------------------------------------------------------------- cards


def sweep(d, s):
    """Trainer card's red corner sweep."""
    d.add(f'<path d="M{240 * s} {2 * s} L{318 * s} {2 * s} L{318 * s} {40 * s} Z" fill="#b02838"/>')
    d.add(f'<path d="M{262 * s} {2 * s} L{318 * s} {2 * s} L{318 * s} {30 * s} Z" fill="#d84048"/>')


def blit_scaled(doc, s, x, y, art, colors, k):
    """blit_map at k times pixel size, for promoting a 12x12 icon to a sprite."""
    doc.add(f'<g transform="translate({fnum(x * s)},{fnum(y * s)}) scale({fnum(k)})">')
    blit_map(doc, s, 0, 0, art, colors)
    doc.add("</g>")


def type_chips(doc, s, x, y, types):
    cx = x
    for t in types:
        cbg, ctx = TYPE_COLORS[t]
        w = len(t) * 6 + 12
        rbox(doc, s, cx, y, w, 16, cbg, border="#00000040", b=1)
        doc.text((cx + 6) * s, (y + 5) * s, t, scale=s * 0.75, fill=ctx)
        cx += w + 6
    return cx


def wrap(text, n):
    """Greedy wrap to n characters, for the dex flavor paragraph."""
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if len(t) > n:
            lines.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def build_card(fname, ns, name, dexno, species, meta, types, dex, link, art, art_colors):
    """A Pokedex entry: inset sprite panel, species line, HT/WT, flavor paragraph."""
    S = 2
    lines = wrap(dex, 46)
    H = 140 + len(lines) * 12 + 30
    d = Doc(320 * S, H * S, ns=ns + "_")
    rbox(d, S, 0, 0, 320, H, CARD_BG, border=CARD_BD, b=2)
    sweep(d, S)

    d.text(16 * S, 12 * S, "POKéDEX", scale=S, fill=GOLD)
    d.text(160 * S, 14 * S, dexno, scale=S * 0.75, fill=SUB)
    px(d, S, 12, 30, 296, 1, CARD_BD)

    # sprite panel, mirroring the trainer card's portrait box
    rbox(d, S, 16, 40, 76, 76, INNER_BG, border=INNER_BD, b=1)
    d.css.append(
        f"@keyframes {ns}bob{{0%,49.9%{{transform:translateY(0)}}50%,100%{{transform:translateY(-3px)}}}}"
        f".{ns}bob{{animation:{ns}bob 1.6s steps(1,end) infinite}}"
    )
    d.add(f'<g class="{ns}bob">')
    blit_scaled(d, S, 30, 54, art, art_colors, 4.0)
    d.add("</g>")

    x = 104
    d.text(x * S, 44 * S, name, scale=S, fill=VAL)
    d.text(x * S, 62 * S, species, scale=S * 0.75, fill=SUB)
    y = 80
    for label, value in meta:
        d.text(x * S, y * S, label, scale=S * 0.75, fill=SUB)
        d.text((x + 24) * S, y * S, value, scale=S * 0.75, fill=VAL)
        y += 13
    type_chips(d, S, x, 104, types)

    px(d, S, 12, 126, 296, 1, RULE_D)
    y = 134
    for ln in lines:
        d.text(18 * S, y * S, ln, scale=S * 0.75, fill=VAL)
        y += 12

    y += 4
    px(d, S, 12, y, 296, 1, RULE_D)
    d.tri_right(18 * S, (y + 7) * S, S * 0.8, fill=GOLD)
    lw = d.text(28 * S, (y + 6) * S, link, scale=S * 0.75, fill=LINK_D)
    px(d, S, 28, y + 14, lw / S, 1, "#3c5a8a")
    d.save(fname)


# ---------------------------------------------------------------- bag / trainer


def build_bag():
    S = 2
    items = [
        ("COFFEE", "x999"),
        ("PYTHON", "x99"),
        ("POSTGRES", "x64"),
        ("SUPABASE", "x32"),
        ("GH-ACTIONS", "x24"),
        ("NETLIFY", "x16"),
        ("BASH", "x255"),
        ("CANCEL", ""),
    ]
    H = 52 + len(items) * 16 + 10
    d = Doc(320 * S, H * S, ns="bag_")
    rbox(d, S, 0, 0, 320, H, PANEL, border=NAVY, b=2)
    og = d.grad("og", "#f0a030", "#c87818")
    rbox(d, S, 8, 8, 304, 26, og, border="#8a5410", b=1)
    d.add(f'<path d="{rpath(S, 10, 10, 300, 7)}" fill="rgba(255,255,255,0.2)"/>')
    d.text_shadow(18 * S, 16 * S, "BAG", scale=S, shadow="rgba(90,50,0,.55)", dy=S)
    d.text(120 * S, 18 * S, "COLE checked the BAG...", scale=S * 0.625, fill="#fff2dc")

    for i, (name, qty) in enumerate(items):
        y = 46 + i * 16
        if i % 2 == 0:
            px(d, S, 12, y - 3, 296, 15, PANEL_ALT)
        d.text(34 * S, y * S, name, scale=S, fill=TXT)
        if qty:
            d.text((306 - len(qty) * 8) * S, y * S, qty, scale=S, fill="#607090")
    n = len(items)
    cyc = n * 1.1
    p = lambda t: fnum(t / cyc * 100)
    frames = []
    for i in range(n):
        a, b = i * 1.1, (i + 1) * 1.1
        frames.append(f"{p(a)}%,{p(b - 0.02)}%{{transform:translateY({i * 16 * S}px)}}")
    d.css.append(
        f".bcur{{animation:bcur {fnum(cyc)}s linear infinite}}"
        f"@keyframes bcur{{0%{{transform:translateY(0)}}{''.join(frames)}100%{{transform:translateY(0)}}}}"
    )
    d.add('<g class="bcur">')
    d.tri_right(18 * S, 46 * S, S, fill=RED)
    d.add("</g>")
    d.save("bag.svg")


def build_trainer():
    S = 2
    H = 158
    d = Doc(320 * S, H * S)
    rbox(d, S, 0, 0, 320, H, "#16161e", border="#c8a040", b=2)
    # red corner sweep
    d.add(f'<path d="M{240 * S} {2 * S} L{318 * S} {2 * S} L{318 * S} {40 * S} Z" fill="#b02838"/>')
    d.add(f'<path d="M{262 * S} {2 * S} L{318 * S} {2 * S} L{318 * S} {30 * S} Z" fill="#d84048"/>')

    d.text(16 * S, 12 * S, "TRAINER CARD", scale=S, fill="#e8c048")
    d.text(160 * S, 14 * S, "IDNo.00094", scale=S * 0.75, fill="#8890a8")
    px(d, S, 12, 30, 296, 1, "#c8a040")

    gw, gh = GENGAR.width, GENGAR.height
    scale_g = 48 / gh
    d.css.append(
        "@keyframes bob{0%,49.9%{transform:translateY(0)}50%,100%{transform:translateY(-3px)}}"
        ".bob{animation:bob 1.6s steps(1,end) infinite}"
    )
    rbox(d, S, 232, 40, 76, 76, "#20202c", border="#3a3a48", b=1)
    vw, vh = VOLKNER.width, VOLKNER.height
    scale_v = 52 / vh
    d.add(image_tag(VOLKNER_URI, 240 * S, 60 * S, vw * scale_v * S, 52 * S))
    d.add(f'<g class="bob">{image_tag(GENGAR_URI, (282 - gw * scale_g / 2) * S, 66 * S, gw * scale_g * S, 48 * S)}</g>')

    rows = [("NAME", "COLE"), ("CLASS", "FULL-STACK"), ("JOB", "DATA @ WELLMARK"),
            ("MONEY", "$?,???,???"), ("TIME", "999:59")]
    y = 42
    for label, value in rows:
        d.text(16 * S, y * S, label, scale=S * 0.75, fill="#8890a8")
        d.text(76 * S, y * S, value, scale=S * 0.75, fill="#f0f0f4")
        y += 14

    px(d, S, 12, 108, 208, 1, "#3a3a48")
    d.text(16 * S, 114 * S, "BADGES", scale=S * 0.75, fill="#e8c048")

    badges = [
        (BADGE_CIRCLE, "PYTHN", "#e0b84c", "#806020"),
        (BADGE_DIAMOND, "PGSQL", "#c0c8d0", "#606870"),
        (BADGE_TRIANGLE, "SUPBS", "#c08850", "#6a4420"),
        (GEAR, "ACTNS", "#88a0b8", "#40506a"),
        (BADGE_HEX, "NTLFY", "#78c8b0", "#2a6a58"),
        (TERMINAL, "BASH", "#404a58", "#40d060"),
        (None, "????", None, None),
        (None, "????", None, None),
    ]
    d.css.append("@keyframes glint{0%,88%{opacity:0}90%,94%{opacity:.7}96%,100%{opacity:0}}")
    for i, (art, label, fill_c, edge_c) in enumerate(badges):
        bx = 16 + i * 26
        if art is not None:
            if art is TERMINAL:
                colors = {"#": fill_c, "-": "#181c24"}
                blit_map(d, S, bx, 126, art, colors)
                px(d, S, bx + 2, 128, 1, 1, edge_c)
                px(d, S, bx + 3, 129, 1, 1, edge_c)
                px(d, S, bx + 2, 130, 1, 1, edge_c)
                px(d, S, bx + 4, 132, 4, 1, edge_c)
            else:
                blit_map(d, S, bx, 126, art, {"#": edge_c, "+": fill_c, "-": fill_c, "o": fill_c})
            d.css.append(
                f".gl{i}{{opacity:0;animation:glint 9s linear infinite;animation-delay:{fnum(i * 0.9)}s}}"
            )
            d.rect(bx * S, 126 * S, 12 * S, 12 * S, "#ffffff", cls=f"gl{i}")
        else:
            for xx in range(0, 12, 2):
                px(d, S, bx + xx, 126, 1, 1, "#3a3a48")
                px(d, S, bx + xx, 137, 1, 1, "#3a3a48")
                px(d, S, bx, 126 + xx, 1, 1, "#3a3a48")
                px(d, S, bx + 11, 126 + xx, 1, 1, "#3a3a48")
        lw = len(label) * 8 * 0.5
        d.text((bx + 6) * S - lw * S / 2, 141 * S, label, scale=S * 0.5, fill="#8890a8" if art else "#4a4a58")
    d.save("trainer-card.svg")


# ---------------------------------------------------------------- divider / save / contact


def build_divider():
    S = 2
    d = Doc(320 * S, 30 * S)
    d.css.append(
        "@keyframes rustle{0%,46%{transform:translateX(0)}50%,96%{transform:translateX(2px)}100%{transform:translateX(0)}}"
        ".rus{animation:rustle 1.3s steps(1,end) infinite}"
        "@keyframes ghost{0%,70%{transform:translateY(30px);opacity:0}"
        "75%,88%{transform:translateY(0);opacity:1}93%,100%{transform:translateY(30px);opacity:0}}"
        ".gho{animation:ghost 11s steps(7) infinite}"
    )
    gh_l = 24
    gw = GENGAR_SHADOW.width * gh_l / GENGAR_SHADOW.height
    d.add(f'<g class="gho">{image_tag(GENGAR_SHADOW_URI, 160 * S - gw * S / 2, 1 * S, gw * S, gh_l * S)}</g>')
    for i in range(20):
        cls = "rus" if i in (4, 15) else None
        if cls:
            d.add(f'<g class="{cls}">')
        blit_map(d, S, i * 16, 22, GRASS, {"#": "#2f8f4a" if i % 2 else "#1f6b36"})
        if cls:
            d.add("</g>")
    d.save("divider.svg")


def build_save():
    S = 2
    d = Doc(320 * S, 60 * S)
    rbox(d, S, 0, 0, 320, 60, PANEL, border=NAVY, b=2)
    d.text(16 * S, 14 * S, "Would you like to", scale=S * 0.875, fill=TXT)
    d.text(16 * S, 32 * S, "SAVE the game?", scale=S * 0.875, fill=TXT)
    rbox(d, S, 232, 6, 78, 48, PANEL, border=NAVY, b=2)
    px(d, S, 238, 12, 66, 14, "#d8e8f8")
    d.text(256 * S, 15 * S, "YES", scale=S * 0.875, fill=TXT)
    d.text(256 * S, 35 * S, "NO", scale=S * 0.875, fill=TXT)
    d.css.append("@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}.blink{animation:blink 1.1s steps(1,end) infinite}")
    d.tri_right(244 * S, 15 * S, S * 0.875, fill=RED, cls="blink")
    d.save("save.svg")


def build_contact(name, label, c1, c2, bd, sh):
    S = 2
    w_log = len(label) * 8 + 44
    d = Doc(w_log * S, 30 * S, ns=f"c{name}_")
    g = d.grad("g", c1, c2)
    rbox(d, S, 0, 0, w_log, 30, g, border=bd, b=2)
    d.add(f'<path d="{rpath(S, 3, 3, w_log - 6, 8)}" fill="rgba(255,255,255,0.22)"/>')
    d.tri_right(12 * S, 11 * S, S * 0.8, fill="#ffffff", cls="blink")
    d.css.append("@keyframes blink{0%,54%{opacity:1}55%,100%{opacity:0}}.blink{animation:blink 1.1s steps(1,end) infinite}")
    d.text_shadow(24 * S, 11 * S, label, scale=S, shadow=sh, dy=S)
    d.save(f"btn-{name}.svg")


def main():
    os.makedirs(OUT, exist_ok=True)
    print("building assets:")
    build_hero()
    for n in NAV_STYLES:
        build_button(n)
        build_header(n)
    build_card(
        "card-haywire.svg",
        "hw",
        "HAYWIRE",
        "No.001",
        "the Hay-Price Pokémon",
        [("HT", "LIVE / REPO PRIVATE"), ("WT", "6 SUBSYSTEMS")],
        ["GRASS", "ELECTRIC"],
        "Scrapes hay auction reports on a cron and publishes a weekly "
        "price digest. Keeps every record behind deny-all RLS, and refuses "
        "to ship when a single policy test comes back red.",
        "haywireag.com",
        WHEAT,
        {"#": "#f8d048"},
    )
    build_card(
        "card-agentfusion.svg",
        "af",
        "AGENT-FUSION",
        "No.002",
        "the Orchestration Pokémon",
        [("HT", "MIT LICENSED"), ("WT", "PYTHON 3.11+")],
        ["GHOST", "PSYCHIC"],
        "Routes a coding task to whichever agent suits it, then makes the "
        "two cooperate. Each one works from a Markdown and YAML skill "
        "profile it will not act outside of.",
        "github.com/ColeGlasgow/agent-fusion",
        ROBOT,
        {"#": "#d8dce8", "o": "#5878c8"},
    )
    build_bag()
    build_trainer()
    build_divider()
    build_save()
    build_contact("email", "EMAIL", "#e878a0", "#c04878", "#8a2c50", "rgba(90,20,50,.55)")
    build_contact("site", "HAYWIREAG.COM", "#5880d8", "#3050a0", "#1c3c78", "rgba(10,30,80,.55)")
    print("done.")


if __name__ == "__main__":
    main()
