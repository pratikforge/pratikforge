"""Generate unified Cool Impasto Studio Poster SVGs (dark & light) with exact fontTools path outlines."""

import json
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
ASSETS_DIR = ROOT / "assets"
STATS_PATH = ROOT / "stats.json"


def load_font(filename: str, weight: int) -> TTFont:
    tt = TTFont(FONTS_DIR / filename)
    if "fvar" in tt:
        tt = instantiateVariableFont(tt, {"wght": weight})
    return tt


FONTS = {
    "display": load_font("MomoTrustDisplay-Regular.ttf", 400),
    "sans_regular": load_font("MomoTrustSans[wght].ttf", 400),
    "sans_medium": load_font("MomoTrustSans[wght].ttf", 500),
    "sans_semibold": load_font("MomoTrustSans[wght].ttf", 600),
}


def measure_text(font: TTFont, text: str, font_size: float, letter_spacing: float = 0.0) -> float:
    upem = font["head"].unitsPerEm
    scale = font_size / upem
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    total = 0.0
    for idx, ch in enumerate(text):
        gname = cmap.get(ord(ch))
        if gname is None:
            continue
        adv, _ = hmtx[gname]
        total += adv * scale
        if idx < len(text) - 1:
            total += letter_spacing
    return total


def text_to_paths(
    font: TTFont,
    text: str,
    x: float,
    y: float,
    font_size: float,
    fill: str,
    letter_spacing: float = 0.0,
    align: str = "left",
    opacity: float = 1.0,
) -> str:
    upem = font["head"].unitsPerEm
    scale = font_size / upem
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"].metrics

    total_w = measure_text(font, text, font_size, letter_spacing)
    if align == "right":
        cursor_x = x - total_w
    elif align == "center":
        cursor_x = x - total_w / 2.0
    else:
        cursor_x = x

    paths = []
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            continue
        adv, _ = hmtx[gname]
        pen = SVGPathPen(glyph_set)
        glyph_set[gname].draw(pen)
        d = pen.getCommands()
        if d:
            paths.append(
                f'<path d="{d}" transform="translate({cursor_x:.2f},{y:.2f}) scale({scale:.6f},{-scale:.6f})"/>'
            )
        cursor_x += adv * scale + letter_spacing

    op_attr = f' fill-opacity="{opacity:.2f}"' if opacity < 1.0 else ""
    return f'<g fill="{fill}"{op_attr}>\n    ' + "\n    ".join(paths) + "\n  </g>"


THEMES = {
    "dark": {
        "primary": "#EDF3F8",
        "secondary": "#C4D1E0",
        "muted": "#7C90A6",
        "accent": "#76AED4",
        "rule": "#4E6F90",
        "divider": "#9EB5CC",
        "swatches": ["#2A608F", "#4B89B8", "#2B7E84", "#5272A8", "#6F8CA8"],
        "lang_colors": ["#4E8EC2", "#7AB6DF", "#2D7A80", "#5F78A8", "#48596B"],
        "heat": ["#151D27", "#213A54", "#305B82", "#4B86B8", "#91C6EC"],
        "glint_core": "#F7FBFF",
        "glint_halo": "#9ED3FF",
        "curve_stroke": "#84BEE6",
        "curve_top": "#4B86B8",
        "curve_bot": "#151D27",
        "axis": "#2A394A",
    },
    "light": {
        "primary": "#131D27",
        "secondary": "#334659",
        "muted": "#627488",
        "accent": "#245480",
        "rule": "#30608C",
        "divider": "#1E2E3F",
        "swatches": ["#1E4F7A", "#326B99", "#1F686E", "#3B5788", "#556E87"],
        "lang_colors": ["#245480", "#4A84B5", "#246B70", "#4B6594", "#8FA2B5"],
        "heat": ["#EAEFF5", "#BDD3E8", "#7FAAD1", "#4178AA", "#1A4168"],
        "glint_core": "#FFFFFF",
        "glint_halo": "#74B8F0",
        "curve_stroke": "#245480",
        "curve_top": "#4178AA",
        "curve_bot": "#EAEFF5",
        "axis": "#CFD9E4",
    },
}

# Verified 2026 in-demand skills backed by pratikforge repositories
STACK_ROWS = [
    ("Agents & AI", "Multi-Agent Orchestration · MCP · Google ADK · LLM Evals · RAG · Multimodal"),
    ("Security & CUA", "Agent Guardrails · Sandboxing · Computer Use (CUA) · Playwright · Telemetry"),
    ("Languages", "Python · TypeScript · Rust · JavaScript"),
    ("Full-Stack", "React · Next.js · Tailwind · Vite  /  FastAPI · Node.js · Streaming (SSE / WS)"),
    ("Data & Infra", "PostgreSQL · Supabase · Redis · SQLite  /  Docker · GitHub Actions · Cloudflare"),
]


def _smooth_bezier(points: list[tuple[float, float]]) -> str:
    if len(points) < 2:
        return ""
    parts = [f"M{points[0][0]:.2f},{points[0][1]:.2f}"]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        cx = (x0 + x1) / 2.0
        parts.append(f"C{cx:.2f},{y0:.2f} {cx:.2f},{y1:.2f} {x1:.2f},{y1:.2f}")
    return " ".join(parts)


def build_studio_svg(theme: str, stats: dict) -> str:
    p = THEMES[theme]

    # ── BAND A: Masthead + Bio + 5 Live Executive KPIs (y=8..98) ──
    name_g = text_to_paths(
        FONTS["display"], "Pratik", x=24, y=49, font_size=40, fill=p["primary"], letter_spacing=0.4
    )
    name_w = measure_text(FONTS["display"], "Pratik", 40, 0.4)
    handle_g = text_to_paths(
        FONTS["sans_medium"],
        "pratikforge",
        x=24 + name_w + 12,
        y=49,
        font_size=14,
        fill=p["accent"],
        letter_spacing=0.25,
    )
    role_g = text_to_paths(
        FONTS["sans_semibold"],
        "AI Systems & Full-Stack Engineer",
        x=24,
        y=69,
        font_size=11.0,
        fill=p["secondary"],
        letter_spacing=0.2,
    )
    bio_g = text_to_paths(
        FONTS["sans_regular"],
        "Autonomous agents, Rust security guardrails & sub-200ms computer-use systems.",
        x=24,
        y=85,
        font_size=10.2,
        fill=p["muted"],
        letter_spacing=0.1,
    )

    kpis = [
        (f"{stats['total_contributions']:,}", "CONTRIBS", 454),
        (f"{stats['longest_streak']}d", "STREAK", 558),
        (f"{stats['pull_requests']}", "PRS", 648),
        (f"{stats['total_repos']}", "REPOS", 728),
        (f"{stats['stars']}", "STARS", 804),
    ]
    kpis_svg = []
    for idx, (val, lbl, kx) in enumerate(kpis):
        kpis_svg.append(
            text_to_paths(FONTS["display"], val, x=kx, y=54, font_size=27.5, fill=p["primary"], letter_spacing=0.3)
        )
        kpis_svg.append(
            text_to_paths(FONTS["sans_semibold"], lbl, x=kx, y=73, font_size=8.6, fill=p["accent"], letter_spacing=1.6)
        )
        if idx > 0:
            vx = kx - 15
            kpis_svg.append(
                f'<line x1="{vx}" y1="28" x2="{vx}" y2="75" stroke="{p["divider"]}" stroke-width="0.65" stroke-opacity="0.16"/>'
            )

    # ── BAND B LEFT: Architectural Editorial Typography (Momo Trust Display + Sans) ──
    stack_svg = []
    row_y0 = 134.0
    row_step = 42.0
    for idx, (domain, items) in enumerate(STACK_ROWS):
        sy = row_y0 + idx * row_step
        pigment = p["swatches"][idx]
        accent_bar = (
            f'<path d="M24,{sy + 2.5:.1f} C24,{sy + 1.5:.1f} 26.5,{sy + 1.5:.1f} 26.5,{sy + 2.5:.1f} '
            f'L26.5,{sy + 19.5:.1f} C26.5,{sy + 20.5:.1f} 24,{sy + 20.5:.1f} 24,{sy + 19.5:.1f} Z" '
            f'fill="{pigment}" opacity="0.92"/>'
        )
        dom_g = text_to_paths(
            FONTS["display"],
            domain,
            x=36,
            y=sy + 16.5,
            font_size=14.5,
            fill=p["primary"],
            letter_spacing=0.2,
        )
        # Auto-fit stack text inside x=174..544 (370px max)
        fsize = 11.2
        tw = measure_text(FONTS["sans_regular"], items, fsize, 0.1)
        if tw > 370.0:
            fsize = fsize * (370.0 / tw)
        items_g = text_to_paths(
            FONTS["sans_regular"],
            items,
            x=174,
            y=sy + 16.0,
            font_size=fsize,
            fill=p["secondary"],
            letter_spacing=0.1,
        )
        stack_svg.append(accent_bar + "\n  " + dom_g + "\n  " + items_g)
        if idx < len(STACK_ROWS) - 1:
            ry = sy + 31.5
            stack_svg.append(
                f'<line x1="24" y1="{ry:.1f}" x2="544" y2="{ry:.1f}" stroke="{p["divider"]}" stroke-width="0.6" stroke-opacity="0.10"/>'
            )

    # ── BAND B RIGHT: Velocity Wave + Real Code Composition Ribbon (x=572..876) ──
    vel_title = text_to_paths(
        FONTS["sans_semibold"], "12-MONTH VELOCITY", x=572, y=144, font_size=10.5, fill=p["accent"], letter_spacing=1.8
    )
    vel_active = text_to_paths(
        FONTS["sans_regular"],
        f"{stats['active_days']} active days",
        x=876,
        y=144,
        font_size=9.5,
        fill=p["muted"],
        align="right",
    )
    monthly = stats["monthly"]
    gx0, gx1 = 572.0, 876.0
    gy_top, gy_bot = 165.0, 222.0
    max_m = max((m["total"] for m in monthly), default=1) or 1
    pts = [
        (gx0 + (gx1 - gx0) * (i / max(len(monthly) - 1, 1)), gy_bot - (gy_bot - gy_top) * (m["total"] / max_m))
        for i, m in enumerate(monthly)
    ]
    curve_d = _smooth_bezier(pts)
    area_d = f"{curve_d} L{pts[-1][0]:.2f},{gy_bot:.2f} L{pts[0][0]:.2f},{gy_bot:.2f} Z"
    peak_idx = max(range(len(monthly)), key=lambda i: monthly[i]["total"])
    pk_x, pk_y = pts[peak_idx]
    pk_label = text_to_paths(
        FONTS["sans_medium"],
        f"{monthly[peak_idx]['total']:,}",
        x=pk_x,
        y=pk_y - 7,
        font_size=9.2,
        fill=p["primary"],
        align="right" if peak_idx >= len(monthly) - 2 else "center",
    )
    m_start = text_to_paths(FONTS["sans_regular"], monthly[0]["label"], x=gx0, y=237, font_size=8.8, fill=p["muted"])
    m_mid = text_to_paths(
        FONTS["sans_regular"],
        monthly[len(monthly) // 2]["label"],
        x=(gx0 + gx1) / 2,
        y=237,
        font_size=8.8,
        fill=p["muted"],
        align="center",
    )
    m_end = text_to_paths(
        FONTS["sans_regular"], monthly[-1]["label"], x=gx1, y=237, font_size=8.8, fill=p["muted"], align="right"
    )

    comp_title = text_to_paths(
        FONTS["sans_semibold"], "CODE COMPOSITION", x=572, y=276, font_size=10.5, fill=p["accent"], letter_spacing=1.8
    )
    langs = stats["languages"]
    bar_x, bar_y, bar_w, bar_h = 572.0, 287.0, 304.0, 10.5
    bar_segs = []
    legend_svg = []
    cur_x = bar_x
    total_pct = sum(x["pct"] for x in langs) or 100.0
    short_names = {"JavaScript": "JS", "TypeScript": "TS"}
    leg_positions = [(572, 316), (674, 316), (776, 316), (572, 334), (674, 334)]

    for i, item in enumerate(langs):
        color = p["lang_colors"][i % len(p["lang_colors"])]
        seg_w = max(4.0, bar_w * (item["pct"] / total_pct))
        if i == len(langs) - 1:
            seg_w = max(3.0, (bar_x + bar_w) - cur_x)
        bar_segs.append(
            f'<rect x="{cur_x:.2f}" y="{bar_y:.1f}" width="{seg_w - 1.5:.2f}" height="{bar_h}" rx="2.5" fill="{color}"/>'
        )
        cur_x += seg_w

        lx, ly = leg_positions[i]
        lbl = f"{short_names.get(item['name'], item['name'])} {item['pct']:.1f}%"
        legend_svg.append(f'<circle cx="{lx + 4}" cy="{ly - 3.5}" r="3.4" fill="{color}"/>')
        legend_svg.append(
            text_to_paths(FONTS["sans_regular"], lbl, x=lx + 12, y=ly, font_size=9.8, fill=p["secondary"], letter_spacing=0.1)
        )

    # ── BAND C: 53-Week Contribution Tapestry + Sunlit/Moonlit Water-Glint Reflection ──
    tap_title = text_to_paths(
        FONTS["sans_semibold"],
        "CONTRIBUTION TAPESTRY  ·  53 WEEKS",
        x=24,
        y=386,
        font_size=10.5,
        fill=p["accent"],
        letter_spacing=1.9,
    )
    leg_y = 378.0
    less_g = text_to_paths(FONTS["sans_regular"], "Less", x=763, y=386, font_size=8.8, fill=p["muted"])
    more_g = text_to_paths(FONTS["sans_regular"], "More", x=850, y=386, font_size=8.8, fill=p["muted"])
    leg_boxes = "".join(
        f'<rect x="{791 + i * 11.4:.1f}" y="{leg_y:.1f}" width="8.6" height="8.6" rx="2.0" fill="{p["heat"][i]}"/>'
        for i in range(5)
    )

    weeks = stats["weeks"]
    non_zero = sorted(d["count"] for w in weeks for d in w if d["count"] > 0)
    q1 = non_zero[len(non_zero) // 4] if non_zero else 1
    q2 = non_zero[len(non_zero) // 2] if non_zero else 4
    q3 = non_zero[(3 * len(non_zero)) // 4] if non_zero else 10

    def level(c: int) -> int:
        if c <= 0:
            return 0
        if c <= q1:
            return 1
        if c <= q2:
            return 2
        if c <= q3:
            return 3
        return 4

    cell = 13.0
    gap = 3.1
    step = cell + gap
    grid_x0 = 24.0
    grid_y0 = 414.0

    cells_svg = []
    months_svg = []
    glint_candidates = []
    last_month = None
    last_label_wi = -4
    glint_classes = ["wg-0", "wg-1", "wg-2", "wg-3", "wg-4", "wg-5"]

    for wi, week in enumerate(weeks):
        wx = grid_x0 + wi * step
        if week:
            m_str = datetime.strptime(week[0]["date"], "%Y-%m-%d").strftime("%b")
            if m_str != last_month:
                if wi < len(weeks) - 2 and (wi - last_label_wi >= 3):
                    months_svg.append(
                        text_to_paths(
                            FONTS["sans_regular"], m_str, x=wx, y=406, font_size=8.8, fill=p["muted"], letter_spacing=0.15
                        )
                    )
                    last_label_wi = wi
                last_month = m_str
        for day in week:
            dy = grid_y0 + day["weekday"] * step
            lvl = level(day["count"])
            fill = p["heat"][lvl]
            if lvl >= 2:
                # Golden-ratio hash so specular water glints dance asynchronously from t=0
                h_idx = (wi * 17 + day["weekday"] * 31) % 6
                neg_delay = -(((wi * 1.618 + day["weekday"] * 0.73) % 7.9) + 0.15)
                cells_svg.append(
                    f'<rect class="{glint_classes[h_idx]}" style="animation-delay:{neg_delay:.2f}s" '
                    f'x="{wx:.1f}" y="{dy:.1f}" width="{cell}" height="{cell}" rx="2.6" fill="{fill}"/>'
                )
                glint_candidates.append((lvl, day["count"], wi, day["weekday"], wx, dy))
            else:
                cells_svg.append(
                    f'<rect x="{wx:.1f}" y="{dy:.1f}" width="{cell}" height="{cell}" rx="2.6" fill="{fill}"/>'
                )

    # Layer 2: ~32 delicate horizontal water-surface specular streaks on active clusters
    glint_candidates.sort(key=lambda item: (-item[0], -item[1], (item[2] * 13 + item[3] * 7) % 19))
    selected_glints = []
    for item in glint_candidates:
        _, _, wi, wd, wx, dy = item
        if any(abs(wi - swi) <= 1 and wd == swd for _, _, swi, swd, _, _ in selected_glints):
            continue
        selected_glints.append(item)
        if len(selected_glints) >= 32:
            break

    streak_classes = ["ws-0", "ws-1", "ws-2", "ws-3", "ws-4"]
    streaks_svg = []
    for idx, (lvl, _, wi, wd, wx, dy) in enumerate(selected_glints):
        half_w = 9.0 if lvl == 4 else 6.8
        cx = wx + cell * 0.5
        cy = dy + (cell * 0.35 if idx % 2 == 0 else cell * 0.65)
        s_cls = streak_classes[(wi + wd + idx) % 5]
        neg_d = -(((idx * 1.37 + wi * 0.41) % 5.9) + 0.1)
        halo_d = f"M{cx - half_w:.1f},{cy:.1f} Q{cx:.1f},{cy - 2.0:.1f} {cx + half_w:.1f},{cy:.1f} Q{cx:.1f},{cy + 2.0:.1f} {cx - half_w:.1f},{cy:.1f} Z"
        core_d = f"M{cx - half_w * 0.72:.1f},{cy:.1f} Q{cx:.1f},{cy - 1.05:.1f} {cx + half_w * 0.72:.1f},{cy:.1f} Q{cx:.1f},{cy + 1.05:.1f} {cx - half_w * 0.72:.1f},{cy:.1f} Z"
        streaks_svg.append(
            f'<g class="{s_cls}" style="animation-delay:{neg_d:.2f}s">'
            f'<path d="{halo_d}" fill="{p["glint_halo"]}" opacity="0.55"/>'
            f'<path d="{core_d}" fill="{p["glint_core"]}"/>'
            f'</g>'
        )

    grid_w = len(weeks) * step - gap
    grid_h = 7 * step - gap

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="540" viewBox="0 0 900 540" role="img" aria-label="Pratik — Cool Impasto Engineering Overview">
  <defs>
    <style>
      @keyframes waterCellGlint {{
        0%, 78%, 100% {{ filter: brightness(1); }}
        86% {{ filter: brightness(1.55); }}
        92% {{ filter: brightness(1.18); }}
      }}
      @keyframes waterStreak {{
        0%, 66%, 100% {{ opacity: 0.04; transform: translateX(-2.5px) scaleX(0.75); }}
        77% {{ opacity: 0.96; transform: translateX(0.8px) scaleX(1.12); }}
        84% {{ opacity: 0.35; transform: translateX(2.0px) scaleX(0.92); }}
        90% {{ opacity: 0.85; transform: translateX(2.8px) scaleX(1.05); }}
      }}
      .wg-0 {{ animation: waterCellGlint 3.7s ease-in-out infinite; }}
      .wg-1 {{ animation: waterCellGlint 4.3s ease-in-out infinite; }}
      .wg-2 {{ animation: waterCellGlint 5.3s ease-in-out infinite; }}
      .wg-3 {{ animation: waterCellGlint 6.1s ease-in-out infinite; }}
      .wg-4 {{ animation: waterCellGlint 7.1s ease-in-out infinite; }}
      .wg-5 {{ animation: waterCellGlint 8.3s ease-in-out infinite; }}
      .ws-0, .ws-1, .ws-2, .ws-3, .ws-4 {{
        transform-box: fill-box;
        transform-origin: center;
      }}
      .ws-0 {{ animation: waterStreak 2.9s ease-in-out infinite; }}
      .ws-1 {{ animation: waterStreak 3.7s ease-in-out infinite; }}
      .ws-2 {{ animation: waterStreak 4.7s ease-in-out infinite; }}
      .ws-3 {{ animation: waterStreak 5.9s ease-in-out infinite; }}
      .ws-4 {{ animation: waterStreak 6.7s ease-in-out infinite; }}
      @media (prefers-reduced-motion: reduce) {{
        .wg-0, .wg-1, .wg-2, .wg-3, .wg-4, .wg-5,
        .ws-0, .ws-1, .ws-2, .ws-3, .ws-4 {{ animation: none; }}
      }}
    </style>
    <linearGradient id="velGrad_{theme}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{p['curve_top']}" stop-opacity="0.36"/>
      <stop offset="100%" stop-color="{p['curve_bot']}" stop-opacity="0.0"/>
    </linearGradient>
    <clipPath id="tapClip_{theme}">
      <rect x="{grid_x0 - 4:.1f}" y="{grid_y0 - 2:.1f}" width="{grid_w + 8:.1f}" height="{grid_h + 4:.1f}" rx="3"/>
    </clipPath>
  </defs>
  <rect width="900" height="540" fill="none"/>

  {name_g}
  {handle_g}
  {role_g}
  {bio_g}
  {''.join(kpis_svg)}

  <line x1="24" y1="108" x2="876" y2="108" stroke="{p['rule']}" stroke-width="0.9" stroke-opacity="0.42"/>

  {''.join(stack_svg)}

  <line x1="556" y1="130" x2="556" y2="338" stroke="{p['divider']}" stroke-width="0.7" stroke-opacity="0.16"/>

  {vel_title}
  {vel_active}
  <line x1="{gx0}" y1="{gy_bot}" x2="{gx1}" y2="{gy_bot}" stroke="{p['axis']}" stroke-width="0.8"/>
  <path d="{area_d}" fill="url(#velGrad_{theme})"/>
  <path d="{curve_d}" fill="none" stroke="{p['curve_stroke']}" stroke-width="2.1" stroke-linecap="round"/>
  <circle cx="{pk_x:.2f}" cy="{pk_y:.2f}" r="3.2" fill="{p['primary']}" stroke="{p['curve_stroke']}" stroke-width="1.5"/>
  {pk_label}
  {m_start}
  {m_mid}
  {m_end}

  {comp_title}
  {''.join(bar_segs)}
  {''.join(legend_svg)}

  <line x1="24" y1="360" x2="876" y2="360" stroke="{p['divider']}" stroke-width="0.7" stroke-opacity="0.16"/>

  {tap_title}
  {less_g}
  {leg_boxes}
  {more_g}
  {''.join(months_svg)}
  {''.join(cells_svg)}
  <g clip-path="url(#tapClip_{theme})" pointer-events="none">
    {''.join(streaks_svg)}
  </g>
</svg>
'''


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    for theme in ("dark", "light"):
        content = build_studio_svg(theme, stats)
        ET.fromstring(content)
        out = ASSETS_DIR / f"studio-cool-{theme}.svg"
        out.write_text(content, encoding="utf-8")
        print(f"Wrote {out.name} ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
