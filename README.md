# Die Pfeile von Fornost

A one-shot adventure (German) for *The One Ring, 2nd Edition*, for about four hours and four heroes: three Hobbits
and one companion (Dwarf, Man or Elf) who is also their bodyguard.

**The pitch.** The Prologue of the Red Book says that Hobbit archers from the Shire helped the king at the battle
of Fornost (TA 1975). Men and Elves do not know of it, or deny it. In autumn TA 2951 the old Took Mirabella wants
proof that Hobbits are more than pipe-smokers and farmers. The Company searches the fields west of Fornost for
traces that survived a thousand years: iron, bronze, stone and earthworks. They find ten possible clues, enough
to conclude that the Hobbits were there, that they mattered and that their part was kept quiet on purpose, but
nobody ever confirms it.

- Warm and curious, with one dangerous place (a barrow-wight) that has nothing to do with the clues.
- A sandbox: five locations in any order, ten clues (A–J) of which the Loremaster picks the ones to use.
- *Skill Points* for the journey and for the 1st, 3rd and 6th clue found (1, 2 and 3 points). No *Fellowship Phase*.
- Written for experienced Loremasters: no stat blocks, the *Core Rules* provide them.

The text is in [src/adventure.md](src/adventure.md) (German). The PDF is built by GitHub Actions on every commit;
tagged commits (`v*`) are published as a release.

## Contents of the repository

| Path | Content |
| --- | --- |
| `adventure.toml` | Title, language, credit |
| `src/adventure.md` | The adventure text (Pandoc Markdown) |
| `src/maps.toml` | Maps in the appendix: the region around Fornost and the waystation |
| `src/cards.toml` | Item cards (none in this adventure) |
| `assets/maps/` | Loremaster and player versions of the maps |
| `tools/maps.py` | Map drawing code (`python3 tools/maps.py fornost wegwacht`) |
| `tools/build.py` | PDF build |
| `latex/`, `filters/tor2e.lua` | Layout and Pandoc filter |

## Build

Needs `pandoc`, TeX Live or MiKTeX with LuaLaTeX and `latexmk`, Python 3.11+ and Pillow.

```sh
make            # both editions: build/<file_name>.pdf and …-Book.pdf
make sheet      # loose punched sheets with a notes column
make book       # book block for binding
make maps       # redraw the maps
```

The version in the footer comes from the latest git tag `v*`, the date from the last commit:

```sh
git tag v0.1
git push --tags      # the CI also publishes a release with both PDFs
```

## Origin

The adventure is a spin on an adventure by Will at the World's End and is built on a Markdown-to-PDF template
for TOR 2e one-shots. The Prologue quote and the setting are Tolkien's. All names, places and clues beyond that
are invented.

## Licence

MIT, see [LICENSE](LICENSE).
