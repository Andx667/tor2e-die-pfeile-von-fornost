#!/usr/bin/env python3
"""Builds the print edition of the adventure.

    python3 tools/build.py            # both editions
    python3 tools/build.py book       # only one: sheet | book

Everything adventure-specific lives in adventure.toml (title, language, credit), src/adventure.md
(the text), src/cards.toml (item cards) and src/maps.toml (maps). Steps:

  1. version and date from git (latest tag v*, commit date)  -> build/version.tex
  2. adventure.toml                                           -> build/meta.tex
  3. src/adventure.md -> build/body.tex (pandoc + filters/tor2e.lua), plus contents and handouts
  4. src/cards.toml   -> build/cards.tex
  5. src/maps.toml    -> build/maps-lm.tex, build/maps-players.tex
  6. LuaLaTeX (latexmk) -> build/<file_name>.pdf (sheet, punched) and build/<file_name>-Book.pdf (book)
  7. copy with the exact version in the name (published by CI)

Needs: pandoc, LuaLaTeX with latexmk (TeX Live or MiKTeX), Python 3.11+.
Without luaotfload XeLaTeX is used instead (FW_ENGINE=... forces an engine).
"""
import datetime
import os
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
SOURCE = os.path.join("src", "adventure.md")

STRINGS = {
    "english": {"Notes": "Notes", "Contents": "Contents", "Version": "Version", "Date": "Date",
                "Cards": "Item Cards", "CardsHeading": "Appendix: Item Cards", "Maps": "Maps and Handouts",
                "MapWord": "Map", "Handout": "Handout", "LmMaps": "Loremaster maps",
                "PlayerHandouts": "Player handouts", "LmVersion": "Loremaster version",
                "MapOf": "Map of"},
    "ngerman": {"Notes": "Notizen", "Contents": "Inhalt", "Version": "Version", "Date": "Stand",
                "Cards": "Gegenstandskarten", "CardsHeading": "Anhang: Gegenstandskarten",
                "Maps": "Karten und Handouts", "MapWord": "Karte", "Handout": "Handout",
                "LmMaps": "Karten für den Loremaster", "PlayerHandouts": "Handouts für die Spieler",
                "LmVersion": "Loremaster-Version", "MapOf": "Karte:"},
}


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, **kw)


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except FileNotFoundError:
        return ""


def tex_escape(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}")):
        s = s.replace(a, b)
    return s


def load_config():
    with open(os.path.join(ROOT, "adventure.toml"), "rb") as f:
        cfg = tomllib.load(f)
    cfg.setdefault("short_title", cfg["title"])
    cfg.setdefault("subtitle", "")
    cfg.setdefault("author", "")
    cfg.setdefault("license", "")
    cfg.setdefault("language", "english")
    cfg.setdefault("file_name", re.sub(r"[^A-Za-z0-9]+", "-", cfg["title"]).strip("-") + "-TOR2e")
    cfg["language"] = "ngerman" if cfg["language"].lower() in ("german", "ngerman", "de") else "english"
    return cfg


# ------------------------------------------------------------------ 1. version
def version():
    """The version in the PDF is the number of the latest tag: v2.1.1 -> "2.1.1".

    The third value is the exact version for the file name: "v2.1.1" on the tagged commit,
    three commits later "v2.1.1+3-abc1234".
    """
    desc = git("describe", "--tags", "--long", "--match", "v*")
    m = re.match(r"v(.+)-(\d+)-g([0-9a-f]+)$", desc)
    if m:
        ver = m[1]
        slug = "v" + (m[1] if m[2] == "0" else f"{m[1]}+{m[2]}-{m[3]}")
    else:
        commit = git("rev-parse", "--short", "HEAD")
        ver = "0.0"
        slug = "v0.0" + ("-" + commit if commit else "")
    if git("status", "--porcelain", "--untracked-files=no"):
        slug += "-local"
    stand = git("log", "-1", "--format=%cd", "--date=format:%d.%m.%Y") or datetime.date.today().strftime("%d.%m.%Y")
    return ver, stand, slug


# ------------------------------------------------------------------ 2. meta
def write_meta(cfg):
    s = STRINGS[cfg["language"]]
    by = ("by " if cfg["language"] == "english" else "von ") + cfg["author"] if cfg["author"] else ""
    credit = " – ".join(x for x in (by, cfg["license"]) if x)
    lines = [r"\def\advLang{%s}" % cfg["language"],
             r"\def\advTitle{%s}" % tex_escape(cfg["title"]),
             r"\def\advTitleShort{%s}" % tex_escape(cfg["short_title"]),
             r"\def\advSubtitle{%s}" % tex_escape(cfg["subtitle"]),
             r"\def\advAuthor{%s}" % tex_escape(cfg["author"]),
             r"\def\advCredit{%s}" % tex_escape(credit)]
    lines += [r"\def\advStr%s{%s}" % (k, tex_escape(v)) for k, v in s.items()]
    with open(os.path.join(BUILD, "meta.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ------------------------------------------------------------------ 3. contents
def clean_title(t):
    t = re.sub(r"\{[^}]*\}\s*$", "", t).strip()
    t = re.sub(r"[*_`]", "", t)
    return tex_escape(t)


def write_contents(cfg, has_cards, first_map):
    entries = []
    with open(os.path.join(ROOT, SOURCE), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^## (.+?)\s*\{#([\w-]+)[^}]*\}\s*$", line)
            if m and m[2] != "overview":
                entries.append((clean_title(m[1]), m[2]))
    s = STRINGS[cfg["language"]]
    if has_cards:
        entries.append((tex_escape(s["Cards"]), "cards"))
    if first_map:
        entries.append((tex_escape(s["Maps"]), "lm-" + first_map))
    half = (len(entries) + 1) // 2
    for name, part in (("left", entries[:half]), ("right", entries[half:])):
        with open(os.path.join(BUILD, f"index-{name}.tex"), "w", encoding="utf-8") as f:
            f.write("\n".join(r"\fwidx{%s}{%s}" % e for e in part) + "\n")


# ------------------------------------------------------------------ 4. cards
def cards_tex():
    with open(os.path.join(ROOT, "src", "cards.toml"), "rb") as f:
        data = tomllib.load(f)
    if not data.get("order"):
        return "", False
    terms = sorted(data.get("terms", []), key=len, reverse=True)
    term_re = re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in terms) + r")(?![\w])") if terms else None

    def it(s):
        s = tex_escape(s)
        return term_re.sub(lambda m: r"\textit{" + m[1] + "}", s) if term_re else s

    def card(key):
        c = data["cards"][key]
        up = [r"\fwcardname{" + tex_escape(c["name"]) + "}", r"\fwcardkind{" + it(c["kind"]) + "}"]
        if "stats" in c:
            up.append(r"\fwcardstats{" + it(c["stats"]) + "}{" + it(c.get("stats_note", "")) + "}")
        up.append(r"\fwcardtext{" + it(c["text"]) + "}")
        up.append(r"\begin{fwcardeffects}")
        up += [r"\item \textbf{" + tex_escape(a) + ":} " + it(b) for a, b in c.get("effects", [])]
        up.append(r"\end{fwcardeffects}")
        return r"\fwcard{" + "\n".join(up) + "}{" + tex_escape(data.get("footer", "")) + "}"

    # six cards per page; \fwcard breaks the rows itself (3 x 2 sheet, 2 x 3 book)
    order = data["order"]
    pages = [order[i:i + 6] for i in range(0, len(order), 6)]
    out = []
    for page in pages:
        out.append(r"\fwcardspage{" + tex_escape(data.get("hint", "")) + "}{%\n" + "\n".join(card(k) for k in page) + "}")
    return "\n\n".join(out) + "\n", True


# ------------------------------------------------------------------ 5. maps
def find_image(stem):
    for ext in (".jpg", ".png"):
        path = os.path.join("assets", "maps", stem + ext)
        if os.path.exists(os.path.join(ROOT, path)):
            return path.replace(os.sep, "/")
    return None


def write_maps(cfg):
    path = os.path.join(ROOT, "src", "maps.toml")
    maps = []
    if os.path.exists(path):
        with open(path, "rb") as f:
            maps = tomllib.load(f).get("maps", [])
    s = STRINGS[cfg["language"]]
    lm, pl = [], []
    first = None
    for m in maps:
        mid, title, sub = m["id"], m["title"], m.get("subtitle", "")
        img = find_image(f"map-{mid}")
        if not img:
            print(f"warning: assets/maps/map-{mid}.jpg|png not found, map skipped")
            continue
        first = first or mid
        group = "[%s]" % tex_escape(s["LmMaps"]) if len(lm) == 0 else ""
        lm.append(r"\fwlmmap%s{lm-%s}{%s: %s}{%s · %s}{%s}{%s: %s}" % (
            group, mid, tex_escape(s["MapWord"]), tex_escape(title), tex_escape(s["LmVersion"]),
            tex_escape(sub), img, tex_escape(s["MapWord"]), tex_escape(title)))
        pimg = find_image(f"map-{mid}-players")
        if pimg and m.get("players", True):
            group = "[%s]" % tex_escape(s["PlayerHandouts"]) if len(pl) == 0 else ""
            pl.append(r"\fwhandoutmap%s{h-%s}{%s}{%s: %s %s}" % (
                group, mid, pimg, tex_escape(s["Handout"]), tex_escape(s["MapOf"]), tex_escape(title)))
    with open(os.path.join(BUILD, "maps-lm.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lm) + "\n")
    with open(os.path.join(BUILD, "maps-players.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(pl) + "\n")
    return first


# ------------------------------------------------------------------ flow
EDITIONS = {"sheet": ("latex/tor2e.tex", ""), "book": ("latex/tor2e-buch.tex", "-Book")}


def main():
    editions = sys.argv[1:] or list(EDITIONS)
    for e in editions:
        if e not in EDITIONS:
            sys.exit(f"Unknown edition '{e}' - choose from: " + ", ".join(EDITIONS))
    cfg = load_config()
    os.makedirs(BUILD, exist_ok=True)
    ver, stand, slug = version()
    with open(os.path.join(BUILD, "version.tex"), "w", encoding="utf-8") as f:
        f.write("\\def\\fwversion{%s}\n\\def\\fwstand{%s}\n" % (tex_escape(ver), stand))
    print(f"{cfg['title']} - version {ver} - date {stand}")

    write_meta(cfg)
    env = dict(os.environ, FW_BUILD=BUILD)
    run(["pandoc", SOURCE, "-f", "markdown", "-t", "latex-smart", "--lua-filter", "filters/tor2e.lua",
         "-o", os.path.join(BUILD, "body.tex")], env=env)
    cards, has_cards = cards_tex()
    with open(os.path.join(BUILD, "cards.tex"), "w", encoding="utf-8") as f:
        f.write(cards)
    first_map = write_maps(cfg)
    write_contents(cfg, has_cards, first_map)

    env["TEXINPUTS"] = os.path.join(ROOT, "latex") + "//" + os.pathsep + env.get("TEXINPUTS", "")
    tex = ["-interaction=nonstopmode", "-halt-on-error", "-file-line-error"]
    engine = os.environ.get("FW_ENGINE") or (
        "lualatex" if subprocess.run(["kpsewhich", "luaotfload-main.lua"], capture_output=True, text=True).stdout.strip()
        else "xelatex")
    print("TeX engine:", engine)
    for e in editions:
        src, suffix = EDITIONS[e]
        job = cfg["file_name"] + suffix
        if shutil.which("latexmk"):
            run(["latexmk", "-" + engine, "-outdir=build", "-jobname=" + job, *tex, src], env=env)
        else:  # without latexmk three runs settle page references and bookmarks
            for _ in range(3):
                run([engine, *tex, "-output-directory=build", "-jobname=" + job, src], env=env)
        pdf = os.path.join("build", f"{job}-{slug}.pdf")
        shutil.copyfile(os.path.join(BUILD, job + ".pdf"), os.path.join(ROOT, pdf))
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"pdf_{e}=" + pdf.replace(os.sep, "/") + "\n")
        print("done:", pdf)


if __name__ == "__main__":
    sys.exit(main())
