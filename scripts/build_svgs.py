#!/usr/bin/env python3
"""Builds every animated SVG used by the profile README.

Run from the repo root:  python3 scripts/build_svgs.py   (needs: pip install fonttools brotli)
Text, links and colors all live in this file. Animation is SMIL inside each SVG,
so it plays on github.com without scripts. Fonts: Mona Sans and Mona Sans Mono
(SIL Open Font License, see fonts/OFL.txt), subset and embedded per SVG.
"""
import base64
import html
import io
import math
import os
import random

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
FONT_DIR = os.path.join(ROOT, "fonts")

# palette
BG, INK, MUTED, RULE, FAINT = "#e9edec", "#000000", "#58635b", "#d2d9d4", "#dde3e0"
GREEN, GREEN_D, BRIGHT, MINT = "#08872b", "#0d6731", "#01b000", "#5fed83"
PURPLE, LILAC, ORANGE, YELLOW, PINK, NIGHT = "#583af7", "#ae85ff", "#c05200", "#bba00a", "#f73678", "#180e27"
BTN_GRAY, BTN_EDGE = "#dfe4e2", "#c3cbc6"

FAMILIES = {
    "s": ("BYs", "MonaSans-Medium.ttf"),
    "b": ("BYb", "MonaSans-SemiBold.ttf"),
    "w": ("BYw", "MonaSansExpanded-Black.ttf"),
    "m": ("BYm", "MonaSansMono-Regular.ttf"),
    "mm": ("BYmm", "MonaSansMono-Medium.ttf"),
}
FALLBACK = {"s": "'Segoe UI',Arial,sans-serif", "b": "'Segoe UI',Arial,sans-serif", "w": "'Arial Black',Arial,sans-serif",
            "m": "Consolas,Menlo,monospace", "mm": "Consolas,Menlo,monospace"}
CHARS = [chr(c) for c in range(32, 127)] + list("·’")
POOL = "!<>-_\\/[]{}=+*^?#@$%&ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz0123456789"

_fonts, _b64 = {}, {}


def font(cls):
    if cls not in _fonts:
        _fonts[cls] = TTFont(os.path.join(FONT_DIR, FAMILIES[cls][1]))
    return _fonts[cls]


def b64(cls):
    if cls not in _b64:
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "calt"]
        f = subset.load_font(os.path.join(FONT_DIR, FAMILIES[cls][1]), opts)
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=[ord(c) for c in CHARS])
        sub.subset(f)
        buf = io.BytesIO()
        subset.save_font(f, buf, opts)
        _b64[cls] = base64.b64encode(buf.getvalue()).decode()
    return _b64[cls]


def measure(s, cls, size):
    f = font(cls)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in s) * size / upm


def cap(cls):
    f = font(cls)
    return f["OS/2"].sCapHeight / f["head"].unitsPerEm


def wrap(s, cls, size, maxw):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if measure(trial, cls, size) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def esc(s):
    return html.escape(s, quote=True)


def n(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


# ------------------------------------------------------------------ svg builder
class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.used, self.defs, self.body = set(), [], []

    def add(self, *parts):
        self.body.extend(parts)

    def text(self, x, y, s, size, cls="s", fill=INK, anchor=None, extra="", inner=""):
        self.used.add(cls)
        a = f' text-anchor="{anchor}"' if anchor else ""
        return f'<text class="{cls}" x="{n(x)}" y="{n(y)}" font-size="{size}" fill="{fill}"{a}{extra}>{esc(s)}{inner}</text>'

    def para(self, x, y, s, size, maxw, lh, cls="s", fill=INK):
        out = []
        for i, line in enumerate(wrap(s, cls, size, maxw)):
            out.append(self.text(x, y + i * lh, line, size, cls, fill))
        return "".join(out), len(wrap(s, cls, size, maxw))

    def save(self, name, title):
        css = "".join(
            f"@font-face{{font-family:{FAMILIES[c][0]};src:url(data:font/woff2;base64,{b64(c)}) format('woff2')}}"
            for c in sorted(self.used)
        ) + "".join(f".{c}{{font-family:{FAMILIES[c][0]},{FALLBACK[c]}}}" for c in sorted(self.used))
        doc = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title><style>{css}</style>'
            f"<defs>{''.join(self.defs)}</defs>"
            f'<rect width="{self.w}" height="{self.h}" fill="{BG}"/>{"".join(self.body)}'
            f'<rect x=".5" y=".5" width="{self.w - 1}" height="{self.h - 1}" fill="none" stroke="{RULE}"/></svg>\n'
        )
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(doc)
        print(f"  {name:<24} {len(doc) / 1024:6.1f} KB")


# ------------------------------------------------------------------ animation helpers
def vis(windows, cycle):
    """Discrete visibility: visible inside each (start, end) window of the cycle."""
    ev = []
    for a, b in windows:
        ev += [(max(a, 0), "visible"), (min(b, cycle), "hidden")]
    ev.sort()
    kts, vals = [0.0], ["hidden"]
    for t, v in ev:
        kt = round(t / cycle, 5)
        if kt >= 1:
            break
        if kt <= kts[-1]:
            vals[-1] = v
            continue
        kts.append(kt)
        vals.append(v)
    return (f'<animate attributeName="visibility" calcMode="discrete" dur="{cycle}s" repeatCount="indefinite" '
            f'values="{";".join(vals)}" keyTimes="{";".join(str(k) for k in kts)}"/>')


def keyed(attr, pts, cycle, discrete=False):
    """Animate attr through (time, value) points; times in seconds within the cycle."""
    kts, vals = [], []
    for t, v in [(0.0, pts[0][1])] + pts + [(cycle, pts[-1][1])]:
        kt = round(min(max(t, 0), cycle) / cycle, 5)
        if kts and kt <= kts[-1]:
            vals[-1] = v
            continue
        kts.append(kt)
        vals.append(v)
    kts[-1] = 1
    mode = ' calcMode="discrete"' if discrete else ""
    vs = ";".join(v if isinstance(v, str) else n(v) for v in vals)
    return f'<animate attributeName="{attr}"{mode} dur="{cycle}s" repeatCount="indefinite" values="{vs}" keyTimes="{";".join(str(k) for k in kts)}"/>'


def scramble(svg, x, y, s, size, fill, t0, cycle, seed, cls="m", anchor=None, frames=12, dt=0.055):
    """Mono label that decodes from random glyphs into its final text."""
    rnd = random.Random(seed)
    out = []
    end = t0 + frames * dt
    for k in range(frames):
        reveal = int(len(s) * k / frames)
        fs = "".join(c if (i < reveal or c == " ") else rnd.choice(POOL) for i, c in enumerate(s))
        out.append(svg.text(x, y, fs, size, cls, fill, anchor, ' visibility="hidden"', vis([(t0 + k * dt, t0 + (k + 1) * dt)], cycle)))
    out.append(svg.text(x, y, s, size, cls, fill, anchor, "", vis([(0, t0), (end, cycle)], cycle)))
    return "".join(out)


def blink_square(x, y, s, color=GREEN):
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{s}" height="{s}" fill="{color}">'
            '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>')


def arrow(x, y, size, color, extra=""):
    """Up-right arrow drawn as strokes, bottom-left corner at (x, y)."""
    s = size
    return (f'<g transform="translate({n(x)} {n(y)})" fill="none" stroke="{color}" stroke-width="{n(s * .14)}" stroke-linecap="square">'
            f'<path d="M0,0 L{n(s)},{n(-s)} M{n(s * .3)},{n(-s)} L{n(s)},{n(-s)} L{n(s)},{n(-s * .7)}"/>{extra}</g>')


CURSOR = "M0,0 L0,21 L5.2,16 L8.8,24 L12.2,22.6 L8.7,14.8 L15.2,14.8 Z"


def ghost_cursor(path_pts, cycle, extra=""):
    vals = ";".join(f"{n(x)},{n(y)}" for _, x, y in path_pts)
    kts = ";".join(str(round(t / cycle, 5)) for t, _, _ in path_pts)
    return (f'<g><path d="{CURSOR}" fill="{INK}" stroke="#fff" stroke-width="1.4" stroke-linejoin="round" transform="scale(1.25)"/>{extra}'
            f'<animateMotion dur="{cycle}s" repeatCount="indefinite" calcMode="linear" values="{vals}" keyTimes="{kts}"/></g>')


def ease_path(waypoints, cycle, step=0.1):
    """waypoints: (time, x, y); smoothstep between them, sampled every `step` seconds."""
    pts = []
    for (t1, x1, y1), (t2, x2, y2) in zip(waypoints, waypoints[1:]):
        steps = max(1, int((t2 - t1) / step))
        for k in range(steps):
            u = k / steps
            e = u * u * (3 - 2 * u)
            pts.append((t1 + (t2 - t1) * u, x1 + (x2 - x1) * e, y1 + (y2 - y1) * e))
    pts.append(waypoints[-1])
    if pts[0][0] > 0:
        pts.insert(0, (0, pts[0][1], pts[0][2]))
    if pts[-1][0] < cycle:
        pts.append((cycle, pts[-1][1], pts[-1][2]))
    return pts


def wordmark(svg, word, x, baseline, size, cycle, start=0.3, hold=8.6, flick=(2, 5), colors=(GREEN, BRIGHT, GREEN)):
    """Giant wide wordmark that assembles from green bars, flickers, then dissolves back."""
    f = font("w")
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    capH = cap("w") * size
    out, cx = [], x
    for i, ch in enumerate(word):
        adv = hmtx[cmap[ord(ch)]][0] * size / upm
        on = start + i * 0.11
        built = on + 0.45
        off = hold + i * 0.06
        bw = size * 0.17
        bx = cx + adv / 2 - bw / 2
        color = colors[i % len(colors)]
        letter_w = [(built, off)]
        bar_w = [(on, built), (off, off + 0.45)]
        if i in flick:
            mid = 4.6 + (i % 3) * 0.7
            letter_w = [(built, mid), (mid + 0.35, off)]
            bar_w.insert(1, (mid, mid + 0.35))
        out.append(
            f'<rect x="{n(bx)}" y="{n(baseline - capH)}" width="{n(bw)}" height="{n(capH)}" fill="{color}" visibility="hidden">'
            + vis(bar_w, cycle)
            + keyed("height", [(on, 0), (on + 0.2, capH)], cycle)
            + keyed("y", [(on, baseline), (on + 0.2, baseline - capH)], cycle)
            + "</rect>"
        )
        out.append(svg.text(cx, baseline, ch, size, "w", INK, None, ' visibility="hidden"', vis(letter_w, cycle)))
        cx += adv
    return "".join(out), cx - x


def fit_size(s, cls, maxw, start):
    size = start
    while measure(s, cls, size) > maxw:
        size -= 1
    return size


# ------------------------------------------------------------------ hero
def hero():
    W, H, cycle = 1200, 600, 12.0
    svg = Svg(W, H)
    nav_h, split = 72, 760
    # nav
    cells = [("about", 226), ("work", 320), ("clients", 406), ("stack", 508), ("contact", 598)]
    svg.add(f'<line x1="0" y1="{nav_h}" x2="{W}" y2="{nav_h}" stroke="{RULE}"/>')
    svg.add(svg.text(26, 46, "bharath.yadav", 22, "b"), blink_square(26 + measure("bharath.yadav", "b", 22) + 6, 30, 12))
    for label, x in cells:
        svg.add(f'<line x1="{x - 16}" y1="0" x2="{x - 16}" y2="{nav_h}" stroke="{RULE}"/>')
        svg.add(svg.text(x, 46, label, 17, "b", GREEN if label == "contact" else INK))
    svg.add(f'<line x1="{cells[-1][1] + measure("contact", "b", 17) + 16}" y1="0" x2="{cells[-1][1] + measure("contact", "b", 17) + 16}" y2="{nav_h}" stroke="{RULE}"/>')
    svg.add(f'<line x1="904" y1="0" x2="904" y2="{nav_h}" stroke="{RULE}"/>')
    svg.add(svg.text(924, 46, "berlin, de", 16, "s", MUTED))
    svg.add(f'<rect x="1000" y="0" width="200" height="{nav_h}" fill="{GREEN}"/>', svg.text(1020, 46, "brande5.com", 17, "b", "#fff"),
            arrow(1150, 46, 11, "#fff"))
    # wordmark
    size = fit_size("BHARATH", "w", 1100, 200)
    wm, _ = wordmark(svg, "BHARATH", 22, 262, size, cycle)
    svg.add(wm)
    svg.add(f'<line x1="0" y1="300" x2="{W}" y2="300" stroke="{RULE}"/><line x1="{split}" y1="300" x2="{split}" y2="{H}" stroke="{RULE}"/>')
    # lower left
    svg.add(scramble(svg, 26, 340, "yadav@berlin", 15, GREEN, 0.4, cycle, 1))
    svg.add(blink_square(26 + measure("yadav@berlin", "m", 15) + 8, 329, 11))
    svg.add(scramble(svg, split - 26, 340, "10+_yrs.exp", 15, GREEN, 0.9, cycle, 2, anchor="end"))
    hs = fit_size("marketer-developer-", "s", split - 52, 66)
    svg.add(svg.text(24, 470, "marketer-developer-", hs, "s", INK, None, ' letter-spacing="-1"'))
    svg.add(svg.text(24, 470 + hs * 1.02, "generalist/", hs, "s", INK, None, ' letter-spacing="-1"'))
    # lower right
    body, _ = svg.para(split + 22, 350, "Senior performance marketer and full-stack developer. Ex Google Operations Center. Founder of Brand E5.",
                       25, W - split - 44, 34, "s", MUTED)
    svg.add(body)
    svg.add(f'<line x1="{split}" y1="478" x2="{W}" y2="478" stroke="{RULE}"/>')
    bx, by, bw, bh = split + 20, 498, W - split - 40, 78
    hover = (5.2, 7.6)
    svg.add(
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="6" fill="{GREEN}">'
        + keyed("fill", [(hover[0], GREEN), (hover[0] + .15, GREEN_D), (hover[1], GREEN_D), (hover[1] + .15, GREEN)], cycle)
        + "</rect>"
    )
    svg.add(svg.text(bx + 18, by + bh - 20, "open to multi-hat roles", 19, "b", "#fff"))
    svg.add(arrow(bx + bw - 34, by + bh - 20, 12, "#fff",
                  f'<animateTransform attributeName="transform" type="translate" additive="sum" dur="{cycle}s" repeatCount="indefinite" '
                  f'values="0 0;0 0;4 -4;4 -4;0 0;0 0" keyTimes="0;{n(hover[0] / cycle)};{n((hover[0] + .2) / cycle)};{n(hover[1] / cycle)};{n((hover[1] + .2) / cycle)};1"/>'))
    path = ease_path([(0, 1230, 640), (3.6, 1230, 640), (5.0, 1020, 540), (7.8, 1060, 548), (9.2, 1240, 470), (12, 1240, 470)], cycle)
    svg.add(ghost_cursor(path, cycle))
    svg.save("hero.svg", "Bharath Yadav: senior performance marketer, full-stack developer, generalist. Ex Google Operations Center. Founder of Brand E5.")


# ------------------------------------------------------------------ hover grid
def grid_panel():
    W, H, cycle = 1200, 560, 14.0
    svg = Svg(W, H)
    split, top, bot, cell = 760, 210, 498, 24
    svg.add(scramble(svg, 26, 46, "approach()", 15, MUTED, 0.5, cycle, 3))
    hs = fit_size("one-person-", "s", split - 52, 62)
    svg.add(svg.text(24, 118, "one-person-", hs, "s", INK, None, ' letter-spacing="-1"'),
            svg.text(24, 118 + hs * 1.02, "full-funnel?", hs, "s", INK, None, ' letter-spacing="-1"'))
    svg.add(f'<line x1="{split}" y1="0" x2="{split}" y2="{top}" stroke="{RULE}"/>')
    body, _ = svg.para(split + 22, 62, "Plan the campaign, build the site it lands on, wire up the tracking and automate the reporting.",
                       24, W - split - 44, 33, "s", MUTED)
    svg.add(body)
    svg.add(f'<line x1="0" y1="{top}" x2="{W}" y2="{top}" stroke="{RULE}"/><line x1="0" y1="{bot}" x2="{W}" y2="{bot}" stroke="{RULE}"/>')
    # grid lines
    svg.defs.append(
        f'<pattern id="gp" x="0" y="{top}" width="{cell}" height="{cell}" patternUnits="userSpaceOnUse">'
        f'<path d="M{cell} 0H0V{cell}" fill="none" stroke="{RULE}" stroke-width="1"/></pattern>'
        '<linearGradient id="gf"><stop offset="0" stop-color="#fff"/><stop offset=".72" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity=".15"/></linearGradient>'
        f'<mask id="gm"><rect x="0" y="{top}" width="{W}" height="{bot - top}" fill="url(#gf)"/></mask>'
    )
    svg.add(f'<rect x="0" y="{top}" width="{W}" height="{bot - top}" fill="url(#gp)" mask="url(#gm)"/>')
    cols, rows = W // cell, (bot - top) // cell
    # ghost cursor path (tip position) on a Lissajous curve over the left 70%
    pts = []
    t = 0.0
    while t <= cycle + 1e-6:
        th = 2 * math.pi * t / cycle
        x = 420 + 360 * math.sin(3 * th + 0.4)
        y = top + 140 + 112 * math.sin(2 * th)
        pts.append((t, x, y))
        t += 0.05
    trail_colors = [GREEN, MINT, PURPLE, PINK, BRIGHT, LILAC]
    visits = {}
    last = None
    for t, x, y in pts:
        c = (int(x // cell), int((y - top) // cell))
        if c != last:
            visits.setdefault(c, []).append(t)
            last = c
    fade = 1.6
    cells_svg = []
    for (cx, cy), times in visits.items():
        if not (0 <= cx < cols and 0 <= cy < rows):
            continue
        times = sorted(times)
        kept = []
        for v in times:
            if not kept or v > kept[-1] + fade:
                kept.append(v)
        p = [(0.0, 0.0)]
        for v in kept:
            p += [(v, 0.0), (v + 0.04, 0.95), (min(v + fade, cycle - 0.001), 0.0)]
        color = trail_colors[int(kept[0] / (cycle / len(trail_colors))) % len(trail_colors)]
        cells_svg.append(
            f'<rect x="{cx * cell + 1}" y="{top + cy * cell + 1}" width="{cell - 1}" height="{cell - 1}" fill="{color}" opacity="0">'
            + keyed("opacity", p, cycle) + "</rect>"
        )
    svg.add("".join(cells_svg))
    # pixel growth chart on the right
    heights = [2, 3, 3, 5, 6, 8, 10, 11]
    c0 = 40
    order = 0
    chart = []
    for i, hgt in enumerate(heights):
        for r in range(hgt):
            on = 1.0 + order * 0.045
            order += 1
            x = (c0 + i * 2) * cell + 1
            y = top + (rows - 1 - r) * cell + 1
            color = MINT if r == hgt - 1 else (GREEN if r < hgt - 3 else BRIGHT)
            chart.append(f'<rect x="{x}" y="{y}" width="{cell * 2 - 2}" height="{cell - 1}" fill="{color}" visibility="hidden">'
                         + vis([(on, 11.6 + i * 0.08)], cycle) + "</rect>")
    svg.add("".join(chart))
    svg.add(ghost_cursor(pts, cycle))
    # bottom bar
    svg.add(scramble(svg, 26, bot + 38, "trail.render(); ", 15, INK, 1.2, cycle, 4))
    svg.add(blink_square(26 + measure("trail.render(); ", "m", 15), bot + 27, 11, MINT))
    svg.add(scramble(svg, W - 26, bot + 38, "growth.chart()", 15, GREEN, 2.0, cycle, 5, anchor="end"))
    svg.save("grid.svg", "One person, full funnel: plan the campaign, build the site, wire up tracking, automate reporting")


# ------------------------------------------------------------------ functions
def functions():
    W, H, cycle = 1200, 590, 6.0
    svg = Svg(W, H)
    head = 120
    svg.add(svg.text(24, 82, "what-i-do/", 54, "s", INK, None, ' letter-spacing="-1"'))
    svg.add(scramble(svg, W - 26, 80, "3 functions, 1 person", 15, MUTED, 0.6, cycle, 6, anchor="end"))
    svg.add(f'<line x1="0" y1="{head}" x2="{W}" y2="{head}" stroke="{RULE}"/>')
    cols = [
        ("dev.market()", "Google Ads, Meta Ads, SEM, SEO and analytics. Campaigns planned around intent and measured to the click.", (GREEN, PINK)),
        ("dev.build()", "Full-stack apps in .NET, C# and Angular on PostgreSQL. HRMS, rental platforms, CRMs and client sites.", (YELLOW, ORANGE)),
        ("dev.automate()", "n8n workflows and local LLMs on Ollama that turn raw data into reports, with no human in the loop.", (PURPLE, LILAC)),
    ]
    tile_h = 230
    rnd = random.Random(21)
    for i, (label, text, (base, acc)) in enumerate(cols):
        ox = i * 400
        if i:
            svg.add(f'<line x1="{ox}" y1="{head}" x2="{ox}" y2="{H}" stroke="{RULE}"/>')
        cw, ch = 50, tile_h / 4
        steps = 12
        frames = []
        for k in range(steps):
            fr = [[rnd.random() < 0.3 for _ in range(8)] for _ in range(4)]
            if k % 3 == 0:  # occasional plus shapes, like pixel signage
                px, py = rnd.randrange(1, 7), rnd.randrange(1, 3)
                for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
                    fr[py + dy][px + dx] = True
            frames.append(fr)
        for r in range(4):
            for c in range(8):
                vals = [(k * cycle / steps, acc if frames[k][r][c] else base) for k in range(steps)]
                svg.add(f'<rect x="{ox + c * cw}" y="{n(head + r * ch)}" width="{cw}" height="{n(ch)}" fill="{base}">'
                        + keyed("fill", vals, cycle, discrete=True) + "</rect>")
        svg.add(f'<line x1="0" y1="{head + tile_h}" x2="{W}" y2="{head + tile_h}" stroke="{RULE}"/>')
        svg.add(scramble(svg, ox + 24, head + tile_h + 44, label, 15, MUTED, 0.3 + i * 0.4, cycle, 10 + i))
        body, _ = svg.para(ox + 24, head + tile_h + 92, text, 23, 352, 31, "s", INK)
        svg.add(body)
    svg.save("functions.svg", "What I do: marketing (Google Ads, Meta Ads, SEM, SEO), building (.NET, C#, Angular, PostgreSQL), automating (n8n, Ollama)")


# ------------------------------------------------------------------ experience
def experience():
    rows = [
        ("google-operations-center/", "Digital Media Consultant", None),
        ("genpact/", "", None),
        ("harphil/", "Operations Manager", None),
        ("brand-e5/", "Founder, since 2016", "now"),
    ]
    head, rh = 120, 96
    W, H = 1200, head + rh * len(rows)
    step = 2.2
    cycle = step * len(rows)
    svg = Svg(W, H)
    svg.add(svg.text(24, 82, "where-i-worked/", 54, "s", INK, None, ' letter-spacing="-1"'))
    svg.add(scramble(svg, W - 26, 80, "10+ years, many hats", 15, GREEN, 0.4, cycle, 14, anchor="end"))
    # sliding hover highlight
    ys = [(k * step, head + k * rh) for k in range(len(rows))]
    svg.add(f'<rect x="0" y="{head}" width="{W}" height="{rh}" fill="#ffffff" opacity=".75">' + keyed("y", ys, cycle, discrete=True) + "</rect>")
    svg.add(f'<rect x="0" y="{head}" width="6" height="{rh}" fill="{GREEN}">' + keyed("y", ys, cycle, discrete=True) + "</rect>")
    for k, (slug, role, badge) in enumerate(rows):
        y0 = head + k * rh
        svg.add(f'<line x1="0" y1="{y0}" x2="{W}" y2="{y0}" stroke="{RULE}"/>')
        svg.add(svg.text(32, y0 + 62, slug, 38, "s", INK, None, ' letter-spacing="-.5"'))
        if badge:
            bx = 32 + measure(slug, "s", 38) + 16
            svg.add(f'<rect x="{n(bx)}" y="{y0 + 34}" width="56" height="30" rx="4" fill="{MINT}"/>',
                    svg.text(bx + 28, y0 + 55, badge, 14, "mm", NIGHT, "middle"))
        if role:
            svg.add(svg.text(1110, y0 + 58, role, 21, "s", MUTED, "end"))
        on, offt = k * step, (k + 1) * step
        vals, kts = [], []
        if on > 0:
            vals.append("0 0")
            kts.append(0)
        vals.append("5 -5")
        kts.append(round(on / cycle, 5))
        if offt < cycle:
            vals.append("0 0")
            kts.append(round(offt / cycle, 5))
        svg.add(arrow(1140, y0 + 60, 14, INK,
                      f'<animateTransform attributeName="transform" type="translate" additive="sum" dur="{cycle}s" repeatCount="indefinite" calcMode="discrete" '
                      f'values="{";".join(vals)}" keyTimes="{";".join(str(k) for k in kts)}"/>'))
    svg.save("experience.svg", "Where I worked: Google Operations Center (Digital Media Consultant), Genpact, Harphil (Operations Manager), Brand E5 (Founder, since 2016)")


# ------------------------------------------------------------------ toolkit
def toolkit():
    tools = [
        ("Google Ads", GREEN), ("Meta Ads", GREEN), ("SEM / PPC", GREEN), ("SEO", GREEN), ("Google Analytics", GREEN), ("Content strategy", GREEN),
        ("C#", PURPLE), (".NET Core", PURPLE), ("Angular", PURPLE), ("TypeScript", PURPLE), ("JavaScript", PURPLE), ("Python", PURPLE),
        ("PostgreSQL", ORANGE), ("SQL Server", ORANGE), ("AWS", ORANGE), ("Firebase", ORANGE), ("Linux", ORANGE), ("HTML / CSS", ORANGE),
        ("n8n", PINK), ("Ollama", PINK), ("LLM pipelines", PINK), ("Salesforce", PINK), ("Social media", GREEN), ("Operations", PINK),
    ]
    head, cw, ch, ncol = 120, 200, 88, 6
    nrow = len(tools) // ncol
    W, H, cycle = 1200, head + ch * nrow, 9.6
    svg = Svg(W, H)
    svg.add(svg.text(24, 82, "toolkit/", 54, "s", INK, None, ' letter-spacing="-1"'))
    legend = [("marketing", GREEN), ("code", PURPLE), ("data + cloud", ORANGE), ("automation", PINK)]
    x = W - 26
    for label, color in reversed(legend):
        w = measure(label, "m", 14)
        svg.add(svg.text(x, 80, label, 14, "m", MUTED, "end"), f'<rect x="{n(x - w - 18)}" y="69" width="10" height="10" fill="{color}"/>')
        x -= w + 40
    # wandering highlight
    rnd = random.Random(8)
    cur, walk = (0, 0), []
    for k in range(16):
        walk.append((k * 0.6, cur))
        opts = [(cur[0] + dx, cur[1] + dy) for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)] if 0 <= cur[0] + dx < ncol and 0 <= cur[1] + dy < nrow]
        cur = rnd.choice(opts)
    svg.add(f'<rect x="0" y="{head}" width="{cw}" height="{ch}" fill="{MINT}" opacity=".6">'
            + keyed("x", [(t, c * cw) for t, (c, r) in walk], cycle, True)
            + keyed("y", [(t, head + r * ch) for t, (c, r) in walk], cycle, True) + "</rect>")
    for i, (label, color) in enumerate(tools):
        c, r = i % ncol, i // ncol
        x0, y0 = c * cw, head + r * ch
        svg.add(f'<rect x="{x0 + 20}" y="{y0 + 22}" width="9" height="9" fill="{color}"/>')
        svg.add(scramble(svg, x0 + 20, y0 + 64, label, min(18, fit_size(label, "mm", cw - 36, 18)), INK, 0.2 + i * 0.07, cycle, 100 + i, cls="mm", frames=8))
    for c in range(ncol + 1):
        svg.add(f'<line x1="{c * cw}" y1="{head}" x2="{c * cw}" y2="{H}" stroke="{RULE}"/>')
    for r in range(nrow + 1):
        svg.add(f'<line x1="0" y1="{head + r * ch}" x2="{W}" y2="{head + r * ch}" stroke="{RULE}"/>')
    svg.save("toolkit.svg", "Toolkit: " + ", ".join(t for t, _ in tools))


# ------------------------------------------------------------------ section header
def header(name, slug, label, seed):
    W, H, cycle = 1200, 120, 8.0
    svg = Svg(W, H)
    svg.add(svg.text(24, 82, slug, 54, "s", INK, None, ' letter-spacing="-1"'))
    svg.add(scramble(svg, W - 26, 80, label, 15, GREEN, 0.5, cycle, seed, anchor="end"))
    svg.add(f'<rect x="0" y="{H - 3}" width="140" height="3" fill="{GREEN}">'
            f'<animate attributeName="x" values="-140;{W}" dur="3.6s" repeatCount="indefinite"/></rect>')
    svg.save(name, slug)


# ------------------------------------------------------------------ build cards
def build_card(name, slug, label, desc, tags, seed, link=True):
    W, H, cycle = 600, 340, 7.0
    svg = Svg(W, H)
    svg.add(scramble(svg, 28, 46, label, 15, GREEN, 0.4, cycle, seed))
    svg.add(blink_square(28 + measure(label, "m", 15) + 8, 35, 11))
    rnd = random.Random(seed)
    palette = [GREEN, MINT, PURPLE, PINK, YELLOW, ORANGE, LILAC]
    for r in range(2):
        for c in range(3):
            vals = [(k * 0.5, rnd.choice(palette + [BG, BG])) for k in range(14)]
            svg.add(f'<rect x="{W - 120 + c * 16}" y="{24 + r * 16}" width="14" height="14" fill="{BG}">' + keyed("fill", vals, cycle, True) + "</rect>")
    if link:
        svg.add(arrow(W - 52, 50, 16, INK,
                      f'<animateTransform attributeName="transform" type="translate" additive="sum" values="0 0;4 -4;0 0" dur="1.8s" repeatCount="indefinite"/>'))
    svg.add(f'<line x1="0" y1="76" x2="{W}" y2="76" stroke="{RULE}"/>')
    svg.add(svg.text(26, 142, slug, fit_size(slug, "s", W - 52, 50), "s", INK, None, ' letter-spacing="-1"'))
    body, lines = svg.para(28, 188, desc, 20, W - 56, 28, "s", MUTED)
    svg.add(body)
    x = 28
    for t in tags:
        w = measure(t, "m", 13) + 24
        svg.add(f'<rect x="{n(x)}" y="{H - 58}" width="{n(w)}" height="30" rx="4" fill="none" stroke="{BTN_EDGE}"/>',
                svg.text(x + 12, H - 38, t, 13, "m", INK))
        x += w + 8
    svg.save(name, f"{slug} {desc}")


# ------------------------------------------------------------------ client cards
def client_card(name, domain, industry, work, seed, mine=False):
    W, H, cycle = 600, 160, 8.0
    svg = Svg(W, H)
    svg.add(f'<rect x="0" y="0" width="6" height="{H}" fill="{GREEN if mine else NIGHT}"/>')
    svg.add(svg.text(32, 64, domain, fit_size(domain, "s", 430, 32), "s", INK, None, ' letter-spacing="-.5"'))
    svg.add(scramble(svg, 33, 100, industry.lower(), 14, GREEN, 0.3 + (seed % 5) * 0.3, cycle, seed))
    svg.add(svg.text(33, 134, work, 17, "s", MUTED))
    if mine:
        svg.add(f'<rect x="{W - 132}" y="26" width="64" height="28" rx="4" fill="{MINT}"/>', svg.text(W - 100, 46, "mine", 14, "mm", NIGHT, "middle"))
    svg.add(arrow(W - 44, 50, 14, INK,
                  f'<animateTransform attributeName="transform" type="translate" additive="sum" values="0 0;4 -4;0 0" dur="1.8s" begin="{-seed % 7 * .2}s" repeatCount="indefinite"/>'))
    svg.save(name, f"{domain}: {industry}. {work}")


# ------------------------------------------------------------------ certifications
def certs():
    items = [
        ("engineering", "Full Stack .NET", "with Angular", PURPLE),
        ("google", "Google Ads Search", "Professional", GREEN),
        ("google", "Google Analytics", "Professional", GREEN),
        ("operations", "Lean Six Sigma", "Yellow Belt", ORANGE),
        ("management", "Harvard Mentor", "Project Management", PINK),
    ]
    head, cw, ch = 120, 240, 180
    W, H, cycle = 1200, head + ch, 7.5
    svg = Svg(W, H)
    svg.add(svg.text(24, 82, "credentials/", 54, "s", INK, None, ' letter-spacing="-1"'))
    svg.add(scramble(svg, W - 26, 80, "certified()", 15, GREEN, 0.5, cycle, 40, anchor="end"))
    svg.add(f'<rect x="0" y="{head}" width="{cw}" height="{ch}" fill="#ffffff" opacity=".75">'
            + keyed("x", [(k * 1.5, k * cw) for k in range(5)], cycle, True) + "</rect>")
    svg.add(f'<line x1="0" y1="{head}" x2="{W}" y2="{head}" stroke="{RULE}"/>')
    for i, (cat, l1, l2, color) in enumerate(items):
        x0 = i * cw
        if i:
            svg.add(f'<line x1="{x0}" y1="{head}" x2="{x0}" y2="{H}" stroke="{RULE}"/>')
        svg.add(f'<rect x="{x0 + 22}" y="{head + 26}" width="10" height="10" fill="{color}"/>')
        svg.add(scramble(svg, x0 + 40, head + 36, cat, 13, MUTED, 0.3 + i * 0.25, cycle, 41 + i))
        svg.add(svg.text(x0 + 22, head + 112, l1, fit_size(l1, "b", cw - 40, 21), "b", INK))
        svg.add(svg.text(x0 + 22, head + 142, l2, fit_size(l2, "s", cw - 40, 19), "s", MUTED))
    svg.save("certs.svg", "Credentials: " + "; ".join(f"{a} {b}" for _, a, b, _ in items))


# ------------------------------------------------------------------ contact + buttons + footer
def contact():
    W, H, cycle, split = 1200, 400, 10.0, 760
    svg = Svg(W, H)
    svg.add(scramble(svg, 26, 46, "contact()", 15, GREEN, 0.4, cycle, 50))
    svg.add(blink_square(26 + measure("contact()", "m", 15) + 8, 35, 11))
    hs = fit_size("lets-build-", "s", split - 52, 92)
    svg.add(svg.text(22, 186, "lets-build-", hs, "s", INK, None, ' letter-spacing="-2"'),
            svg.text(22, 186 + hs * 1.0, "something/", hs, "s", INK, None, ' letter-spacing="-2"'))
    svg.add(f'<line x1="{split}" y1="0" x2="{split}" y2="{H}" stroke="{RULE}"/>')
    body, _ = svg.para(split + 22, 72, "Open to roles that need someone who wears many hats: marketing, engineering, automation and operations.",
                       24, W - split - 44, 33, "s", MUTED)
    svg.add(body)
    body2, _ = svg.para(split + 22, 262, "Or bring your project to Brand E5.", 24, W - split - 44, 33, "s", INK)
    svg.add(body2)
    svg.save("contact.svg", "Let's build something. Open to multi-hat roles across marketing, engineering, automation and operations. Projects welcome at Brand E5.")


def button(name, label, primary, seed):
    W, H = 392, 80
    svg = Svg(W, H)
    fill, color = (GREEN, "#fff") if primary else (BTN_GRAY, INK)
    svg.add(f'<rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="6" fill="{fill}" stroke="{GREEN_D if primary else BTN_EDGE}"/>')
    svg.add(svg.text(24, H - 24, label, 18, "b", color))
    svg.add(arrow(W - 40, H - 24, 12, color,
                  f'<animateTransform attributeName="transform" type="translate" additive="sum" values="0 0;4 -4;0 0" dur="1.6s" begin="{-seed * .4}s" repeatCount="indefinite"/>'))
    svg.save(name, label)


def footer():
    W, H, cycle = 1200, 290, 12.0
    svg = Svg(W, H)
    size = fit_size("YADAV", "w", 1150, 260)
    wm, _ = wordmark(svg, "YADAV", 22, 226, size, cycle, start=0.5, hold=9.0, flick=(1, 3), colors=(GREEN, BRIGHT, PURPLE))
    svg.add(wm)
    svg.add(f'<line x1="0" y1="250" x2="{W}" y2="250" stroke="{RULE}"/>')
    svg.add(svg.text(24, 276, "bharath yadav · berlin · brande5.com", 13, "m", MUTED))
    svg.add(svg.text(W - 24, 276, "pure svg, zero javascript", 13, "m", MUTED, "end"))
    svg.save("footer.svg", "Yadav")


if __name__ == "__main__":
    for f in os.listdir(OUT) if os.path.isdir(OUT) else []:
        if f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    print("Building SVGs into assets/")
    hero()
    grid_panel()
    functions()
    experience()
    toolkit()
    header("head-builds.svg", "featured-builds/", "shipped.list()", 60)
    build_card("build-wgfinder.svg", "wgfinder/", "flatsingermany.com",
               "Rental platform for German cities: listings, visit bookings, contracts, complaints and payments.",
               ["Angular", ".NET Core", "PostgreSQL", "AWS"], 61)
    build_card("build-visionm.svg", "visionm-hrms/", "visionm.in",
               "Enterprise HR system: attendance, leave, payroll, recruitment and training, with role-based access.",
               [".NET Web API", "Angular", "PostgreSQL", "JWT"], 62)
    build_card("build-ai.svg", "ai-pipelines/", "n8n + ollama",
               "Workflows that run data through local LLMs (Hermes, Mistral) for private, offline extraction and reporting.",
               ["n8n", "Ollama", "Python", "REST"], 63, link=False)
    build_card("build-crm.svg", "internal-crm/", "operations",
               "Task assignment, workflow automation and reporting, wired into Salesforce Service Cloud for routing and SLAs.",
               [".NET Core", "Angular", "SQL Server", "Salesforce"], 64, link=False)
    header("head-clients.svg", "client-work/", "built.and.marketed()", 70)
    clients = [
        ("brande5.com", "Digital marketing, web and AI", "My company: brand, website, growth", True),
        ("flatsingermany.com", "Real estate and rentals", "Full-stack app, booking engine, payments", False),
        ("dhanalakshmigroup.com", "Construction and interiors", "Website design and development, SEO", False),
        ("vdesignss.com", "Branding and signage", "Website build, digital marketing", False),
        ("shizconlogistics.com", "Logistics and transport", "Corporate website, content marketing", False),
        ("sukridha.com", "Business services", "Planning, deployment, marketing", False),
        ("harphil.com", "Corporate services", "Website, email domain, digital presence", False),
        ("ayattih.com", "Business services", "Setup, management, marketing", False),
    ]
    for i, (d, ind, work, mine) in enumerate(clients):
        client_card(f"client-{i + 1}.svg", d, ind, work, 71 + i, mine)
    header("head-activity.svg", "github-activity/", "live.stats()", 80)
    certs()
    contact()
    button("btn-linkedin.svg", "linkedin", True, 1)
    button("btn-email.svg", "email me", False, 2)
    button("btn-brande5.svg", "brande5.com", False, 3)
    footer()
