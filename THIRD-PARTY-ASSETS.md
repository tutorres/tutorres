# Third-party assets

The code and generated layout in this repository are the author's. Third-party
logos and trademarks are **not** covered by that and remain subject to the rights
of their owners. They appear here as nominative use: to identify the employer,
the university and the project each card is about.

| Asset | Owner | Source | Local file | Modifications |
|---|---|---|---|---|
| Banco Inter wordmark | Banco Inter S.A. | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Logo_do_banco_Inter_(2023).svg), marked public domain | `assets/brands/inter.png` | Rasterized from SVG at 360px wide. No recolouring: the brand orange `#EA7100` reads on both GitHub themes, so there is no dark twin |
| CEFET-MG identity | CEFET-MG | [CEFET-MG visual identity](https://www.secom.cefetmg.br/identidade-visual-do-cefet-mg/), via the light/dark pair prepared in [santana-iago/santana-iago](https://github.com/santana-iago/santana-iago) (MIT for its code) | `assets/brands/cefetmg.png`, `assets/brands/cefetmg-dark.png` | Raster payload extracted from the SVG wrapper it shipped in; proportions preserved |
| Torres tower mark | Arthur Torres (own work) | `public/icon.svg` in `tutorres/torres.dev` | `assets/brands/torres.png`, `assets/brands/torres-dark.png` | Rasterized at 180px wide. The source is solid `#000000` and disappears on a dark background, so the dark twin is the same artwork with the fill swapped to `#FEFEFE` |

Last reviewed: 2026-08-20.

## Why the brand files are PNG and not SVG

Every mark is embedded into the generated SVG as a base64 `data:` URI. A vector
SVG nested that way (a data-URI SVG inside a data-URI SVG inside the README's
`<img>`) is not reliably rendered or themed by browsers. The reference
implementation this layout borrows from documents the same finding: its contact
icons vanished in light mode until they were rasterized.

So the artwork is rasterized **once, out of band**, and the PNG is committed.
The consequence worth keeping: `scripts/build_profile.py` needs no rasterizer,
and the build dependency list stays at PyYAML alone.

## Theme adaptation

Where a mark needs different artwork per theme, a `-dark` twin sits beside it and
the generator embeds both, wrapped in `.theme-light-only` and `.theme-dark-only`.
The same `prefers-color-scheme` media query that swaps the text palette picks
one. A mark whose colour already works on both themes ships as a single file and
is embedded once.

## Marks deliberately absent

- **Vale.** The Programa Desenvolver work was an open challenge, not employment,
  and the mark is theirs. The card says so in words instead.
- **EF SET, Thoth / CSSC, Anthropic.** No asset on hand for three of the four
  certifications. One badge with real artwork beside three without would read
  worse than four consistent ones, so all four keep the drawn monogram.
