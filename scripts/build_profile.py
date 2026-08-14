"""Generate the profile README and every SVG it references from profile.yml.

Two decisions worth explaining, both learned the hard way.

Colours are inline presentation attributes rather than CSS classes, with a small
dark-mode override appended. Browsers honour the override, so the profile works
on both GitHub themes; offline renderers ignore it, which means this script can
rasterise its own output and the layout can be inspected instead of guessed at.
A stylesheet-only approach renders as unstyled text offline and hides every
spacing mistake until it is already public.

Run:
    python scripts/build_profile.py [--render]

Everything under assets/generated/ is derived. The next build overwrites it.
"""

from __future__ import annotations

import html
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "profile.yml"
OUT_DIR = ROOT / "assets" / "generated"
README = ROOT / "README.md"
PREVIEW = ROOT / "assets" / "preview"

# Light values are inline; the media query swaps them on a dark GitHub.
INK, INK_D = "#1f2328", "#e6edf3"
MUTED, MUTED_D = "#57606a", "#8b949e"
LABEL, LABEL_D = "#656d76", "#7d8590"
LINE, LINE_D = "#d0d7de", "#30363d"
SOFT, SOFT_D = "#eaeef2", "#21262d"
CARD, CARD_D = "#f6f8fa", "#161b22"

DARK = (
    "<style>@media(prefers-color-scheme:dark){"
    f".ink{{fill:{INK_D}}}.muted{{fill:{MUTED_D}}}.lbl{{fill:{LABEL_D}}}"
    f".ln{{stroke:{LINE_D}}}.sln{{stroke:{SOFT_D}}}"
    f".cd{{fill:{CARD_D};stroke:{LINE_D}}}.ar{{stroke:{LABEL_D}}}"
    "}</style>"
)

SERIF = "Georgia,'Times New Roman',serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace"
UI = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

SERIF_R, MONO_R, UI_R = 0.47, 0.60, 0.53


@dataclass(frozen=True)
class Size:
    name: str
    width: int
    head: float
    copy: float
    val: float
    title: float
    desc: float
    card: int


DESKTOP = Size("desktop", 880, 32, 11.5, 13, 14, 12.5, 430)
MOBILE = Size("mobile", 420, 19, 10, 11.5, 13, 11.5, 420)
SIZES = (DESKTOP, MOBILE)

ASSETS: dict[str, str] = {}


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def wrap(s: str, fs: float, maxw: float, ratio: float) -> list[str]:
    lines: list[str] = []
    cur = ""
    for w in s.split():
        cand = f"{cur} {w}".strip()
        if cur and len(cand) * fs * ratio > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def txt(
    s: str,
    x: float,
    y: float,
    *,
    fs: float,
    font: str,
    fill: str,
    cls: str,
    weight: str = "400",
    ls: float = 0,
    italic: bool = False,
    anchor: str = "start",
) -> str:
    style = ' font-style="italic"' if italic else ""
    spacing = f' letter-spacing="{ls}"' if ls else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{fs:g}" '
        f'font-weight="{weight}" fill="{fill}" class="{cls}" text-anchor="{anchor}"'
        f"{style}{spacing}>{esc(s)}</text>"
    )


def block(lines: list[str], x: float, y: float, lh: float, **kw: Any) -> tuple[str, float]:
    out = "".join(txt(l, x, y + i * lh, **kw) for i, l in enumerate(lines))
    return out, y + lh * (len(lines) - 1)


def hline(y: float, x1: float, x2: float, soft: bool = False) -> str:
    c, cls = (SOFT, "sln") if soft else (LINE, "ln")
    return f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{c}" class="{cls}"/>'


def vline(x: float, y1: float, y2: float) -> str:
    return f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" stroke="{SOFT}" class="sln"/>'


def card_rect(w: float, h: float) -> str:
    return (
        f'<rect x=".5" y=".5" width="{w - 1:.1f}" height="{h - 1:.1f}" rx="10" '
        f'fill="{CARD}" stroke="{LINE}" class="cd"/>'
    )


def svg(w: float, h: float, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" '
        f'height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">{DARK}{body}</svg>'
    )


def write(name: str, size: Size, content: str) -> None:
    """Stable filenames, deliberately.

    An earlier version hashed the filename to defeat GitHub's image proxy. That
    proxy is not in the path: README images living in the same repo are served
    straight from /raw/, so there was no cache to defeat. Renaming every asset on
    every build only guaranteed that any cached copy of the rendered README
    pointed at files that had just been deleted, which is what produced the
    broken images.
    """
    key = f"{name}-{size.name}"
    fn = f"{key}.svg"
    (OUT_DIR / fn).write_text(content, encoding="utf-8")
    ASSETS[key] = fn


# --------------------------------------------------------------------------- #


def build_hero(cfg: dict[str, Any], s: Size) -> None:
    w, pad = s.width, 4
    head = wrap(cfg["headline"], s.head, w - pad * 2, SERIF_R)
    copy = wrap(cfg["copy"], s.copy, w - pad * 2, MONO_R)

    b = [hline(6, 2, w - 2)]
    y = 16 + s.head
    part, y = block(head, pad, y, s.head * 1.28, fs=s.head, font=SERIF, fill=INK,
                    cls="ink", weight="600", italic=True)
    b.append(part)
    y += s.copy * 2.7
    part, y = block(copy, pad + 1, y, s.copy * 1.6, fs=s.copy, font=MONO, fill=MUTED,
                    cls="muted")
    b.append(part)
    y += 20
    b.append(hline(y, 2, w - 2))
    write("hero", s, svg(w, y + 8, "".join(b)))


def build_status(items: list[dict[str, str]], s: Size) -> None:
    w = s.width
    if s.name == "mobile":
        row = 38.0
        b = [hline(0.5, 0, w)]
        for i, it in enumerate(items):
            y = 22 + i * row
            if i:
                b.append(hline(y - 16, 0, w, soft=True))
            b.append(txt(it["label"], 12, y, fs=9, font=MONO, fill=LABEL, cls="lbl",
                         weight="600", ls=1.4))
            b.append(txt(it["value"], 12, y + 17, fs=s.val, font=MONO, fill=INK,
                         cls="ink", weight="500"))
        h = 22 + row * len(items)
        b.append(hline(h - 0.5, 0, w))
        write("status", s, svg(w, h, "".join(b)))
        return

    col = w / len(items)
    b = [hline(0.5, 0, w)]
    for i, it in enumerate(items):
        x = i * col + 14
        if i:
            b.append(vline(i * col, 14, 58))
        b.append(txt(it["label"], x, 28, fs=9, font=MONO, fill=LABEL, cls="lbl",
                     weight="600", ls=1.4))
        b.append(txt(it["value"], x, 49, fs=s.val, font=MONO, fill=INK, cls="ink",
                     weight="500"))
    b.append(hline(71.5, 0, w))
    write("status", s, svg(w, 72, "".join(b)))


def build_section(name: str, heading: str, s: Size) -> None:
    b = txt(heading, 2, 22, fs=15, font=UI, fill=INK, cls="ink", weight="500")
    b += hline(35, 2, s.width - 2)
    write(name, s, svg(s.width, 42, b))


def build_contact(item: dict[str, Any], s: Size) -> None:
    w = 208 if s.name == "desktop" else 200
    h, ic = 68, 26
    tx = 16 + ic + 12
    b = [
        card_rect(w, h),
        f'<rect x="16" y="{(h - ic) / 2:.1f}" width="{ic}" height="{ic}" rx="7" '
        f'fill="{item["color"]}"/>',
        txt(item["mark"], 16 + ic / 2, h / 2 + 4, fs=10.5, font=MONO, fill="#ffffff",
            cls="", weight="700", anchor="middle"),
        txt(item["label"], tx, h / 2 - 8, fs=8.5, font=MONO, fill=LABEL, cls="lbl",
            weight="600", ls=1.3),
        txt(item["value"], tx, h / 2 + 13, fs=11.5, font=MONO, fill=INK, cls="ink",
            weight="600"),
        f'<path d="M{w - 22} {h / 2 + 4:.1f} L{w - 15} {h / 2 - 3:.1f} '
        f'M{w - 20} {h / 2 - 3:.1f} H{w - 15} V{h / 2 + 2:.1f}" fill="none" '
        f'stroke="{LABEL}" class="ar" stroke-width="1.2" stroke-linecap="round" '
        f'stroke-linejoin="round"/>',
    ]
    write(f'contact-{item["id"]}', s, svg(w, h, "".join(b)))


def entry(item: dict[str, Any], x: float, colw: float, s: Size, y0: float) -> tuple[str, float]:
    """Category label, then title, then body. Returns the markup and the baseline
    of the last line so callers can size the container to the content."""
    b = []
    part, y = block(wrap(item["category"], 9, colw, MONO_R), x, y0, 11, fs=9,
                    font=MONO, fill=LABEL, cls="lbl", weight="600", ls=1.1)
    b.append(part)
    y += s.title * 1.75
    part, y = block(wrap(item["title"], s.title, colw, UI_R), x, y, s.title * 1.3,
                    fs=s.title, font=UI, fill=INK, cls="ink", weight="600")
    b.append(part)
    y += s.desc * 1.95
    part, y = block(wrap(item["body"], s.desc, colw, UI_R), x, y, s.desc * 1.45,
                    fs=s.desc, font=UI, fill=MUTED, cls="muted")
    b.append(part)
    return "".join(b), y


def build_featured(cfg: dict[str, Any], s: Size) -> None:
    items, w = cfg["items"], s.width
    b = [
        txt(cfg["heading"], 2, 22, fs=15, font=UI, fill=INK, cls="ink", weight="500"),
        hline(35, 2, w - 2),
    ]

    if s.name == "mobile":
        y = 66.0
        for i, it in enumerate(items):
            part, y = entry(it, 6, w - 16, s, y)
            y += 28
            b.append(part)
            if i < len(items) - 1:
                b.append(hline(y - 15, 0, w, soft=True))
        b.append(hline(y - 10, 0, w))
        write("featured", s, svg(w, y, "".join(b)))
        return

    col = w / len(items)
    bottom = 0.0
    for i, it in enumerate(items):
        part, y = entry(it, i * col + (4 if i == 0 else 22), col - 36, s, 68)
        b.append(part)
        bottom = max(bottom, y)
    for i in range(1, len(items)):
        b.append(vline(i * col, 50, bottom + 16))
    b.append(hline(bottom + 26, 0, w))
    write("featured", s, svg(w, bottom + 34, "".join(b)))


def build_current(items: list[dict[str, Any]], s: Size) -> None:
    cw = s.card
    for i, it in enumerate(items):
        part, y = entry(it, 16, cw - 36, s, 30)
        write(f"current-{i}", s, svg(cw, y + 24, card_rect(cw, y + 24) + part))


def build_cert(i: int, item: dict[str, Any], s: Size) -> None:
    w = s.card if s.name == "desktop" else s.width
    h, ic = 70, 28
    tx = 16 + ic + 12
    b = [
        card_rect(w, h),
        f'<rect x="16" y="{(h - ic) / 2:.1f}" width="{ic}" height="{ic}" rx="8" '
        f'fill="{item["color"]}"/>',
        txt(item["mark"], 16 + ic / 2, h / 2 + 4, fs=10.5, font=MONO, fill="#ffffff",
            cls="", weight="700", anchor="middle"),
        txt(item["label"], tx, h / 2 - 6, fs=12.5, font=UI, fill=INK, cls="ink",
            weight="600"),
        txt(item["detail"], tx, h / 2 + 13, fs=9, font=MONO, fill=LABEL, cls="lbl",
            weight="600", ls=1),
    ]
    write(f"cert-{i}", s, svg(w, h, "".join(b)))


# --------------------------------------------------------------------------- #



def build_all(cfg: dict[str, Any], s: Size) -> None:
    """Every visual block in one asset.

    The profile previously shipped seventeen separate images. GitHub serves
    same-repo README images straight from /raw/, which is rate limited, so a
    different random subset failed on each page load and the profile looked
    broken in a different place every time. One request removes the failure mode
    entirely. The cost is that the blocks are no longer individually linkable,
    which the accessible text section below already covers.
    """
    w = s.width
    parts: list[str] = []
    y = 0.0

    def place(markup: str, height: float, gap: float = 0) -> None:
        nonlocal y
        parts.append(f'<g transform="translate(0,{y:.1f})">{markup}</g>')
        y += height + gap

    head = wrap(cfg["hero"]["headline"], s.head, w - 8, SERIF_R)
    copy = wrap(cfg["hero"]["copy"], s.copy, w - 8, MONO_R)
    hb = [hline(6, 2, w - 2)]
    hy = 16 + s.head
    part, hy = block(head, 4, hy, s.head * 1.28, fs=s.head, font=SERIF, fill=INK,
                     cls="ink", weight="600", italic=True)
    hb.append(part)
    hy += s.copy * 2.7
    part, hy = block(copy, 5, hy, s.copy * 1.6, fs=s.copy, font=MONO, fill=MUTED, cls="muted")
    hb.append(part)
    hy += 20
    hb.append(hline(hy, 2, w - 2))
    place("".join(hb), hy + 6)

    col = w / len(cfg["status"])
    sb = [hline(0.5, 0, w)]
    for i, it in enumerate(cfg["status"]):
        x = i * col + 14
        if i:
            sb.append(vline(i * col, 14, 58))
        sb.append(txt(it["label"], x, 28, fs=9, font=MONO, fill=LABEL, cls="lbl",
                      weight="600", ls=1.4))
        sb.append(txt(it["value"], x, 49, fs=s.val, font=MONO, fill=INK, cls="ink", weight="500"))
    sb.append(hline(71.5, 0, w))
    place("".join(sb), 72, 26)

    for group in (cfg["featured"], cfg["current"]):
        gb = [txt(group["heading"], 2, 22, fs=15, font=UI, fill=INK, cls="ink", weight="500"),
              hline(35, 2, w - 2)]
        items = group["items"]
        per_row = 3 if group is cfg["featured"] else 2
        cw = w / per_row
        rows = [items[i:i + per_row] for i in range(0, len(items), per_row)]
        gy = 58.0
        for row in rows:
            bottom = gy
            for i, it in enumerate(row):
                part, ey = entry(it, i * cw + (4 if i == 0 else 22), cw - 36, s, gy + 12)
                gb.append(part)
                bottom = max(bottom, ey)
            for i in range(1, len(row)):
                gb.append(vline(i * cw, gy, bottom + 12))
            gy = bottom + 34
            if row is not rows[-1]:
                gb.append(hline(gy - 16, 0, w, soft=True))
        gb.append(hline(gy - 6, 0, w))
        place("".join(gb), gy + 4, 22)

    cb = [txt(cfg["certifications"]["heading"], 2, 22, fs=15, font=UI, fill=INK,
              cls="ink", weight="500"), hline(35, 2, w - 2)]
    cy = 52.0
    for i, c in enumerate(cfg["certifications"]["items"]):
        cw2, ic = w / 2, 26
        cx = (i % 2) * cw2
        ry = cy + (i // 2) * 76
        cb.append(f'<rect x="{cx + 4:.1f}" y="{ry:.1f}" width="{cw2 - 20:.1f}" height="62" '
                  f'rx="10" fill="{CARD}" stroke="{LINE}" class="cd"/>')
        cb.append(f'<rect x="{cx + 20:.1f}" y="{ry + 18:.1f}" width="{ic}" height="{ic}" '
                  f'rx="8" fill="{c["color"]}"/>')
        cb.append(txt(c["mark"], cx + 20 + ic / 2, ry + 36, fs=10.5, font=MONO,
                      fill="#ffffff", cls="", weight="700", anchor="middle"))
        cb.append(txt(c["label"], cx + 60, ry + 27, fs=12.5, font=UI, fill=INK,
                      cls="ink", weight="600"))
        cb.append(txt(c["detail"], cx + 60, ry + 45, fs=9, font=MONO, fill=LABEL,
                      cls="lbl", weight="600", ls=1))
    rows_n = (len(cfg["certifications"]["items"]) + 1) // 2
    place("".join(cb), cy + rows_n * 76)

    write("profile", s, svg(w, y, "".join(parts)))


def pic(name: str, alt: str, *, width: str | None = None) -> str:
    w = f' width="{width}"' if width else ""
    return (
        "<picture>"
        f'<source media="(max-width: 480px)" srcset="./assets/generated/{ASSETS[name + "-mobile"]}">'
        f'<img src="./assets/generated/{ASSETS[name + "-desktop"]}"{w} alt="{esc(alt)}">'
        "</picture>"
    )


def link(url: str | None, inner: str) -> str:
    return f'<a href="{url}">{inner}</a>' if url else inner


def build_readme(cfg: dict[str, Any]) -> str:
    contacts = " · ".join(
        f'[{c["label"].title()}]({c["url"]})' for c in cfg["contact"]
    )

    acc: list[str] = []
    for group in (cfg["featured"], cfg["current"]):
        acc += [f'## {group["heading"]}', ""]
        for it in group["items"]:
            t = f'[{it["title"]}]({it["url"]})' if it.get("url") else it["title"]
            acc += [f"### {t}", f'*{it["category"]}*', "", it["body"], ""]
    acc += [f'## {cfg["certifications"]["heading"]}', ""]
    acc += [f'- **{c["label"]}**: {c["detail"]}' for c in cfg["certifications"]["items"]]

    alt = (f'Arthur Torres. {cfg["hero"]["headline"]} '
           + " ".join(f'{x["label"]}: {x["value"]}.' for x in cfg["status"]))

    return f"""<div align="center">

{pic("profile", alt, width="100%")}

{contacts}

</div>

<details>
<summary>Accessible text version</summary>

{chr(10).join(acc)}

</details>

<!-- Generated from profile.yml. Edit profile.yml, then run python scripts/build_profile.py. -->
"""


def render_previews() -> None:
    """Rasterise every desktop asset so the layout can be eyeballed before publishing."""
    from reportlab.graphics import renderPM
    from svglib.svglib import svg2rlg

    if PREVIEW.exists():
        shutil.rmtree(PREVIEW)
    PREVIEW.mkdir(parents=True)
    for src in sorted(OUT_DIR.glob("*-desktop.*.svg")):
        drawing = svg2rlg(str(src))
        if drawing is None:
            continue
        renderPM.drawToFile(drawing, str(PREVIEW / f'{src.name.split(".")[0]}.png'),
                            fmt="PNG", bg=0xFFFFFF, dpi=144)
    print(f"previews in {PREVIEW.relative_to(ROOT)}")


def main() -> None:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    for s in SIZES:
        build_all(cfg, s)

    README.write_text(build_readme(cfg), encoding="utf-8")
    print(f"{len(list(OUT_DIR.glob('*.svg')))} SVGs written")

    if "--render" in sys.argv:
        render_previews()


if __name__ == "__main__":
    main()
