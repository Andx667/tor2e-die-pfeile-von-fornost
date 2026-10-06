# TOR 2e Adventure Template

A starting point for a one-shot adventure for *The One Ring, 2nd Edition*: Markdown text in, a print-ready
PDF out (loose punched sheets with a notes column, and a book edition for binding), with item cards,
Loremaster and player maps, and handouts. GitHub Actions builds the PDFs on every commit.

## Start a new adventure

1. Use this repository as a template (**Use this template** on GitHub), or copy the folder and run `git init`.
2. Edit [adventure.toml](adventure.toml): title, subtitle, author, language (`english` or `german`), file name.
3. Write the adventure in [src/adventure.md](src/adventure.md). It is a skeleton that shows every markup feature.
4. Fill in [src/cards.toml](src/cards.toml) (or empty `order` for no cards) and [src/maps.toml](src/maps.toml).
5. `python3 tools/build.py` and look at `build/*.pdf`.

## Layout of the repository

| Path | Content |
| --- | --- |
| `adventure.toml` | Title, language, credit: everything that is not text |
| `src/adventure.md` | The adventure text (Pandoc Markdown), where you write |
| `src/cards.toml` | Item cards (values, text, order) |
| `src/maps.toml` | Which maps the appendix contains |
| `assets/` | Logo (`tools/logo.py`), social preview (`tools/social.py`), maps in `assets/maps/` |
| `latex/tor2e.sty` | The layout: margins, notes column, boxes, tables, cards, handouts |
| `latex/tor2e.tex`, `latex/tor2e-buch.tex` | Skeletons of the sheet and book editions |
| `latex/inhalt.tex` | The shared content order of both editions (body, cards, maps, handouts) |
| `filters/tor2e.lua` | Pandoc filter: Markdown elements into layout blocks |
| `tools/build.py` | Builds the PDFs |
| `tools/maps.py` | Map drawing engine (parchment, hatched walls, markers) with a sample map |
| `.github/workflows/build.yml` | CI: builds on every commit, release on tag `v*` |

## Writing rules for the Markdown

- `## Chapter {#id}` starts a chapter on a new page with a notes column; `{#id .nonotes}` sets it in full width
  (use that for tables and appendices). The first chapter should have the id `overview`: the contents list is
  generated from all other chapters and closes the first page.
- `### Section` is a subheading. Numbered locations (`### 1. The Gate`) should match the numbers on the maps.
- A paragraph that starts with one of these bold labels becomes a box: **Note for the Loremaster:**,
  **Extension (optional) – Title:**, **Reminder for the Loremaster:**, **Possible ending:**, **If they refuse:**,
  **Experience:**. The German labels of the older adventures also work.
- The word `Skippable` at the end of an event becomes a grey pill (`Optional` too).
- A rules paragraph that starts with **Gift of the Star (house rule)** followed by a list and one more paragraph
  becomes a framed house-rule box. Rename or reuse the label in `filters/tor2e.lua`.
- Rules terms are in italics (`*Hope*`, `*Council*`), Tolkien names stay English.
- Maps in the text: `![Caption](assets/maps/file.jpg){.map}`.
- Letters and handouts: `::: {.letter #id title="Handout 1: The Letter"} … :::`. Every line ends with a
  backslash, and the signature is a `[Name]{.sig}` span. The text appears in the chapter and again as a
  full-page handout at the end of the PDF.
- Tables are normal pipe tables. The widths are chosen by the first column header (`TABLES` in the filter:
  `Part`, `When`, `Name`, `Trigger`, `Score`, `Choice`, `Round`, plus the German ones). Unknown headers get equal
  widths and a warning.

## Cards and maps

- **Cards** are six per A4 page, 63 × 88 mm, in the order of `order` in `src/cards.toml`. Terms listed in
  `terms` are set in italics automatically.
- **Maps** come as a pair per entry in `src/maps.toml`: `assets/maps/map-<id>.jpg` (Loremaster, numbered, with
  secrets in red) and `map-<id>-players.jpg` (layout only). Draw them with `tools/maps.py`: copy
  `map_example`, change the rooms and register the function in `MAPS`. `python3 tools/maps.py <id>` renders both
  versions. Any other image of the right name works too.

## Build

Needs `pandoc`, TeX Live or MiKTeX with LuaLaTeX and `latexmk`, Python 3.11+ and Pillow (for the tools).

```sh
make            # both editions: build/<file_name>.pdf and …-Book.pdf
make sheet      # loose punched sheets
make book       # book block for binding
make maps       # redraw the maps
```

The version in the footer comes from the latest git tag `v*`, the date from the last commit:

```sh
git tag v0.1
git push --tags      # the CI also publishes a release with both PDFs
```

## Language

`language = "german"` in `adventure.toml` switches hyphenation and the layout words (Notizen, Inhalt, Stand,
Anhang: Gegenstandskarten). The box labels and the skippable pill of both languages are always recognised.

## Licence

MIT, see [LICENSE](LICENSE). Change the name in the licence and in `adventure.toml`.
