"""Alexey's GitHub banner: a Siberian winter night (dark theme) and a Scottsdale noon (light theme).

The OpenOrange ring is the sun. Its outer rays are the last 53 weeks of contributions from GitHub's public
calendar (this week at 12 o'clock); on every load a hot arc runs once around the rim and blooms. When
releases.json is given, inner rays are the OpenOrange releases of the last 24 hours on a 24-hour Arizona clock
(midnight at the top), the newest one pulsing. Every 90 s a small plane flies a parabola; while it is over the
top, the snow (dust by day) and the figure float. SMIL only, so it plays inside GitHub's <img>.

Usage: python3 make_banner.py --calendar calendar.json [--releases releases.json] --out DIR
"""

import argparse
import datetime as dt
import json
import math
import os
import random

W, H, PX = 800, 200, 4
ORANGE, HOT, CREAM = "#D6561A", "#F2A26E", "#F4F0E9"
CX, CY, R = 628, 74, 30
CYCLE, FLOAT = 90.0, (9.0, 29.0)  # seconds: one plane pass per cycle; ~20 s of zero g over the top
ARIZONA = dt.timezone(dt.timedelta(hours=-7))  # no daylight saving

THEMES = {
    "dark": dict(
        sky=("#05070c", "#0d1117", "#22160f"), glow=(ORANGE, 0.38), core=None,
        far=("#232a36", "#8fa3b8"), near=("#13151a", "#d8dee6"), ground="#e9e4dc", mesa=False,
        figure="#e2e8f0", thread=("#6ECDD6", "#9fe3e8"), particle=(CREAM, CREAM), plane="#c9d1d9",
        caption="#6b6259", stars=True, aurora=True, snowcaps=True, shimmer=False),
    "light": dict(
        sky=("#8ec9e8", "#cfe6ef", "#f6e3c4"), glow=("#FFD9A0", 0.55), core="#FFF6E0",
        far=("#e3b08b", "#efc8a6"), near=("#b4502c", "#d27a4a"), ground="#e8c896", mesa=True,
        figure="#3a2a22", thread=("#2a8a92", "#3fa7ae"), particle=("#b98b55", "#a8783f"), plane="#3d4148",
        caption="#8a6a4c", stars=False, aurora=False, snowcaps=False, shimmer=True),
}


def ridge(peaks, base, cap_depth, seed, mesa):
    """Stepped pixel ridge (one path) and its caps (snow, or a lit rim on mesas), from (x, height) peaks."""
    r = random.Random(seed)
    slopes = [(0.55 + r.random() * 0.45, 0.55 + r.random() * 0.45) for _ in peaks]
    tops_w = [24 + r.random() * 36 for _ in peaks]  # mesa tabletop half-widths
    tops = []
    for x in range(0, W, PX):
        if mesa:  # flat tabletops, steep walls
            h = max(ph * 0.8 - max(0, abs(x - px) - top) * (sl if x < px else sr) * 2.4
                    for (px, ph), (sl, sr), top in zip(peaks, slopes, tops_w))
        else:
            h = max(ph - abs(x - px) * (sl if x < px else sr) for (px, ph), (sl, sr) in zip(peaks, slopes))
        h = max(h, 0) + r.choice((0, 0, 0, PX))  # a little pixel roughness
        tops.append(base - int(h // PX) * PX)
    path = [f"M0 {H}"] + [f"V{y}H{x + PX}" for x, y in zip(range(0, W, PX), tops)] + [f"V{H}Z"]
    caps = []
    peak_ys = [base - ph for _, ph in peaks]
    for x, y in zip(range(0, W, PX), tops):
        if mesa and y < base - 12:
            caps.append(f"M{x} {y}h{PX}v{PX}h-{PX}z")
        elif not mesa and any(y <= py + 22 for py in peak_ys if abs(y - py) < 40):
            depth = cap_depth + r.choice((0, PX, PX * 2))
            caps.append(f"M{x} {y}h{PX}v{depth}h-{PX}z")
    return "".join(path), "".join(caps)


def drift_values(rng, length, speed, cross, float_move):
    """Keyframes for one particle over the shared cycle: travel along an axis, wrap off-screen, and float
    during the zero-g window. The speed is tuned so the cycle ends where it began (seamless repeat)."""
    w0, w1 = FLOAT
    fa, fc = float_move
    laps = max(1, round(speed * (CYCLE - (w1 - w0)) / length))
    v = (laps * length - fa) / (CYCLE - (w1 - w0))
    s = rng.uniform(0, length)
    c_float = 0.0
    frames = [(0.0, s, cross * s / length)]

    def travel(t0, t1):
        nonlocal s, c_float
        t = t0
        while s + v * (t1 - t) >= length:
            t += (length - s) / v
            frames.append((t, length, cross + c_float))
            s, c_float = 0.0, 0.0
            frames.append((t, 0.0, 0.0))  # off-screen jump back to the start; key times are nudged apart below
        s += v * (t1 - t)
        frames.append((t1, s, cross * s / length + c_float))

    travel(0.0, w0)
    s, c_float = s + fa, c_float + fc
    frames.append((w1, s, cross * s / length + c_float))
    travel(w1, CYCLE)
    times, last = [], -1.0
    for t, _, _ in frames:  # strictly increasing key times
        k = max(round(t / CYCLE, 5), last + 0.00001)
        times.append(min(k, 1.0))
        last = k
    times[-1] = 1.0
    return times, [(a, c) for _, a, c in frames]


def year_ring(weeks, glow_filter):
    """Outer rays: one per week (oldest just clockwise of 12, this week at 12), log scale; and the one-shot flare."""
    out = []
    top = math.log1p(max(weeks) or 1)
    for i, w in enumerate(weeks):
        if not w:
            continue
        a = 2 * math.pi * (i + 1) / len(weeks) - math.pi / 2
        k = math.log1p(w) / top
        r0, r1 = R + 3.5, R + 4 + 16 * k
        out.append(f'    <line x1="{CX + r0 * math.cos(a):.1f}" y1="{CY + r0 * math.sin(a):.1f}" '
                   f'x2="{CX + r1 * math.cos(a):.1f}" y2="{CY + r1 * math.sin(a):.1f}" '
                   f'stroke="{HOT if k > 0.8 else ORANGE}" stroke-width="2.4" opacity="{0.35 + 0.65 * k:.2f}"/>')
    out.append(f'    <circle cx="{CX}" cy="{CY}" r="{R}" stroke="{ORANGE}" stroke-width="5.5"/>')
    circ = 2 * math.pi * R
    out.append(f'    <circle cx="{CX}" cy="{CY}" r="{R}" stroke="#FFD2A8" stroke-width="6" stroke-linecap="round" '
               f'stroke-dasharray="{circ * 0.18:.1f} {circ:.1f}" transform="rotate(-90 {CX} {CY})" opacity="0" '
               f'filter="url(#{glow_filter})">'
               f'<animate attributeName="stroke-dashoffset" from="0" to="{-circ:.1f}" begin="0.8s" dur="1.6s" '
               f'fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1" keyTimes="0;1"/>'
               f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.75;1" begin="0.8s" '
               f'dur="1.6s" fill="freeze"/></circle>')
    out.append(f'    <circle cx="{CX}" cy="{CY}" r="{R}" stroke="{ORANGE}" stroke-width="14" filter="url(#halo)" '
               f'opacity="0"><animate attributeName="opacity" values="0;0.95;0" keyTimes="0;0.35;1" begin="1.6s" '
               f'dur="1.4s" fill="freeze"/><animate attributeName="r" values="{R};{R + 9};{R + 4}" '
               f'keyTimes="0;0.35;1" begin="1.6s" dur="1.4s" fill="freeze"/></circle>')
    return out


def release_rays(stamps, now):
    """Inner rays: releases of the last 24 h at their Arizona clock time, fading with age; the newest pulses."""
    day = sorted(t for t in stamps if dt.timedelta(0) <= now - t < dt.timedelta(hours=24))
    out = []
    for t in day:
        lt = t.astimezone(ARIZONA)
        a = math.radians((lt.hour + lt.minute / 60) / 24 * 360 - 90)
        fresh = 1 - (now - t).total_seconds() / 86400
        r0, r1 = R - 4.5, R - 10 - 6 * fresh
        pulse = ('<animate attributeName="opacity" values="0.4;1;0.4" dur="1.6s" repeatCount="indefinite"/>'
                 if t == day[-1] else "")
        out.append(f'    <line x1="{CX + r0 * math.cos(a):.1f}" y1="{CY + r0 * math.sin(a):.1f}" '
                   f'x2="{CX + r1 * math.cos(a):.1f}" y2="{CY + r1 * math.sin(a):.1f}" stroke="{HOT}" '
                   f'stroke-width="2" stroke-linecap="round" opacity="{0.3 + 0.7 * fresh:.2f}">{pulse}</line>')
    return out, len(day)


def plane_path():
    """Level entry, pull-up, the parabola (zero g) and a climbing exit, as points with their key times."""
    pts, keys = [(-24, 26), (120, 30), (200, 62)], [(0.0, 0), (3.0, 0), (7.0, 2)]
    pts.append((250, 34))
    keys.append((9.0, 3))
    for i in range(1, 23):  # y = 12 + 22 ((x - 360) / 110)^2 from x = 250 to 470
        x = 250 + 10 * i
        pts.append((x, 12 + 22 * ((x - 360) / 110) ** 2))
    keys.append((29.0, len(pts) - 1))
    pts += [(520, 62), (566, -14)]
    keys += [(31.0, len(pts) - 2), (33.5, len(pts) - 1), (CYCLE, len(pts) - 1)]
    lens = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        lens.append(lens[-1] + math.hypot(x1 - x0, y1 - y0))
    d = "M" + " L".join(f"{x:.0f} {y:.1f}" for x, y in pts)
    return d, ";".join(f"{t / CYCLE:.4f}" for t, _ in keys), ";".join(f"{lens[i] / lens[-1]:.4f}" for _, i in keys)


def build(theme, weeks, stamps, now):
    th = THEMES[theme]
    rng = random.Random(20261030)
    out = []
    add = out.append
    sky = th["sky"]
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none">')
    add(f"""  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{sky[0]}"/><stop offset="0.55" stop-color="{sky[1]}"/><stop offset="1" stop-color="{sky[2]}"/>
    </linearGradient>
    <radialGradient id="sun" cx="{CX}" cy="92" r="190" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{th['glow'][0]}" stop-opacity="{th['glow'][1]}"/><stop offset="1" stop-color="{th['glow'][0]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="core" cx="{CX}" cy="{CY}" r="70" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{th['core'] or ORANGE}" stop-opacity="{0.9 if th['core'] else 0}"/><stop offset="1" stop-color="{th['core'] or ORANGE}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="aurora" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#6ECDD6" stop-opacity="0"/><stop offset="1" stop-color="#6ECDD6" stop-opacity="0.55"/>
    </linearGradient>
    <linearGradient id="thread" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{th['thread'][0]}" stop-opacity="0.15"/><stop offset="45%" stop-color="{th['thread'][1]}" stop-opacity="0.85"/>
      <stop offset="80%" stop-color="{HOT}" stop-opacity="0.9"/><stop offset="100%" stop-color="{ORANGE}" stop-opacity="0.6"/>
    </linearGradient>
    <filter id="blur6"><feGaussianBlur stdDeviation="6"/></filter>
    <filter id="halo" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>
    <filter id="glow"><feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>""")
    add(f'  <rect width="{W}" height="{H}" rx="8" fill="url(#sky)"/>')
    add(f'  <rect width="{W}" height="{H}" rx="8" fill="url(#sun)"/>')
    add(f'  <rect width="{W}" height="{H}" rx="8" fill="url(#core)"/>')

    if th["aurora"]:  # slow breathing curtains
        for d, dur in [("M150 64C210 30 270 70 330 40S450 50 500 28L500 58C450 80 390 62 330 74S210 64 150 92Z", 9),
                       ("M90 40C150 14 220 44 280 22S390 30 430 14L430 40C390 56 330 44 280 56S160 50 90 64Z", 12)]:
            add(f'  <path d="{d}" fill="url(#aurora)" filter="url(#blur6)" opacity="0.45">'
                f'<animate attributeName="opacity" values="0.25;0.6;0.25" dur="{dur}s" repeatCount="indefinite"/></path>')
    for _ in range(90):  # pixel stars, a few twinkling; none in front of the sun (positions drawn either way)
        x, y = rng.randrange(8, W - 8), int((rng.random() ** 1.6) * 120) + 4
        s, o, tw = rng.choice((1.5, 1.5, 2, 2.5)), rng.choice((0.35, 0.55, 0.8)), rng.random() < 0.3
        dur = rng.uniform(2.5, 6)
        if not th["stars"] or (x - CX) ** 2 + (y - CY) ** 2 < (R * 1.7) ** 2:
            continue
        anim = (f'<animate attributeName="opacity" values="{o};0.1;{o}" dur="{dur:.1f}s" repeatCount="indefinite"/>'
                if tw else "")
        add(f'  <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{CREAM}" opacity="{o}">{anim}</rect>')

    # The sun: a soft pulsing halo behind the year ring.
    add(f'  <circle cx="{CX}" cy="{CY}" r="{R}" stroke="{ORANGE}" stroke-width="10" filter="url(#halo)" opacity="0.7">'
        f'<animate attributeName="opacity" values="0.45;0.85;0.45" dur="4s" repeatCount="indefinite"/></circle>')
    add('  <g id="year-ring">')
    out.extend(year_ring(weeks, "glow"))
    rays, n24 = release_rays(stamps, now) if stamps else ([], 0)
    out.extend(rays)
    add("  </g>")

    # The plane flies its parabola behind the mountains' line of sight, in front of the sky.
    d, key_times, key_points = plane_path()
    pc = th["plane"]
    add(f'  <g opacity="0.9"><g fill="{pc}">'
        f'<rect x="-8" y="-1.5" width="16" height="3"/><rect x="-8" y="-5" width="3" height="4"/>'
        f'<rect x="-2" y="0" width="6" height="2" opacity="0.7"/><rect x="5" y="-2.5" width="2" height="1"/></g>'
        f'<animateMotion path="{d}" dur="{CYCLE:.0f}s" repeatCount="indefinite" rotate="auto" calcMode="linear" '
        f'keyTimes="{key_times}" keyPoints="{key_points}"/></g>')

    far, far_caps = ridge([(40, 64), (170, 82), (300, 70), (430, 92), (560, 66), (720, 84), (790, 60)], 176, 6, 1,
                          th["mesa"])
    near, near_caps = ridge([(100, 46), (240, 58), (380, 44), (500, 62), (650, 50), (760, 56)], 184, 5, 2, th["mesa"])
    add(f'  <path d="{far}" fill="{th["far"][0]}"/><path d="{far_caps}" fill="{th["far"][1]}"/>')
    add(f'  <path d="{near}" fill="{th["near"][0]}"/><path d="{near_caps}" fill="{th["near"][1]}"/>')
    ground = [f"M0 {H}"]
    for x in range(0, W, PX * 2):
        ground.append(f"V{186 + rng.choice((0, 0, PX, -PX))}H{x + PX * 2}")
    ground.append(f"V{H}Z")
    add(f'  <path d="{"".join(ground)}" fill="{th["ground"]}"/>')
    if th["shimmer"]:  # heat haze over the sand
        for i, y in enumerate((150, 162, 174)):
            add(f'  <path d="M0 {y}Q100 {y - 3} 200 {y}T400 {y}T600 {y}T800 {y}" stroke="#FFF4E0" stroke-width="1.5" '
                f'opacity="0"><animate attributeName="opacity" values="0;0.3;0" dur="{3 + i}s" begin="{i}s" '
                f'repeatCount="indefinite"/><animateTransform attributeName="transform" type="translate" '
                f'values="0 0;-12 0;0 0" dur="{5 + i}s" repeatCount="indefinite"/></path>')

    # A saguaro: in the snow at night, at home at noon.
    sx, stop = 716, 136
    for x, y, w, h in [(sx, stop, 8, 192 - stop), (sx - 12, 158, 12, 6), (sx - 12, 144, 6, 14), (sx + 8, 150, 12, 6),
                       (sx + 14, 132, 6, 18)]:
        add(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#3f7d4e"/>')
    for x, y, h in [(sx + 2, stop + 4, 50), (sx - 10, 146, 10), (sx + 16, 134, 14)]:
        add(f'  <rect x="{x}" y="{y}" width="2" height="{h}" fill="#5fa36c"/>')
    if th["snowcaps"]:
        for x, y, w in [(sx, stop - 4, 8), (sx - 12, 140, 6), (sx + 14, 128, 6)]:
            add(f'  <rect x="{x}" y="{y}" width="{w}" height="4" fill="{CREAM}"/>')

    for d, dur in [("M150 64C260 30 430 40 598 66", 6), ("M152 84C300 70 450 96 598 78", 7),
                   ("M148 104C290 120 460 110 600 88", 8), ("M146 74C280 46 470 66 600 72", 9.5)]:
        add(f'  <path d="{d}" stroke="url(#thread)" stroke-width="1.3" stroke-dasharray="3 9" filter="url(#glow)" '
            f'opacity="0.85"><animate attributeName="stroke-dashoffset" values="0;-120" dur="{dur}s" '
            f'repeatCount="indefinite"/></path>')

    # The figure, Alexey's neural constellation; it lifts a little in zero g.
    nodes = {"head": (0, -48, 4), "ls": (-18, -30, 3), "rs": (18, -30, 3), "core": (0, -10, 3.5),
             "lh": (-13, 10, 2.5), "rh": (13, 10, 2.5), "lf": (-10, 34, 2), "rf": (10, 34, 2)}
    edges = [("head", "ls"), ("head", "rs"), ("ls", "core"), ("rs", "core"), ("core", "lh"), ("core", "rh"),
             ("lh", "lf"), ("rh", "rf"), ("ls", "rs")]
    w0, w1 = FLOAT
    lift = ";".join(f"{t / CYCLE:.4f}" for t in (0, w0, w0 + 4, w1 - 2, w1 + 2, CYCLE))
    add(f'  <g><animateTransform attributeName="transform" type="translate" values="0 0;0 0;0 -8;0 -8;0 0;0 0" '
        f'keyTimes="{lift}" dur="{CYCLE:.0f}s" repeatCount="indefinite"/>')
    add('  <g transform="translate(118 92)" filter="url(#glow)">')
    for a, b in edges:
        (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
        add(f'    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{th["figure"]}" stroke-width="0.8" '
            f'opacity="0.35"/>')
    for i, (x, y, rr) in enumerate(nodes.values()):
        o = 0.9 - i * 0.05
        add(f'    <circle cx="{x}" cy="{y}" r="{rr}" fill="{th["figure"]}" opacity="{o:.2f}"><animate '
            f'attributeName="opacity" values="{o:.2f};0.3;{o:.2f}" dur="{2.8 + i * 0.3:.1f}s" '
            f'repeatCount="indefinite"/></circle>')
    add("  </g></g>")

    # Particles share one cycle so they all float together: snow falls at night, dust blows by day.
    prng = random.Random(7)
    snow = theme == "dark"
    for _ in range(46 if snow else 28):
        size = prng.choice((1.5, 2, 2, 2.5))
        op = prng.choice((0.5, 0.7, 0.9))
        if snow:
            length, speed, cross = H + 12, (H + 12) / prng.uniform(7, 15), prng.uniform(-18, 18)
            fm = (-prng.uniform(2, 8), prng.uniform(-5, 5))
            base = f'x="{prng.randrange(0, W)}" y="0"'
        else:
            length, speed, cross = W + 12, (W + 12) / prng.uniform(22, 40), prng.uniform(-10, 10)
            fm = (-prng.uniform(0, 4), -prng.uniform(2, 8))
            base = f'x="0" y="{prng.randrange(96, 184)}"'
        times, vals = drift_values(prng, length, speed, cross, fm)
        pos = ";".join((f"{c:.1f} {a - 6:.1f}" if snow else f"{a - 6:.1f} {c:.1f}") for a, c in vals)
        add(f'  <rect {base} width="{size}" height="{size}" fill="{th["particle"][prng.random() < 0.5]}" '
            f'opacity="{op}"><animateTransform attributeName="transform" type="translate" values="{pos}" '
            f'keyTimes="{";".join(f"{k:.5f}" for k in times)}" dur="{CYCLE:.0f}s" repeatCount="indefinite"/></rect>')

    caption = "intelligence in transit"
    if stamps:
        n30 = sum(dt.timedelta(0) <= now - t < dt.timedelta(days=30) for t in stamps)
        caption += f" · {n24} release{'' if n24 == 1 else 's'} in the last 24h · {n30} in 30 days"
    add(f'  <text x="400" y="196" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
        f'font-size="8" letter-spacing="2.5" fill="{th["caption"]}">{caption}</text>')
    add("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calendar", required=True)
    ap.add_argument("--releases")
    ap.add_argument("--out", required=True)
    ap.add_argument("--now", help="ISO time, for previews")
    args = ap.parse_args()
    cal = json.load(open(args.calendar))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    stamps = []
    if args.releases and os.path.exists(args.releases):
        stamps = [dt.datetime.fromisoformat(s.replace("Z", "+00:00")) for s in json.load(open(args.releases))]
    now = dt.datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else dt.datetime.now(dt.timezone.utc)
    os.makedirs(args.out, exist_ok=True)
    for theme, name in (("dark", "winter.svg"), ("light", "desert.svg")):
        svg = build(theme, weeks, stamps, now)
        with open(os.path.join(args.out, name), "w") as f:
            f.write(svg)
        print(name, len(svg), "bytes")


if __name__ == "__main__":
    main()
