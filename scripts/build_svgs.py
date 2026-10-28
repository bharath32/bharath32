#!/usr/bin/env python3
"""Builds every animated SVG used by the profile README.

Run from the repo root:  python3 scripts/build_svgs.py
Edit the text in this file (roles, bullets, skills, certs) and re-run.
All animation is SMIL inside the SVG, so it plays on github.com without scripts.
"""
import html
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

SANS = "'Segoe UI', Inter, Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, 'Liberation Mono', Consolas, monospace"

CARD, EDGE = "#0b1020", "#1f2747"
TEXT, SOFT, MUTED, DIM = "#eef1fb", "#c3cbe6", "#9aa4c7", "#5b6688"
VIOLET, CYAN, PINK, AMBER, GREEN = "#7c5cff", "#22d3ee", "#ff4d8d", "#ffb547", "#3ddc97"


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(s, quote=True)


def n(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def write(name, w, h, title, body):
    doc = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title>"
        f"<style>text{{font-family:{SANS}}}.m{{font-family:{MONO}}}</style>"
        f"{body}</svg>\n"
    )
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"  {name:<22} {len(doc)/1024:6.1f} KB")


def disc(attr, pts, cycle):
    """Discrete SMIL animation from (time, value) points within one cycle."""
    vals, kts = [], []
    for t, v in [(0.0, pts[0][1])] + pts:
        kt = round(t / cycle, 5)
        if kts and kt <= kts[-1]:
            vals[-1] = v
            continue
        kts.append(kt)
        vals.append(v)
    if kts[-1] < 1:
        kts.append(1)
        vals.append(vals[0])
    return (
        f'<animate attributeName="{attr}" calcMode="discrete" dur="{cycle}s" repeatCount="indefinite" '
        f'values="{";".join(n(v) for v in vals)}" keyTimes="{";".join(str(k) for k in kts)}"/>'
    )


def typing(count, base, unit, t0, t_type, t_end, t_del=0.0):
    """Points for revealing `count` characters, holding, then deleting."""
    pts = [(0.0, base)]
    for k in range(count + 1):
        pts.append((t0 + t_type * k / max(count, 1), base + k * unit))
    if t_del:
        for k in range(count - 1, -1, -1):
            pts.append((t_end + t_del * (count - k) / count, base + k * unit))
    else:
        pts.append((t_end, base))
    return pts


def window(t_on, t_off, cycle, fade=0.25, lo=0, hi=1, attr="opacity"):
    keys = [0, t_on, t_on + fade, t_off, min(t_off + fade, cycle - 0.01), cycle]
    vals = [lo, lo, hi, hi, lo, lo]
    return (
        f'<animate attributeName="{attr}" dur="{cycle}s" repeatCount="indefinite" '
        f'values="{";".join(n(v) for v in vals)}" '
        f'keyTimes="{";".join(str(round(k / cycle, 4)) for k in keys)}"/>'
    )


def mono_text(x, y, s, color, size, cw, weight=None, extra=""):
    w = f' font-weight="{weight}"' if weight else ""
    return (
        f'<text class="m" x="{n(x)}" y="{n(y)}" font-size="{size}" fill="{color}"{w} '
        f'textLength="{n(len(s) * cw)}" lengthAdjust="spacingAndGlyphs"{extra}>{esc(s)}</text>'
    )


def segs(x0, y, parts, size, cw):
    """Render (text, color[, weight]) parts on a monospace grid; pure spaces only advance."""
    out, col = [], 0
    for p in parts:
        s, color = p[0], p[1]
        weight = p[2] if len(p) > 2 else None
        lead = len(s) - len(s.lstrip(" "))
        body = s.strip(" ")
        if body:
            out.append(mono_text(x0 + (col + lead) * cw, y, body, color, size, cw, weight))
        col += len(s)
    return "".join(out)


def blur(fid, sd):
    return (
        f'<filter id="{fid}" x="-80%" y="-80%" width="260%" height="260%">'
        f'<feGaussianBlur stdDeviation="{sd}"/></filter>'
    )


def particles(w, h, count, seed, color="#ffffff"):
    rnd = random.Random(seed)
    out = []
    for _ in range(count):
        x, y = rnd.uniform(10, w - 10), rnd.uniform(20, h - 10)
        r = rnd.uniform(0.7, 2.1)
        d = rnd.uniform(4, 9)
        b = -rnd.uniform(0, d)
        out.append(
            f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="{color}" opacity="0">'
            f'<animate attributeName="cy" values="{n(y)};{n(y - 34)}" dur="{n(d)}s" begin="{n(b)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;.85;0" dur="{n(d)}s" begin="{n(b)}s" repeatCount="indefinite"/>'
            f"</circle>"
        )
    return "".join(out)


def grid(pid, w, h, size=44, alpha="0b"):
    return (
        f'<pattern id="{pid}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">'
        f'<path d="M{size} 0H0V{size}" fill="none" stroke="#ffffff{alpha}" stroke-width="1"/>'
        f'<animateTransform attributeName="patternTransform" type="translate" from="0 0" to="{size} {size}" dur="9s" repeatCount="indefinite"/>'
        f"</pattern>"
    )


def orb(cx, cy, r, color, dx, dy, dur, op=0.38, fid="blur"):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="{op}" filter="url(#{fid})">'
        f'<animate attributeName="cx" values="{cx};{cx + dx};{cx}" dur="{dur}s" repeatCount="indefinite"/>'
        f'<animate attributeName="cy" values="{cy};{cy + dy};{cy}" dur="{dur}s" repeatCount="indefinite"/>'
        f"</circle>"
    )


def card_frame(w, h, rx, cid):
    return (
        f'<clipPath id="{cid}"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>'
    )


# ---------------------------------------------------------------- hero
def hero():
    W, H = 1200, 440
    roles = ["Senior Performance Marketer", "Full-Stack Developer", "AI Automation Builder", "Founder of Brand E5"]
    slot, cycle = 5.0, 5.0 * len(roles)
    rx0, ry, size, cw = 106, 262, 32, 19.2

    defs = [
        blur("blur", 64),
        blur("soft", 14),
        grid("g", W, H),
        card_frame(W, H, 28, "clip"),
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#060914"/><stop offset="1" stop-color="#0d1330"/></linearGradient>',
        '<radialGradient id="fade" cx=".5" cy=".45" r=".7"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>',
        '<mask id="gm"><rect width="1200" height="440" fill="url(#fade)"/></mask>',
        f'<linearGradient id="name" gradientUnits="userSpaceOnUse" x1="70" y1="0" x2="640" y2="0" spreadMethod="reflect">'
        f'<stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#c8bcff"/><stop offset=".75" stop-color="{CYAN}"/><stop offset="1" stop-color="#ffffff"/>'
        f'<animate attributeName="x1" values="70;1210" dur="7s" repeatCount="indefinite"/>'
        f'<animate attributeName="x2" values="640;1780" dur="7s" repeatCount="indefinite"/></linearGradient>',
        f'<radialGradient id="core" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#a18bff"/><stop offset=".6" stop-color="{VIOLET}"/><stop offset="1" stop-color="#2b1c80"/></radialGradient>',
        f'<linearGradient id="ring"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>',
    ]
    for i, r in enumerate(roles):
        pts = typing(len(r), 0, cw, i * slot + 0.35, 0.055 * len(r), i * slot + 4.1, 0.5)
        defs.append(
            f'<clipPath id="rc{i}"><rect x="{rx0 - 2}" y="{ry - 34}" width="0" height="46">{disc("width", pts, cycle)}</rect></clipPath>'
        )
    body = [f"<defs>{''.join(defs)}</defs>", '<g clip-path="url(#clip)">']
    body.append('<rect width="1200" height="440" fill="url(#bg)"/>')
    body.append('<rect width="1200" height="440" fill="url(#g)" mask="url(#gm)"/>')
    body.append(orb(300, 90, 200, VIOLET, 140, 60, 14))
    body.append(orb(1010, 380, 190, CYAN, -120, -50, 17, 0.28))
    body.append(orb(700, 30, 140, PINK, 80, 40, 12, 0.26))
    body.append(particles(W, H, 40, 3))

    # status pill
    pill = "BERLIN, GERMANY · OPEN TO SENIOR ROLES"
    pw = len(pill) * 8.1 + 58
    body.append(
        f'<g transform="translate(70 52)"><rect width="{n(pw)}" height="34" rx="17" fill="#ffffff0d" stroke="#ffffff22"/>'
        f'<circle cx="21" cy="17" r="4.5" fill="{GREEN}"/>'
        f'<circle cx="21" cy="17" r="4.5" fill="none" stroke="{GREEN}" stroke-width="2">'
        f'<animate attributeName="r" values="4.5;13" dur="1.8s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values=".8;0" dur="1.8s" repeatCount="indefinite"/></circle>'
        + mono_text(36, 22, pill, SOFT, 12.5, 8.1, extra=' letter-spacing="1"')
        + "</g>"
    )
    # name
    body.append(
        '<text x="66" y="188" font-size="86" font-weight="800" letter-spacing="-1.5" fill="url(#name)" opacity="0">'
        "Bharath Yadav"
        '<animate attributeName="opacity" from="0" to="1" dur="1s" fill="freeze"/>'
        '<animateTransform attributeName="transform" type="translate" from="0 18" to="0 0" dur="1s" fill="freeze"/></text>'
    )
    # typed roles
    body.append(mono_text(70, ry, "❯", CYAN, size, cw, "700"))
    for i, r in enumerate(roles):
        body.append(f'<g clip-path="url(#rc{i})">' + mono_text(rx0, ry, r, TEXT, size, cw, "600") + "</g>")
    caret_pts = []
    for i, r in enumerate(roles):
        caret_pts += typing(len(r), rx0 + 2, cw, i * slot + 0.35, 0.055 * len(r), i * slot + 4.1, 0.5)[1:]
    body.append(
        f'<rect x="{rx0 + 2}" y="{ry - 28}" width="3" height="34" fill="{CYAN}">'
        + disc("x", caret_pts, cycle)
        + '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1s" repeatCount="indefinite"/></rect>'
    )
    # credibility line
    body.append(
        f'<text x="70" y="320" font-size="21" fill="{MUTED}">'
        f'<tspan fill="{TEXT}" font-weight="600">Ex Google Operations Center</tspan>'
        f'<tspan dx="14" fill="{DIM}">·</tspan>'
        f'<tspan dx="14">Founder, </tspan><tspan fill="{TEXT}" font-weight="600">Brand E5 (BE5)</tspan></text>'
    )
    # chips
    x = 70
    for i, (label, color) in enumerate([("MARKETING", AMBER), ("ENGINEERING", VIOLET), ("AI AUTOMATION", CYAN)]):
        cw2 = 9.2
        w = len(label) * cw2 + 50
        body.append(
            f'<g transform="translate({n(x)} 352)">'
            f'<rect width="{n(w)}" height="38" rx="19" fill="{color}" fill-opacity=".08" stroke="{color}" stroke-opacity=".35">'
            f'<animate attributeName="stroke-opacity" values=".25;.95;.25" dur="3s" begin="{i}s" repeatCount="indefinite"/>'
            f'<animate attributeName="fill-opacity" values=".06;.18;.06" dur="3s" begin="{i}s" repeatCount="indefinite"/></rect>'
            f'<circle cx="21" cy="19" r="4.5" fill="{color}"/>'
            + mono_text(34, 24, label, color, 13, cw2, "700")
            + "</g>"
        )
        x += w + 14

    # orbit system
    cx, cy = 968, 222
    body.append(f'<circle cx="{cx}" cy="{cy}" r="96" fill="{VIOLET}" opacity=".35" filter="url(#blur)"/>')
    body.append(
        f'<g><circle cx="{cx}" cy="{cy}" r="176" fill="none" stroke="#ffffff22" stroke-dasharray="2 9"/>'
        f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="70s" repeatCount="indefinite"/></g>'
    )
    body.append(
        f'<g><circle cx="{cx}" cy="{cy}" r="120" fill="none" stroke="url(#ring)" stroke-width="1.6" stroke-dasharray="70 22 12 22" opacity=".8"/>'
        + "".join(
            f'<circle cx="{n(cx + 120 * math.cos(math.radians(a)))}" cy="{n(cy + 120 * math.sin(math.radians(a)))}" r="5" fill="{c}"/>'
            for a, c in [(30, PINK), (150, CYAN), (270, AMBER)]
        )
        + f'<animateTransform attributeName="transform" type="rotate" from="360 {cx} {cy}" to="0 {cx} {cy}" dur="26s" repeatCount="indefinite"/></g>'
    )
    nodes = [("ADS", AMBER, -90), ("SEO", GREEN, 0), ("DEV", VIOLET, 90), ("AI", CYAN, 180)]
    g = []
    for label, color, a in nodes:
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        g.append(
            f'<line x1="{n(cx + 66 * ca)}" y1="{n(cy + 66 * sa)}" x2="{n(cx + 148 * ca)}" y2="{n(cy + 148 * sa)}" '
            f'stroke="{color}" stroke-opacity=".55" stroke-width="1.6" stroke-dasharray="3 7">'
            f'<animate attributeName="stroke-dashoffset" from="20" to="0" dur="1s" repeatCount="indefinite"/></line>'
        )
        px, py = cx + 176 * ca, cy + 176 * sa
        g.append(
            f'<g transform="translate({n(px)} {n(py)})"><g>'
            f'<circle r="27" fill="{CARD}" stroke="{color}" stroke-width="2"/>'
            f'<circle r="27" fill="{color}" opacity=".12"/>'
            + mono_text(-len(label) * 4.6, 5, label, color, 13.5, 9.2, "800")
            + f'<animateTransform attributeName="transform" type="rotate" from="0" to="-360" dur="36s" repeatCount="indefinite"/>'
            "</g></g>"
        )
    body.append(
        "<g>" + "".join(g)
        + f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="36s" repeatCount="indefinite"/></g>'
    )
    body.append(
        f'<circle cx="{cx}" cy="{cy}" r="62" fill="url(#core)" stroke="#ffffff40" stroke-width="1.5">'
        '<animate attributeName="r" values="62;67;62" dur="3.2s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{cx}" cy="{cy}" r="62" fill="none" stroke="{VIOLET}" stroke-width="2">'
        '<animate attributeName="r" values="62;100" dur="3.2s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values=".7;0" dur="3.2s" repeatCount="indefinite"/></circle>'
        f'<text x="{cx}" y="{cy + 15}" text-anchor="middle" font-size="42" font-weight="800" fill="#fff" letter-spacing="1">BY</text>'
    )
    body.append('<rect width="1200" height="440" rx="28" fill="none" stroke="#ffffff16"/></g>')
    write("hero.svg", W, H, "Bharath Yadav: Senior Performance Marketer, Full-Stack Developer, AI Automation Builder, Founder of Brand E5", "".join(body))


# ---------------------------------------------------------------- terminal
def terminal():
    W, H = 1200, 470
    X0, Y0, LH, size, cw = 40, 98, 31, 17, 10.2
    cycle, end = 16.0, 15.3
    lines = [
        ("cmd", "whoami"),
        ("out", [("Bharath Yadav", TEXT, "700"), ("  // marketer who ships code", DIM)]),
        ("cmd", "cat roles.txt"),
        ("out", [("▸ ", VIOLET), ("Senior Performance Marketer", TEXT), ("    Google Ads, Meta Ads, SEM, SEO", MUTED)]),
        ("out", [("▸ ", VIOLET), ("Full-Stack Developer", TEXT), ("           .NET, C#, Angular, PostgreSQL", MUTED)]),
        ("out", [("▸ ", VIOLET), ("AI Automation Builder", TEXT), ("          n8n, Ollama, local LLMs", MUTED)]),
        ("out", [("▸ ", VIOLET), ("Founder", TEXT), ("                        Brand E5 (BE5)", AMBER)]),
        ("cmd", "ls experience/"),
        ("out", [("google-operations-center/", CYAN), ("   genpact/", CYAN), ("   harphil/", CYAN), ("   brand-e5/", AMBER, "700")]),
        ("cmd", "echo $BASE"),
        ("out", [("Berlin, Germany", TEXT), ("  |  ", DIM), ("work across Germany and India", MUTED)]),
        ("prompt", None),
    ]
    defs = [card_frame(W, H, 20, "tc")]
    body = []
    t = 0.6
    for i, (kind, val) in enumerate(lines):
        y = Y0 + i * LH
        if kind == "cmd":
            pts = typing(len(val), 0, cw, t + 0.25, 0.06 * len(val), end)
            defs.append(f'<clipPath id="c{i}"><rect x="{X0 + 2 * cw - 1}" y="{y - 20}" width="0" height="28">{disc("width", pts, cycle)}</rect></clipPath>')
            body.append(
                f'<g opacity="0">{window(t, end, cycle, 0.05)}'
                + mono_text(X0, y, "$", GREEN, size, cw, "700")
                + f'<g clip-path="url(#c{i})">' + mono_text(X0 + 2 * cw, y, val, TEXT, size, cw) + "</g></g>"
            )
            t += 0.25 + 0.06 * len(val) + 0.3
        elif kind == "out":
            body.append(f'<g opacity="0">{window(t, end, cycle, 0.12)}' + segs(X0, y, val, size, cw) + "</g>")
            t += 0.16
            if i + 1 < len(lines) and lines[i + 1][0] != "out":
                t += 0.3
        else:
            body.append(
                f'<g opacity="0">{window(t, end, cycle, 0.05)}'
                + mono_text(X0, y, "$", GREEN, size, cw, "700")
                + f'<rect x="{X0 + 2 * cw}" y="{y - 16}" width="{cw}" height="20" fill="{CYAN}">'
                '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1s" repeatCount="indefinite"/></rect></g>'
            )

    # "now" panel
    px, py, pwid, ph = 836, 76, 334, 368
    panel = [
        f'<rect x="{px}" y="{py}" width="{pwid}" height="{ph}" rx="14" fill="#ffffff05" stroke="{EDGE}" stroke-dasharray="6 6">'
        '<animate attributeName="stroke-dashoffset" from="0" to="-24" dur="1.6s" repeatCount="indefinite"/></rect>',
        mono_text(px + 22, py + 36, "// now", DIM, 14, 8.4),
    ]
    items = [
        ("BUILDING", "WGfinder, rentals in Germany", CYAN),
        ("EXPLORING", "n8n + Ollama + local LLMs", PINK),
        ("GROWING", "Brand E5 at brande5.com", AMBER),
        ("OPEN TO", "Senior roles across the EU", GREEN),
    ]
    for k, (lab, val, color) in enumerate(items):
        yy = py + 84 + k * 74
        panel.append(
            f'<g opacity="0">{window(1.2 + k * 0.45, end, cycle, 0.3)}'
            f'<rect x="{px + 22}" y="{yy - 11}" width="9" height="9" rx="2" fill="{color}">'
            f'<animate attributeName="opacity" values="1;.25;1" dur="2s" begin="{k * 0.5}s" repeatCount="indefinite"/></rect>'
            + mono_text(px + 40, yy - 2, lab, color, 12, 8.2, "700", ' letter-spacing="1.5"')
            + f'<text x="{px + 22}" y="{yy + 26}" font-size="17.5" fill="{TEXT}">{esc(val)}</text></g>'
        )

    out = [
        f"<defs>{''.join(defs)}</defs>",
        '<g clip-path="url(#tc)">',
        f'<rect width="{W}" height="{H}" fill="{CARD}"/>',
        f'<rect width="{W}" height="48" fill="#0f1733"/>',
        f'<line x1="0" y1="48" x2="{W}" y2="48" stroke="{EDGE}"/>',
        '<circle cx="28" cy="24" r="6.5" fill="#ff5f57"/><circle cx="50" cy="24" r="6.5" fill="#febc2e"/><circle cx="72" cy="24" r="6.5" fill="#28c840"/>',
        f'<text class="m" x="600" y="29" font-size="13.5" fill="{MUTED}" text-anchor="middle">bharath@berlin: ~/profile</text>',
        f'<circle cx="1140" cy="24" r="4" fill="{GREEN}"><animate attributeName="opacity" values="1;.2;1" dur="1.6s" repeatCount="indefinite"/></circle>',
        mono_text(1080, 29, "online", MUTED, 12, 7.6),
        "".join(body),
        "".join(panel),
        "</g>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="{EDGE}"/>',
    ]
    write("terminal.svg", W, H, "whoami: Bharath Yadav, senior performance marketer, full-stack developer, AI automation builder, founder of Brand E5", "".join(out))


# ---------------------------------------------------------------- pillars
def pillars():
    W, H = 1200, 400
    cards = [
        ("01 / MARKETING", "Growth Marketing", AMBER,
         ["Google Ads and Meta Ads campaigns", "SEM, PPC, SEO and analytics", "Ex Google Operations Center"]),
        ("02 / ENGINEERING", "Full-Stack Engineering", VIOLET,
         [".NET Core, C#, Angular, TypeScript", "PostgreSQL, SQL Server, AWS", "HRMS, rental platform, CRM"]),
        ("03 / AUTOMATION", "AI & Automation", CYAN,
         ["n8n workflow automation", "Local LLMs with Ollama", "From raw data to reports"]),
    ]
    cw_, ch = 380, 398
    per = 2 * (cw_ + ch) - (8 - 2 * math.pi) * 22
    defs = [blur("pb", 40)]
    body = []
    for i, (lab, title, color, bullets) in enumerate(cards):
        ox = i * 410
        defs.append(f'<clipPath id="pc{i}"><rect x="{ox + 1}" y="1" width="{cw_}" height="{ch}" rx="22"/></clipPath>')
        g = [f'<g clip-path="url(#pc{i})">',
             f'<rect x="{ox}" y="0" width="{cw_ + 2}" height="{H}" fill="{CARD}"/>',
             f'<circle cx="{ox + 330}" cy="20" r="120" fill="{color}" opacity=".2" filter="url(#pb)"/>']
        if i == 0:
            base = 168
            hs = [34, 52, 46, 74, 92, 118]
            xs = [ox + 40 + j * 44 for j in range(6)]
            defs.append(f'<linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{AMBER}" stop-opacity=".25"/><stop offset="1" stop-color="{PINK}"/></linearGradient>')
            for j, (x, h) in enumerate(zip(xs, hs)):
                d = j * 0.08
                g.append(
                    f'<rect x="{x}" y="{base - 6}" width="28" height="6" rx="5" fill="url(#bar)">'
                    f'<animate attributeName="height" values="6;6;{h};{h};6" keyTimes="0;{n(d)};{n(.35 + d)};.86;1" dur="5s" repeatCount="indefinite"/>'
                    f'<animate attributeName="y" values="{base - 6};{base - 6};{base - h};{base - h};{base - 6}" keyTimes="0;{n(d)};{n(.35 + d)};.86;1" dur="5s" repeatCount="indefinite"/></rect>'
                )
            pts = [(x + 14, base - h - 16) for x, h in zip(xs, hs)]
            L = sum(math.dist(pts[k], pts[k + 1]) for k in range(5))
            g.append(
                f'<polyline points="{" ".join(f"{n(a)},{n(b)}" for a, b in pts)}" fill="none" stroke="{AMBER}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{n(L)}">'
                f'<animate attributeName="stroke-dashoffset" values="{n(L)};{n(L)};0;0;{n(L)}" keyTimes="0;.3;.62;.86;1" dur="5s" repeatCount="indefinite"/></polyline>'
                f'<circle cx="{n(pts[-1][0])}" cy="{n(pts[-1][1])}" r="5" fill="{AMBER}" opacity="0">'
                '<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.6;.64;.86;1" dur="5s" repeatCount="indefinite"/>'
                '<animate attributeName="r" values="5;8;5" dur="1s" repeatCount="indefinite"/></circle>'
            )
            for k, tag in enumerate(["CTR", "ROAS", "CPA"]):
                tx, ty = ox + 300, 44 + k * 38
                g.append(
                    f'<g><rect x="{tx}" y="{ty}" width="58" height="24" rx="12" fill="{AMBER}" fill-opacity=".08" stroke="{AMBER}" stroke-opacity=".5"/>'
                    + mono_text(tx + 29 - len(tag) * 3.6, ty + 16.5, tag, AMBER, 11.5, 7.2, "700")
                    + f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" dur="{3 + k * 0.6}s" repeatCount="indefinite"/></g>'
                )
        elif i == 1:
            code = [
                (0, [(70, VIOLET), (110, SOFT)]),
                (1, [(46, CYAN), (90, PINK), (40, SOFT)]),
                (2, [(120, AMBER), (60, SOFT)]),
                (2, [(80, GREEN), (54, CYAN)]),
                (1, [(30, PINK)]),
                (0, [(56, VIOLET), (84, SOFT)]),
            ]
            for j, (ind, toks) in enumerate(code):
                y = 40 + j * 22
                x = ox + 40 + ind * 24
                a, b = j * 0.11, j * 0.11 + 0.12
                for w, c in toks:
                    g.append(
                        f'<rect x="{x}" y="{y}" width="0" height="10" rx="5" fill="{c}" opacity=".85">'
                        f'<animate attributeName="width" values="0;0;{w};{w};0" keyTimes="0;{n(a)};{n(b)};.88;1" dur="6s" repeatCount="indefinite"/></rect>'
                    )
                    x += w + 8
            g.append(
                f'<text class="m" x="{ox + 336}" y="120" font-size="40" font-weight="800" fill="{VIOLET}" text-anchor="middle">&lt;/&gt;'
                '<animate attributeName="opacity" values=".35;1;.35" dur="2.4s" repeatCount="indefinite"/></text>'
            )
        else:
            pos = [(52, 102), (145, 56), (145, 148), (240, 102), (328, 102)]
            labels = ["SRC", "n8n", "API", "LLM", "OUT"]
            edges = [((0, 1), 0), ((0, 2), 0), ((1, 3), 1), ((2, 3), 1), ((3, 4), 2)]
            for (a, b), _ in edges:
                (x1, y1), (x2, y2) = pos[a], pos[b]
                g.append(f'<line x1="{ox + x1}" y1="{y1}" x2="{ox + x2}" y2="{y2}" stroke="{CYAN}" stroke-opacity=".3" stroke-width="2"/>')
            cyc = 3.6
            for (a, b), stage in edges:
                (x1, y1), (x2, y2) = pos[a], pos[b]
                s, e = stage * 1.2 / cyc, (stage + 1) * 1.2 / cyc
                g.append(
                    f'<circle r="4.5" fill="#fff" opacity="0">'
                    f'<animateMotion path="M{ox + x1},{y1} L{ox + x2},{y2}" dur="{cyc}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;{n(s)};{n(e)};1"/>'
                    f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{n(s)};{n(s + .01)};{n(e - .01)};{n(e)};1" dur="{cyc}s" repeatCount="indefinite"/></circle>'
                )
            arrive = {0: 0.0, 1: 1.2, 2: 1.2, 3: 2.4, 4: 3.55}
            for k, ((x, y), nlab) in enumerate(zip(pos, labels)):
                hot = k == 3
                at = arrive[k] / cyc
                g.append(
                    f'<circle cx="{ox + x}" cy="{y}" r="24" fill="none" stroke="{CYAN}" stroke-width="2" opacity="0">'
                    f'<animate attributeName="r" values="24;24;36;36" keyTimes="0;{n(at)};{n(min(at + .2, .99))};1" dur="{cyc}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values="0;0;.8;0;0" keyTimes="0;{n(max(at - .001, 0))};{n(at + .002)};{n(min(at + .2, .99))};1" dur="{cyc}s" repeatCount="indefinite"/></circle>'
                    f'<circle cx="{ox + x}" cy="{y}" r="24" fill="{CYAN if hot else CARD}" fill-opacity="{".9" if hot else "1"}" stroke="{CYAN}" stroke-width="1.6"/>'
                    + mono_text(ox + x - len(nlab) * 3.6, y + 4.5, nlab, CARD if hot else CYAN, 12, 7.2, "800")
                )
        g.append(mono_text(ox + 32, 214, lab, color, 12.5, 8.2, "700", ' letter-spacing="2"'))
        g.append(f'<text x="{ox + 32}" y="250" font-size="26" font-weight="700" fill="{TEXT}">{esc(title)}</text>')
        for k, b in enumerate(bullets):
            y = 294 + k * 33
            g.append(
                f'<text x="{ox + 32}" y="{y}" font-size="16" fill="{color}">▹</text>'
                f'<text x="{ox + 54}" y="{y}" font-size="16.5" fill="{SOFT}">{esc(b)}</text>'
            )
        g.append("</g>")
        g.append(f'<rect x="{ox + 1}" y="1" width="{cw_}" height="{ch}" rx="22" fill="none" stroke="{EDGE}"/>')
        g.append(
            f'<rect x="{ox + 1}" y="1" width="{cw_}" height="{ch}" rx="22" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-dasharray="120 {n(per - 120)}">'
            f'<animate attributeName="stroke-dashoffset" values="0;{n(-per)}" dur="7s" begin="{-i * 2.3}s" repeatCount="indefinite"/></rect>'
        )
        body.append("".join(g))
    write("pillars.svg", W, H, "What I do: growth marketing, full-stack engineering, AI and automation", f"<defs>{''.join(defs)}</defs>" + "".join(body))


# ---------------------------------------------------------------- growth loop
def loop():
    W, H = 1200, 290
    xs, y, yb = [150, 375, 600, 825, 1050], 92, 226
    stages = [
        ("Research", "audience, intent, offers", AMBER),
        ("Build", "sites, apps, funnels", VIOLET),
        ("Launch", "ads, content, SEO", PINK),
        ("Measure", "tracking and analytics", CYAN),
        ("Optimize", "test, learn, scale", GREEN),
    ]
    path = f"M150,{y} H1050 C1140,{y} 1140,{yb} 1050,{yb} H150 C60,{yb} 60,{y} 150,{y} Z"

    def bez(p0, p1, p2, p3, steps=200):
        L, prev = 0, p0
        for s in range(1, steps + 1):
            t = s / steps
            pt = tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t ** 2 * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3))
            L += math.dist(prev, pt)
            prev = pt
        return L

    curve = bez((1050, y), (1140, y), (1140, yb), (1050, yb))
    total = 900 * 2 + curve * 2
    dur = 10
    defs = [card_frame(W, H, 22, "lc"), blur("lb", 6), blur("big", 50)]
    body = [f"<defs>{''.join(defs)}</defs>", '<g clip-path="url(#lc)">', f'<rect width="{W}" height="{H}" fill="{CARD}"/>',
            orb(250, 60, 150, VIOLET, 120, 30, 15, 0.16, "big"), orb(950, 250, 150, CYAN, -100, -30, 13, 0.14, "big"),
            f'<path d="{path}" fill="none" stroke="{EDGE}" stroke-width="3"/>',
            f'<path d="{path}" fill="none" stroke="{VIOLET}" stroke-opacity=".55" stroke-width="2" stroke-dasharray="6 14">'
            '<animate attributeName="stroke-dashoffset" from="0" to="-200" dur="4s" repeatCount="indefinite"/></path>']
    for k, ((name, sub, color), x) in enumerate(zip(stages, xs)):
        f_ = (x - 150) / total
        if k == 0:
            halo_k, halo_v = "0;.07;.95;1", ".9;0;0;.9"
        else:
            halo_k = f"0;{n(f_ - .01)};{n(f_ + .005)};{n(f_ + .08)};1"
            halo_v = "0;0;.9;0;0"
        body.append(
            f'<circle cx="{x}" cy="{y}" r="46" fill="{color}" opacity="0" filter="url(#lb)">'
            f'<animate attributeName="opacity" values="{halo_v}" keyTimes="{halo_k}" dur="{dur}s" repeatCount="indefinite"/></circle>'
            f'<g><circle cx="{x}" cy="{y}" r="44" fill="none" stroke="{color}" stroke-opacity=".45" stroke-dasharray="4 8"/>'
            f'<animateTransform attributeName="transform" type="rotate" from="0 {x} {y}" to="{360 if k % 2 else -360} {x} {y}" dur="20s" repeatCount="indefinite"/></g>'
            f'<circle cx="{x}" cy="{y}" r="34" fill="{CARD}" stroke="{color}" stroke-width="2.2"/>'
            f'<circle cx="{x}" cy="{y}" r="34" fill="{color}" opacity=".1"/>'
            + mono_text(x - 11.4, y + 6.5, f"0{k + 1}", color, 18, 11.4, "800")
            + f'<text x="{x}" y="{y + 72}" text-anchor="middle" font-size="21" font-weight="700" fill="{TEXT}">{esc(name)}</text>'
            f'<text class="m" x="{x}" y="{y + 98}" text-anchor="middle" font-size="13" fill="{MUTED}">{esc(sub)}</text>'
        )
    body.append(
        '<g><circle r="16" fill="#22d3ee" opacity=".45" filter="url(#lb)"/><circle r="6.5" fill="#fff"/>'
        f'<animateMotion path="{path}" dur="{dur}s" repeatCount="indefinite"/></g>'
        '<g><circle r="3.5" fill="#fff" opacity=".5"/>'
        f'<animateMotion path="{path}" dur="{dur}s" begin="-0.18s" repeatCount="indefinite"/></g>'
    )
    body.append(f'<text class="m" x="600" y="{yb + 40}" text-anchor="middle" font-size="13" fill="{DIM}">↻  repeat what works, cut what does not</text>')
    body.append(f'</g><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="{EDGE}"/>')
    write("loop.svg", W, H, "How I work: research, build, launch, measure, optimize, repeat", "".join(body))


# ---------------------------------------------------------------- stack marquee
def stack():
    W, H = 1200, 196
    rows = [
        [("Google Ads", AMBER), ("Meta Ads", PINK), ("SEM / PPC", AMBER), ("SEO", GREEN), ("Google Analytics", AMBER),
         ("Content Strategy", PINK), ("Social Media", PINK), ("Performance Marketing", AMBER), ("Salesforce", CYAN), ("Operations", GREEN)],
        [("C#", VIOLET), (".NET Core", VIOLET), ("Angular", PINK), ("TypeScript", CYAN), ("JavaScript", AMBER), ("Python", CYAN),
         ("HTML5", PINK), ("CSS3", CYAN), ("PostgreSQL", CYAN), ("SQL Server", PINK), ("AWS", AMBER), ("Firebase", AMBER),
         ("Linux", GREEN), ("n8n", PINK), ("Ollama", TEXT), ("LLM Pipelines", VIOLET)],
    ]
    cw, gap = 9.0, 14
    defs = [card_frame(W, H, 22, "sc"),
            '<linearGradient id="edge"><stop offset="0" stop-color="#000"/><stop offset=".09" stop-color="#fff"/><stop offset=".91" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>',
            f'<mask id="sm"><rect width="{W}" height="{H}" fill="url(#edge)"/></mask>']
    body = [f"<defs>{''.join(defs)}</defs>", '<g clip-path="url(#sc)">', f'<rect width="{W}" height="{H}" fill="{CARD}"/>', '<g mask="url(#sm)">']
    for r, items in enumerate(rows):
        yc = 66 if r == 0 else 132
        pills, x = [], 0
        for label, color in items:
            w = len(label) * cw + 52
            pills.append((x, w, label, color))
            x += w + gap
        total = x
        g = []
        for rep in range(2):
            for px, w, label, color in pills:
                X = px + rep * total
                g.append(
                    f'<g transform="translate({n(X)} {yc - 21})"><rect width="{n(w)}" height="42" rx="21" fill="{color}" fill-opacity=".07" stroke="{color}" stroke-opacity=".38"/>'
                    f'<circle cx="23" cy="21" r="5" fill="{color}"/>'
                    + mono_text(38, 26.5, label, TEXT, 15, cw, "600") + "</g>"
                )
        frm, to = ("0 0", f"{n(-total)} 0") if r == 0 else (f"{n(-total)} 0", "0 0")
        body.append(
            "<g>" + "".join(g)
            + f'<animateTransform attributeName="transform" type="translate" from="{frm}" to="{to}" dur="{n(total / 42)}s" repeatCount="indefinite"/></g>'
        )
    body.append(f'</g></g><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="{EDGE}"/>')
    write("stack.svg", W, H, "Toolkit: marketing platforms, languages, databases, cloud and AI tools", "".join(body))


# ---------------------------------------------------------------- section headers
def headers():
    W, H = 1200, 104
    items = [
        ("About", "who I am", VIOLET),
        ("What I do", "marketing x engineering x automation", AMBER),
        ("How I work", "the growth loop", PINK),
        ("Toolkit", "platforms, languages, infrastructure", CYAN),
        ("Featured builds", "products I designed and shipped", VIOLET),
        ("Client work", "websites built and marketed", AMBER),
        ("GitHub activity", "live stats", GREEN),
        ("Credentials", "certifications", CYAN),
        ("Let's talk", "roles, projects, collaborations", PINK),
    ]
    for i, (title, sub, color) in enumerate(items):
        num = f"{i + 1:02d}"
        defs = (
            card_frame(W, H, 18, "hc")
            + f'<linearGradient id="ng" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{color}"/><stop offset="1" stop-color="#ffffff"/></linearGradient>'
            + '<linearGradient id="sh"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            + f'<linearGradient id="ln"><stop offset="0" stop-color="{color}" stop-opacity="0"/><stop offset="1" stop-color="{color}"/></linearGradient>'
        )
        b = [
            f"<defs>{defs}</defs>",
            '<g clip-path="url(#hc)">',
            f'<rect width="{W}" height="{H}" fill="{CARD}"/>',
            f'<circle cx="60" cy="52" r="70" fill="{color}" opacity=".10"/>',
            f'<rect x="-320" y="0" width="300" height="{H}" fill="url(#sh)">'
            f'<animate attributeName="x" values="-320;1220;1220" keyTimes="0;.45;1" dur="7s" begin="{-i * 0.8}s" repeatCount="indefinite"/></rect>',
            f'<text x="34" y="74" font-size="58" font-weight="800" fill="{color}" fill-opacity=".08" stroke="url(#ng)" stroke-width="1.4" '
            f'stroke-dasharray="320" letter-spacing="2">{num}'
            '<animate attributeName="stroke-dashoffset" values="320;0;0;320" keyTimes="0;.3;.85;1" dur="8s" repeatCount="indefinite"/></text>',
            f'<text x="152" y="56" font-size="30" font-weight="700" fill="{TEXT}">{esc(title)}</text>',
            f'<text class="m" x="153" y="82" font-size="12.5" fill="{MUTED}" letter-spacing="2.2">{esc(sub.upper())}</text>',
            f'<line x1="760" y1="52" x2="1146" y2="52" stroke="{EDGE}" stroke-width="2"/>',
            f'<line x1="760" y1="52" x2="1146" y2="52" stroke="url(#ln)" stroke-width="2" stroke-dasharray="90 400">'
            '<animate attributeName="stroke-dashoffset" values="90;-400" dur="3.2s" repeatCount="indefinite"/></line>',
            f'<circle cx="1158" cy="52" r="5" fill="{color}"/>',
            f'<circle cx="1158" cy="52" r="5" fill="none" stroke="{color}" stroke-width="2">'
            '<animate attributeName="r" values="5;14" dur="2s" repeatCount="indefinite"/>'
            '<animate attributeName="opacity" values=".9;0" dur="2s" repeatCount="indefinite"/></circle>',
            "</g>",
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{EDGE}"/>',
        ]
        write(f"section-{num}.svg", W, H, f"{num} {title}", "".join(b))


# ---------------------------------------------------------------- certifications
def certs():
    W, H = 1200, 210
    items = [
        ("\U0001f393", "ENGINEERING", "Full Stack .NET", "with Angular", VIOLET),
        ("\U0001f4ca", "GOOGLE", "Google Ads Search", "Professional", AMBER),
        ("\U0001f4c8", "GOOGLE", "Google Analytics", "Professional", CYAN),
        ("\U0001f3f7️", "OPERATIONS", "Lean Six Sigma", "Yellow Belt", GREEN),
        ("\U0001f4cb", "MANAGEMENT", "Harvard Mentor", "Project Management", PINK),
    ]
    cw_, ch = 224, 206
    defs = ['<linearGradient id="sheen"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".14"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>']
    body = []
    cyc = 6.0
    for i, (emo, cat, l1, l2, color) in enumerate(items):
        ox = i * 244
        defs.append(f'<clipPath id="cc{i}"><rect x="{ox + 1}" y="2" width="{cw_ - 2}" height="{ch - 2}" rx="18"/></clipPath>')
        s = i * 0.5 / cyc
        body.append(
            f'<g clip-path="url(#cc{i})"><rect x="{ox}" y="0" width="{cw_}" height="{H}" fill="{CARD}"/>'
            f'<circle cx="{ox + 190}" cy="30" r="70" fill="{color}" opacity=".14"/>'
            f'<rect x="{ox}" y="0" width="{cw_}" height="5" fill="{color}"/>'
            f'<g transform="skewX(-20)"><rect x="-200" y="0" width="90" height="{H}" fill="url(#sheen)">'
            f'<animate attributeName="x" values="{ox - 140};{ox - 140};{ox + 330};{ox + 330}" keyTimes="0;{n(s)};{n(s + .22)};1" dur="{cyc}s" repeatCount="indefinite"/></rect></g>'
            f'<g><text x="{ox + 24}" y="66" font-size="30">{emo}</text>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -4;0 0" dur="3s" begin="{-i * 0.6}s" repeatCount="indefinite"/></g>'
            + mono_text(ox + 24, 110, cat, color, 11.5, 8.0, "700", ' letter-spacing="1.5"')
            + f'<text x="{ox + 24}" y="143" font-size="16" font-weight="700" fill="{TEXT}">{esc(l1)}</text>'
            f'<text x="{ox + 24}" y="166" font-size="16" fill="{SOFT}">{esc(l2)}</text></g>'
            f'<rect x="{ox + 1}" y="2" width="{cw_ - 2}" height="{ch - 2}" rx="18" fill="none" stroke="{EDGE}"/>'
        )
    write("certs.svg", W, H, "Certifications: Full Stack .NET with Angular, Google Ads Search, Google Analytics, Lean Six Sigma Yellow Belt, Harvard Mentor Project Management", f"<defs>{''.join(defs)}</defs>" + "".join(body))


# ---------------------------------------------------------------- call to action
def cta():
    W, H = 1200, 300
    rnd = random.Random(11)
    stars = []
    for _ in range(16):
        x, y, s = rnd.uniform(40, 1160), rnd.uniform(30, 270), rnd.uniform(4, 9)
        d, b = rnd.uniform(1.8, 3.6), -rnd.uniform(0, 3)
        stars.append(
            f'<path transform="translate({n(x)} {n(y)})" d="M0,{-s} Q0,0 {s},0 Q0,0 0,{s} Q0,0 {-s},0 Q0,0 0,{-s}Z" fill="#fff" opacity="0">'
            f'<animate attributeName="opacity" values="0;.9;0" dur="{n(d)}s" begin="{n(b)}s" repeatCount="indefinite"/></path>'
        )
    defs = [
        card_frame(W, H, 28, "kc"), blur("blur", 60), grid("kg", W, H),
        '<linearGradient id="kbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1330"/><stop offset="1" stop-color="#060914"/></linearGradient>',
        f'<linearGradient id="kt" gradientUnits="userSpaceOnUse" x1="170" y1="0" x2="700" y2="0" spreadMethod="reflect">'
        f'<stop offset="0" stop-color="#fff"/><stop offset=".4" stop-color="{AMBER}"/><stop offset=".7" stop-color="{PINK}"/><stop offset="1" stop-color="{VIOLET}"/>'
        '<animate attributeName="x1" values="170;1230" dur="6s" repeatCount="indefinite"/>'
        '<animate attributeName="x2" values="700;1760" dur="6s" repeatCount="indefinite"/></linearGradient>',
        f'<linearGradient id="ku"><stop offset="0" stop-color="{AMBER}"/><stop offset=".5" stop-color="{PINK}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>',
    ]
    body = [
        f"<defs>{''.join(defs)}</defs>", '<g clip-path="url(#kc)">',
        f'<rect width="{W}" height="{H}" fill="url(#kbg)"/>',
        f'<rect width="{W}" height="{H}" fill="url(#kg)" opacity=".7"/>',
        orb(220, 260, 170, PINK, 120, -40, 13, 0.3), orb(980, 40, 180, VIOLET, -120, 40, 15, 0.35), orb(600, 300, 140, AMBER, 60, -30, 11, 0.18),
        "".join(stars),
        '<text x="600" y="128" text-anchor="middle" font-size="52" font-weight="800" letter-spacing="-1" fill="url(#kt)">Let’s build something that grows.</text>',
        '<path d="M330,152 Q465,166 600,152 T870,152" fill="none" stroke="url(#ku)" stroke-width="4" stroke-linecap="round" stroke-dasharray="560">'
        '<animate attributeName="stroke-dashoffset" values="560;0;0;560" keyTimes="0;.3;.85;1" dur="6s" repeatCount="indefinite"/></path>',
        f'<text x="600" y="202" text-anchor="middle" font-size="19" fill="{SOFT}">Open to senior marketing, engineering and AI automation roles in Berlin and the EU.</text>',
        f'<text x="600" y="234" text-anchor="middle" font-size="19" fill="{MUTED}">Have a project? Bring it to <tspan fill="{AMBER}" font-weight="700">Brand E5</tspan>.</text>',
        "</g>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="28" fill="none" stroke="#ffffff18"/>',
    ]
    write("cta.svg", W, H, "Let's build something that grows. Open to senior marketing, engineering and AI automation roles. Projects welcome at Brand E5.", "".join(body))


# ---------------------------------------------------------------- footer
def footer():
    W, H = 1200, 150

    def wave(base, amp, length, phase=0):
        pts = []
        for x in range(0, 2 * W + 1, 10):
            pts.append(f"{x},{n(base + amp * math.sin(2 * math.pi * x / length + phase))}")
        return f"M0,{H} L" + " L".join(pts) + f" L{2 * W},{H} Z"

    layers = [(96, 12, 400, 0, VIOLET, .30, 22), (106, 10, 300, 1.4, CYAN, .30, 16), (118, 8, 600, 2.5, PINK, .35, 28)]
    defs = [
        f'<linearGradient id="fw{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c}" stop-opacity="{o}"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient>'
        for i, (_, _, _, _, c, o, _) in enumerate(layers)
    ]
    body = [f"<defs>{''.join(defs)}</defs>"]
    for i, (base, amp, length, ph, _, _, dur) in enumerate(layers):
        frm, to = ("0 0", f"-{W} 0") if i % 2 == 0 else (f"-{W} 0", "0 0")
        body.append(
            f'<path d="{wave(base, amp, length, ph)}" fill="url(#fw{i})">'
            f'<animateTransform attributeName="transform" type="translate" from="{frm}" to="{to}" dur="{dur}s" repeatCount="indefinite"/></path>'
        )
    body.append(f'<text class="m" x="600" y="44" text-anchor="middle" font-size="13" fill="{MUTED}" letter-spacing="1.5">MARKETER · DEVELOPER · FOUNDER OF BRAND E5</text>')
    write("footer.svg", W, H, "Footer", "".join(body))


if __name__ == "__main__":
    print("Building SVGs into assets/")
    hero()
    terminal()
    pillars()
    loop()
    stack()
    headers()
    certs()
    cta()
    footer()
