"""Generate the profile README and every SVG it references from profile.yml.

Why SVG instead of markdown: GitHub strips CSS from README markdown, so shipping
pictures is the only way to control typography and layout.

Design language, deliberately borrowed from a profile Arthur liked: GitHub's own
light palette, hairlines rather than boxes as the structural device, one serif
italic headline, and monospace at small sizes for everything else. The restraint
is the point. A dark card stack with big sans type reads as a template; this
reads as a page someone set.

Two widths are emitted for every asset. The README picks between them with
<picture><source media="(max-width: 480px)">, which GitHub honours.

Run:
    python scripts/build_profile.py

Everything under assets/generated/ is derived. The next build overwrites it.
"""

from __future__ import annotations

import html
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "profile.yml"
OUT_DIR = ROOT / "assets" / "generated"
README = ROOT / "README.md"

XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>'

# GitHub light palette, so the cards sit on the page instead of on top of it.
INK = "#1f2328"
MUTED = "#57606a"
LABEL = "#656d76"
LINE = "#d0d7de"
SOFT = "#eaeef2"
CARD = "#f6f8fa"

STYLE = f"""<style>
.line{{stroke:{LINE};stroke-width:1}}
.soft-line{{stroke:{SOFT};stroke-width:1}}
.card{{fill:{CARD};stroke:{LINE};stroke-width:1}}
.headline{{font:italic 600 {{HEADLINE}}px Georgia,'Times New Roman',serif;fill:{INK}}}
.copy{{font:400 {{COPY}}px ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;fill:{MUTED}}}
.label{{font:600 9px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.4px;fill:{LABEL}}}
.value{{font:500 {{VALUE}}px ui-monospace,SFMono-Regular,Menlo,monospace;fill:{INK}}}
.section{{font:500 15px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:{INK}}}
.title{{font:600 {{TITLE}}px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:{INK}}}
.category{{font:600 9px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1.1px;fill:{LABEL}}}
.desc{{font:400 {{DESC}}px -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:{MUTED}}}
.arrow{{stroke:{LABEL};fill:none;stroke-width:1.2;stroke-linecap:round;stroke-linejoin:round}}
.mark{{font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace;fill:#ffffff}}
</style>"""


@dataclass(frozen=True)
class Size:
    name: str
    width: int
    headline: float
    copy: float
    value: float
    title: float
    desc: float
    card_w: int


DESKTOP = Size("desktop", 880, 34, 11, 13, 14, 12.5, 390)
MOBILE = Size("mobile", 420, 17, 9, 11, 12.5, 11, 420)
SIZES = (DESKTOP, MOBILE)

# No font metrics at build time, so text is laid out with an estimated advance.
SERIF_RATIO = 0.46
MONO_RATIO = 0.60
UI_RATIO = 0.53


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def wrap(s: str, font_size: float, max_width: float, ratio: float) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if cur and len(cand) * font_size * ratio > max_width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def tspans(lines: list[str], x: float, dy: float) -> str:
    out = [f'<tspan x="{x:.1f}" dy="0">{esc(lines[0])}</tspan>']
    out += [f'<tspan x="{x:.1f}" dy="{dy:.0f}">{esc(l)}</tspan>' for l in lines[1:]]
    return "".join(out)


def svg(width: float, height: float, body: str, size: Size) -> str:
    style = (
        STYLE.replace("{HEADLINE}", f"{size.headline:g}")
        .replace("{COPY}", f"{size.copy:g}")
        .replace("{VALUE}", f"{size.value:g}")
        .replace("{TITLE}", f"{size.title:g}")
        .replace("{DESC}", f"{size.desc:g}")
    )
    return (
        f'{XML_DECL}<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">{style}{body}</svg>'
    )


def write(name: str, size: Size, content: str) -> None:
    (OUT_DIR / f"{name}-{size.name}.svg").write_text(content, encoding="utf-8")


def rule(y: float, w: float, cls: str = "line", x: float = 2) -> str:
    return f'<line class="{cls}" x1="{x}" y1="{y:.1f}" x2="{w - x:.1f}" y2="{y:.1f}"/>'


# --------------------------------------------------------------------------- #


def build_hero(cfg: dict[str, Any], size: Size) -> None:
    """Geometry copied from the reference profile rather than derived, so the
    rhythm matches instead of approximating it."""
    w = size.width
    head = wrap(cfg["headline"], size.headline, w - 8, SERIF_RATIO)
    copy = wrap(cfg["copy"], size.copy, w - 12, MONO_RATIO)

    head_lh = size.headline * 1.25
    copy_lh = size.copy * 1.5
    head_y = 58 if size.name == "desktop" else 34
    copy_y = 92 if size.name == "desktop" else 58

    body = [rule(8, w)]
    body.append(f'<text x="2" y="{head_y}" class="headline">{tspans(head, 2, head_lh)}</text>')
    body.append(f'<text x="4" y="{copy_y + head_lh * (len(head) - 1):.1f}" class="copy">'
                f'{tspans(copy, 4, copy_lh)}</text>')
    bottom = copy_y + head_lh * (len(head) - 1) + copy_lh * (len(copy) - 1) + 22
    body.append(rule(bottom, w))
    write("hero", size, svg(w, bottom + 9, "".join(body), size))


def build_status(items: list[dict[str, str]], size: Size) -> None:
    w = size.width
    if size.name == "mobile":
        row = 34.0
        h = row * len(items) + 10
        body = [rule(0.5, w, x=0)]
        for i, it in enumerate(items):
            y = 14 + i * row
            body.append(f'<text x="12" y="{y:.1f}" class="label">{esc(it["label"])}</text>')
            body.append(f'<text x="12" y="{y + 15:.1f}" class="value">{esc(it["value"])}</text>')
            if i:
                body.append(rule(y - 12, w, "soft-line", x=0))
        body.append(rule(h - 0.5, w, x=0))
        write("status", size, svg(w, h, "".join(body), size))
        return

    col = w / len(items)
    body = [rule(0.5, w, x=0)]
    for i, it in enumerate(items):
        x = i * col + 12
        if i:
            body.append(f'<line class="line" x1="{i * col:.1f}" y1="16" x2="{i * col:.1f}" y2="56"/>')
        body.append(f'<text x="{x:.1f}" y="28" class="label">{esc(it["label"])}</text>')
        body.append(f'<text x="{x:.1f}" y="49" class="value">{esc(it["value"])}</text>')
    body.append(rule(71.5, w, x=0))
    write("status", size, svg(w, 72, "".join(body), size))


def build_section(name: str, heading: str, size: Size) -> None:
    body = f'<text x="2" y="22" class="section">{esc(heading)}</text>' + rule(35, size.width)
    write(name, size, svg(size.width, 42, body, size))


def build_contact(item: dict[str, Any], size: Size) -> None:
    w = 265 if size.name == "desktop" else 200
    h = 76 if size.name == "desktop" else 64
    icon = 28 if size.name == "desktop" else 24
    tx = 20 + icon + 12

    body = [
        f'<rect class="card" x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10"/>',
        f'<rect x="20" y="{(h - icon) / 2:.1f}" width="{icon}" height="{icon}" rx="7" '
        f'fill="{item["color"]}"/>',
        f'<text x="{20 + icon / 2:.1f}" y="{h / 2 + 4:.1f}" class="mark" '
        f'text-anchor="middle">{esc(item["mark"])}</text>',
        f'<text x="{tx}" y="{h / 2 - 9:.1f}" class="label">{esc(item["label"])}</text>',
        f'<text x="{tx}" y="{h / 2 + 14:.1f}" class="value">{esc(item["value"])}</text>',
        f'<path d="M{w - 24} {h / 2 + 4:.1f} L{w - 16} {h / 2 - 4:.1f} '
        f'M{w - 21} {h / 2 - 4:.1f} H{w - 16} V{h / 2 + 1:.1f}" class="arrow"/>',
    ]
    write(f'contact-{item["id"]}', size, svg(w, h, "".join(body), size))


def _entry(item: dict[str, Any], x: float, col_w: float, size: Size) -> tuple[str, float]:
    """One featured/current entry laid out in a column. Returns body and bottom y."""
    title = wrap(item["title"], size.title, col_w, UI_RATIO)
    cat = wrap(item["category"], 9, col_w, MONO_RATIO)
    desc = wrap(item["body"], size.desc, col_w, UI_RATIO)

    t_lh, d_lh = size.title * 1.3, size.desc * 1.35
    y = 22 + size.title
    parts = [f'<text x="{x:.1f}" y="{y:.1f}" class="title">{tspans(title, x, t_lh)}</text>']
    y += t_lh * (len(title) - 1) + 22
    parts.append(f'<text x="{x:.1f}" y="{y:.1f}" class="category">{tspans(cat, x, 11)}</text>')
    y += 11 * (len(cat) - 1) + 24
    parts.append(f'<text x="{x:.1f}" y="{y:.1f}" class="desc">{tspans(desc, x, d_lh)}</text>')
    y += d_lh * (len(desc) - 1) + 16
    return "".join(parts), y


def build_featured(cfg: dict[str, Any], size: Size) -> None:
    """Desktop: three columns in one SVG. Mobile: one card per item."""
    items = cfg["items"]
    if size.name == "mobile":
        for i, item in enumerate(items):
            b, y = _entry(item, 8, size.width - 20, size)
            write(f"featured-{i}", size, svg(size.width, y + 10, b + rule(y, size.width, x=0), size))
        return

    w = size.width
    col = w / len(items)
    body = [f'<text x="2" y="22" class="section">{esc(cfg["heading"])}</text>', rule(35, w)]
    bottom = 0.0
    for i, item in enumerate(items):
        x = i * col + (8 if i == 0 else 20)
        b, y = _entry(item, x, col - 34, size)
        body.append(f'<g transform="translate(0,34)">{b}</g>')
        bottom = max(bottom, y + 34)
        if i:
            body.append(
                f'<line class="soft-line" x1="{i * col:.1f}" y1="54" '
                f'x2="{i * col:.1f}" y2="{bottom + 6:.0f}"/>'
            )
    body.append(rule(bottom + 14, w, x=0))
    write("featured", size, svg(w, bottom + 24, "".join(body), size))


def build_current(items: list[dict[str, Any]], size: Size) -> None:
    """Two cards per row on desktop, one per row on mobile."""
    cw = size.card_w
    for i, item in enumerate(items):
        b, y = _entry(item, 10, cw - 24, size)
        write(f"current-{i}", size, svg(cw, y + 10, b + rule(y, cw, x=0), size))


def build_cert(i: int, item: dict[str, Any], size: Size) -> None:
    w = size.card_w if size.name == "desktop" else size.width
    h = 74 if size.name == "desktop" else 66
    icon = 30 if size.name == "desktop" else 26
    tx = 16 + icon + 12

    body = [
        f'<rect class="card" x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="9"/>',
        f'<rect x="16" y="{(h - icon) / 2:.1f}" width="{icon}" height="{icon}" rx="8" '
        f'fill="{item["color"]}"/>',
        f'<text x="{16 + icon / 2:.1f}" y="{h / 2 + 4:.1f}" class="mark" '
        f'text-anchor="middle">{esc(item["mark"])}</text>',
        f'<text x="{tx}" y="{h / 2 - 6:.1f}" class="title">{esc(item["label"])}</text>',
        f'<text x="{tx}" y="{h / 2 + 14:.1f}" class="category">{esc(item["detail"])}</text>',
    ]
    write(f"cert-{i}", size, svg(w, h, "".join(body), size))


# --------------------------------------------------------------------------- #


def pic(name: str, alt: str, *, width: str | None = None) -> str:
    w = f' width="{width}"' if width else ""
    return (
        "<picture>"
        f'<source media="(max-width: 480px)" srcset="./assets/generated/{name}-mobile.svg">'
        f'<img src="./assets/generated/{name}-desktop.svg"{w} alt="{esc(alt)}">'
        "</picture>"
    )


def link(url: str | None, inner: str) -> str:
    return f'<a href="{url}">{inner}</a>' if url else inner


def build_readme(cfg: dict[str, Any]) -> str:
    contacts = "".join(link(c["url"], pic(f'contact-{c["id"]}', f'{c["label"]}: {c["value"]}')) for c in cfg["contact"])

    featured_mobile = "".join(
        link(it.get("url"), pic(f"featured-{i}", it["title"], width="100%"))
        for i, it in enumerate(cfg["featured"]["items"])
    )
    current = "".join(link(it.get("url"), pic(f"current-{i}", it["title"])) for i, it in enumerate(cfg["current"]["items"]))
    certs = "".join(pic(f"cert-{i}", f'{c["label"]} — {c["detail"]}') for i, c in enumerate(cfg["certifications"]["items"]))

    acc = ["## " + cfg["featured"]["heading"], ""]
    for group in (cfg["featured"], cfg["current"]):
        if group is not cfg["featured"]:
            acc += ["## " + group["heading"], ""]
        for it in group["items"]:
            t = f'[{it["title"]}]({it["url"]})' if it.get("url") else it["title"]
            acc += [f"### {t}", f'*{it["category"]}*', "", it["body"], ""]
    acc += ["## " + cfg["certifications"]["heading"], ""]
    acc += [f'- **{c["label"]}** — {c["detail"]}' for c in cfg["certifications"]["items"]]

    return f"""<div align="center">
{pic("hero", f'Arthur Torres. {cfg["hero"]["headline"]}', width="100%")}
{pic("status", " ".join(f'{s["label"]}: {s["value"]}.' for s in cfg["status"]), width="100%")}
</div>

<br>

<p align="center">
{contacts}
</p>

<picture><source media="(max-width: 480px)" srcset="./assets/generated/featured-header-mobile.svg"><img src="./assets/generated/featured-header-desktop.svg" width="100%" alt="{esc(cfg["featured"]["heading"])}"></picture>

{featured_mobile}

{pic("current-header", cfg["current"]["heading"], width="100%")}

<p align="center">
{current}
</p>

{pic("certifications-header", cfg["certifications"]["heading"], width="100%")}

<p align="center">
{certs}
</p>

<details>
<summary>Accessible text version</summary>

{chr(10).join(acc)}

</details>

<!-- Generated from profile.yml. Edit profile.yml, then run python scripts/build_profile.py. -->
"""


def main() -> None:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    for size in SIZES:
        build_hero(cfg["hero"], size)
        build_status(cfg["status"], size)
        for c in cfg["contact"]:
            build_contact(c, size)
        build_section("featured-header", cfg["featured"]["heading"], size)
        build_featured(cfg["featured"], size)
        build_section("current-header", cfg["current"]["heading"], size)
        build_current(cfg["current"]["items"], size)
        build_section("certifications-header", cfg["certifications"]["heading"], size)
        for i, c in enumerate(cfg["certifications"]["items"]):
            build_cert(i, c, size)

    README.write_text(build_readme(cfg), encoding="utf-8")
    print(f"{len(list(OUT_DIR.glob('*.svg')))} SVGs written")


if __name__ == "__main__":
    main()
