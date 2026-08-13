"""Generate the profile README and every SVG it references from profile.yml.

Why SVG instead of markdown: GitHub strips CSS from README markdown, so the only
way to control typography and layout is to ship pictures. Each SVG carries its own
background, which also means the profile looks deliberate on both the light and the
dark GitHub themes instead of inheriting one and breaking on the other.

Two widths are emitted for every asset. The README picks between them with
<picture><source media="(max-width: 480px)">, which GitHub honours.

No third-party dependencies beyond PyYAML, and no network calls. Run:

    python scripts/build_profile.py

Everything under assets/generated/ is derived. Editing those files by hand is
pointless, the next build overwrites them.
"""

from __future__ import annotations

import html
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "profile.yml"
OUT_DIR = ROOT / "assets" / "generated"
README = ROOT / "README.md"

# GitHub proxies README images through camo. An explicit declaration removes any
# doubt about how the middle dots and accented characters are decoded.
XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>'

SANS = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"

# SVG has no font metrics at build time, so text is laid out with an estimated
# advance width. These ratios are deliberately generous: overestimating means a
# line wraps early, underestimating means it overflows the card.
SANS_RATIO = 0.54
MONO_RATIO = 0.62


@dataclass(frozen=True)
class Size:
    """One of the two rendering targets."""

    name: str
    width: int
    pad: int
    scale: float


DESKTOP = Size(name="desktop", width=880, pad=36, scale=1.0)
MOBILE = Size(name="mobile", width=420, pad=22, scale=0.86)
SIZES = (DESKTOP, MOBILE)


def text_width(s: str, font_size: float, mono: bool = False) -> float:
    ratio = MONO_RATIO if mono else SANS_RATIO
    return len(s) * font_size * ratio


def wrap(s: str, font_size: float, max_width: float, mono: bool = False) -> list[str]:
    """Greedy wrap using the estimated advance width."""
    words = s.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate, font_size, mono) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate

    if current:
        lines.append(current)
    return lines


def esc(s: str) -> str:
    return html.escape(s, quote=False)


class Svg:
    """Minimal SVG builder. Tracks height so cards can size themselves to content."""

    def __init__(self, width: int, theme: dict[str, str]) -> None:
        self.width = width
        self.theme = theme
        self.parts: list[str] = []
        self.y = 0.0

    def advance(self, dy: float) -> None:
        self.y += dy

    def text(
        self,
        content: str,
        *,
        x: float,
        size: float,
        fill: str,
        weight: str = "400",
        mono: bool = False,
        letter_spacing: float = 0.0,
        anchor: str = "start",
    ) -> None:
        family = MONO if mono else SANS
        spacing = f' letter-spacing="{letter_spacing}"' if letter_spacing else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{self.y:.1f}" font-family="{family}" '
            f'font-size="{size:.1f}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{spacing}>{esc(content)}</text>'
        )

    def rect(
        self,
        *,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str,
        stroke: str | None = None,
        radius: float = 0,
    ) -> None:
        stroke_attr = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{radius:.1f}" fill="{fill}"{stroke_attr}/>'
        )

    def render(self, height: float, *, radius: float = 10) -> str:
        body = "".join(self.parts)
        return (
            XML_DECL
            + f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{height:.0f}" viewBox="0 0 {self.width} {height:.0f}" '
            f'role="img">'
            f'<rect width="{self.width}" height="{height:.0f}" rx="{radius}" '
            f'fill="{self.theme["background"]}"/>'
            f'<rect x="0.5" y="0.5" width="{self.width - 1}" height="{height - 1:.0f}" '
            f'rx="{radius}" fill="none" stroke="{self.theme["border"]}"/>'
            f"{body}</svg>"
        )


def write(name: str, size: Size, content: str) -> None:
    path = OUT_DIR / f"{name}-{size.name}.svg"
    path.write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Blocks
# --------------------------------------------------------------------------- #


def build_hero(cfg: dict[str, Any], theme: dict[str, str], size: Size) -> None:
    svg = Svg(size.width, theme)
    inner = size.width - size.pad * 2

    name_size = 40 * size.scale
    tag_size = 17 * size.scale

    svg.advance(size.pad + name_size * 0.82)
    svg.text(
        cfg["name"],
        x=size.pad,
        size=name_size,
        fill=theme["text"],
        weight="700",
        letter_spacing=-0.5,
    )

    svg.advance(tag_size * 1.9)
    for line in wrap(cfg["tagline"], tag_size, inner):
        svg.text(line, x=size.pad, size=tag_size, fill=theme["muted"])
        svg.advance(tag_size * 1.5)

    svg.advance(-tag_size * 1.5)
    svg.advance(size.pad)
    write("hero", size, svg.render(svg.y))


def build_status(cfg: dict[str, Any], theme: dict[str, str], size: Size) -> None:
    svg = Svg(size.width, theme)
    inner = size.width - size.pad * 2 - 14
    font = 13.5 * size.scale

    svg.advance(size.pad * 0.8)
    bar_top = svg.y
    svg.advance(font * 1.15)

    lines = wrap(cfg["text"], font, inner, mono=True)
    for line in lines:
        svg.text(line, x=size.pad + 14, size=font, fill=theme["muted"], mono=True)
        svg.advance(font * 1.6)

    svg.advance(-font * 1.6 + size.pad * 0.8)
    svg.rect(
        x=size.pad,
        y=bar_top,
        w=3,
        h=font * 1.6 * len(lines) - font * 0.5,
        fill=theme["accent"],
        radius=1.5,
    )
    write("status", size, svg.render(svg.y))


def build_section_header(
    name: str, heading: str, theme: dict[str, str], size: Size
) -> None:
    svg = Svg(size.width, theme)
    font = 12 * size.scale

    svg.advance(size.pad * 0.62 + font)
    svg.text(
        heading.upper(),
        x=size.pad,
        size=font,
        fill=theme["accent"],
        weight="600",
        mono=True,
        letter_spacing=1.6,
    )
    svg.advance(size.pad * 0.62)
    write(name, size, svg.render(svg.y, radius=6))


def build_card(
    name: str,
    item: dict[str, Any],
    theme: dict[str, str],
    size: Size,
    *,
    eyebrow_key: str,
    title_key: str,
) -> None:
    svg = Svg(size.width, theme)
    inner = size.width - size.pad * 2

    eyebrow_size = 10.5 * size.scale
    title_size = 19 * size.scale
    body_size = 13.5 * size.scale

    svg.advance(size.pad * 0.9 + eyebrow_size)
    svg.text(
        item[eyebrow_key],
        x=size.pad,
        size=eyebrow_size,
        fill=theme["accent"],
        weight="600",
        mono=True,
        letter_spacing=1.2,
    )

    svg.advance(title_size * 1.55)
    for line in wrap(item[title_key], title_size, inner):
        svg.text(line, x=size.pad, size=title_size, fill=theme["text"], weight="600")
        svg.advance(title_size * 1.32)
    svg.advance(-title_size * 1.32)

    body = item.get("body")
    if body:
        svg.advance(body_size * 2.05)
        for line in wrap(body, body_size, inner):
            svg.text(line, x=size.pad, size=body_size, fill=theme["muted"])
            svg.advance(body_size * 1.62)
        svg.advance(-body_size * 1.62)

    svg.advance(size.pad * 0.95)
    write(name, size, svg.render(svg.y))


def build_chip(
    name: str, label: str, theme: dict[str, str], size: Size, *, filled: bool = False
) -> None:
    font = 12.5 * size.scale
    pad_x = 15 * size.scale
    height = 34 * size.scale
    width = int(text_width(label, font, mono=True) + pad_x * 2)

    svg = Svg(width, theme)
    svg.rect(
        x=0.5,
        y=0.5,
        w=width - 1,
        h=height - 1,
        fill=theme["surface"] if filled else "none",
        stroke=theme["border"],
        radius=height / 2,
    )
    svg.y = height / 2 + font * 0.35
    svg.text(
        label,
        x=width / 2,
        size=font,
        fill=theme["text"] if filled else theme["muted"],
        mono=True,
        anchor="middle",
    )
    path = OUT_DIR / f"{name}-{size.name}.svg"
    path.write_text(
        XML_DECL
        + f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" '
        f'viewBox="0 0 {width} {height:.0f}" role="img">{"".join(svg.parts)}</svg>',
        encoding="utf-8",
    )


def build_cert(
    name: str, item: dict[str, Any], theme: dict[str, str], size: Size
) -> None:
    # The chip carries the short form so the row does not wrap three times. The
    # full detail lives in the accessible section instead.
    label = item.get("short") or item["label"]
    build_chip(name, label, theme, size, filled=item.get("status") == "DONE")


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #


def picture(name: str, alt: str, *, width: str | None = None) -> str:
    w = f' width="{width}"' if width else ""
    return (
        "<picture>"
        f'<source media="(max-width: 480px)" srcset="./assets/generated/{name}-mobile.svg">'
        f'<img src="./assets/generated/{name}-desktop.svg"{w} alt="{esc(alt)}">'
        "</picture>"
    )


def linked(url: str | None, inner: str) -> str:
    return f'<a href="{url}">{inner}</a>' if url else inner


def accessible_section(heading: str, items: Iterable[dict[str, Any]], key: str) -> str:
    lines = [f"## {heading}", ""]
    for item in items:
        title = item[key]
        title = f'[{title}]({item["url"]})' if item.get("url") else title
        lines.append(f"### {title}")
        note = item.get("eyebrow") or item.get("note")
        if note:
            lines.append(f"*{note}*")
        if item.get("body"):
            lines.extend(["", item["body"]])
        lines.append("")
    return "\n".join(lines)


def build_readme(cfg: dict[str, Any]) -> str:
    featured = cfg["featured"]
    current = cfg["current"]
    certs = cfg["certifications"]

    contacts = "".join(
        linked(c["url"], picture(f'contact-{c["id"]}', c["label"]))
        for c in cfg["contact"]
    )

    featured_cards = "\n".join(
        linked(item.get("url"), picture(f"featured-{i}", item["title"], width="100%"))
        for i, item in enumerate(featured["items"])
    )

    current_cards = "\n".join(
        linked(item.get("url"), picture(f"current-{i}", item["label"], width="100%"))
        for i, item in enumerate(current["items"])
    )

    cert_chips = "".join(
        picture(f"cert-{i}", f'{item["label"]} — {item["detail"]}')
        for i, item in enumerate(certs["items"])
    )

    accessible = "\n".join(
        [
            accessible_section(featured["heading"], featured["items"], "title"),
            accessible_section(current["heading"], current["items"], "label"),
            f'## {certs["heading"]}',
            "",
            *[
                f'- **{c["label"]}** — {c["detail"]}'
                for c in certs["items"]
            ],
        ]
    )

    return f"""<div align="center">
{picture("hero", f'{cfg["hero"]["name"]}. {cfg["hero"]["tagline"]}', width="100%")}
{picture("status", cfg["status"]["text"], width="100%")}
</div>

<br>

<p align="center">
{contacts}
</p>

{picture("featured-header", featured["heading"], width="100%")}

{featured_cards}

{picture("current-header", current["heading"], width="100%")}

{current_cards}

{picture("certifications-header", certs["heading"], width="100%")}

<p align="center">
{cert_chips}
</p>

<details>
<summary>Accessible text version</summary>

{accessible}

</details>

<!-- Generated from profile.yml. Edit profile.yml, then run python scripts/build_profile.py. -->
"""


def main() -> None:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    theme = cfg["theme"]

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    for size in SIZES:
        build_hero(cfg["hero"], theme, size)
        build_status(cfg["status"], theme, size)

        for contact in cfg["contact"]:
            build_chip(f'contact-{contact["id"]}', contact["label"], theme, size)

        build_section_header(
            "featured-header", cfg["featured"]["heading"], theme, size
        )
        for i, item in enumerate(cfg["featured"]["items"]):
            build_card(
                f"featured-{i}",
                item,
                theme,
                size,
                eyebrow_key="eyebrow",
                title_key="title",
            )

        build_section_header("current-header", cfg["current"]["heading"], theme, size)
        for i, item in enumerate(cfg["current"]["items"]):
            build_card(
                f"current-{i}",
                item,
                theme,
                size,
                eyebrow_key="note",
                title_key="label",
            )

        build_section_header(
            "certifications-header", cfg["certifications"]["heading"], theme, size
        )
        for i, item in enumerate(cfg["certifications"]["items"]):
            build_cert(f"cert-{i}", item, theme, size)

    README.write_text(build_readme(cfg), encoding="utf-8")

    count = len(list(OUT_DIR.glob("*.svg")))
    print(f"{count} SVGs written to {OUT_DIR.relative_to(ROOT)}")
    print(f"README.md rebuilt ({len(README.read_text(encoding='utf-8'))} bytes)")


if __name__ == "__main__":
    main()
