--[[
Pandoc filter for the adventure: Markdown -> LaTeX building blocks from latex/tor2e.sty.

  * Kapitel (## im Markdown):   \fwchapter{notes|nonotes}{id}{Titel}{Lesezeichen}
  * Kästen (Absätze, die mit einem fetten Label beginnen): fwbox-Umgebung
  * Hausregel-Kasten: Absatz „Gabe der Wacht (Hausregel …)“ + Liste + Absatz
  * „Optional“: graue Pille \fwskip
  * Tabellen: longtable mit festen Spaltenbreiten je Tabellentyp
  * Karten (Bilder mit Klasse .map): \fwmap
  * Brief (::: letter): fwletter-Umgebung; der Text geht zusätzlich als Handout
    nach $FW_BUILD/letter.tex
--]]

local BOX_LABELS = {
  "Hinweis für den Loremaster", "Optionale Erweiterung", "Erinnerung für den Loremaster",
  "Möglicher Abschluss", "Wenn sie trotzdem gehen", "Erfahrung",
  "Note for the Loremaster", "Extension (optional)", "Reminder for the Loremaster",
  "Possible ending", "If they refuse", "Experience",
}
-- Kästen, die über einen Seitenumbruch laufen dürfen
local SPLIT_LABELS = { "Brór auf der Rampe" }

-- Spaltenbreiten (Anteile der Zeilenbreite) und Schriftgröße je Tabellentyp,
-- erkannt am ersten Spaltenkopf
local TABLES = {
  ["Jahr (TA)"] = { widths = { 0.15, 0.62, 0.23 }, size = "normal" },
  ["Tag"]       = { widths = { 0.08, 0.17, 0.18, 0.57 }, size = "normal" },
  ["Welle"]     = { widths = { 0.22, 0.20, 0.29, 0.29 }, size = "normal" },
  ["Vorbereitung"] = { widths = { 0.24, 0.22, 0.54 }, size = "small" },
  ["Angriff"]   = { widths = { 0.16, 0.17, 0.33, 0.34 }, size = "small" },
  ["Im Kampf"]  = { widths = { 0.24, 0.76 }, size = "small" },
  ["Name"]      = { widths = { 0.13, 0.17, 0.17, 0.24, 0.29 }, size = "small" },
  ["Volk"]      = { widths = { 0.16, 0.84 }, size = "small" },
  -- English edition
  ["Part"]      = { widths = { 0.27, 0.12, 0.10, 0.51 }, size = "normal" },
  ["When"]      = { widths = { 0.21, 0.59, 0.20 }, size = "small" },
  ["Trigger"]   = { widths = { 0.76, 0.24 }, size = "small" },
  ["Score"]     = { widths = { 0.08, 0.14, 0.78 }, size = "small" },
  ["Choice"]    = { widths = { 0.27, 0.24, 0.49 }, size = "small" },
  ["Round"]     = { widths = { 0.09, 0.27, 0.27, 0.37 }, size = "small" },
}

local stringify = pandoc.utils.stringify
local function raw(s) return pandoc.RawBlock("latex", s) end
local function rawi(s) return pandoc.RawInline("latex", s) end

local function to_latex_inlines(inlines)
  local s = pandoc.write(pandoc.Pandoc({ pandoc.Plain(inlines) }), "latex")
  return (s:gsub("%s+$", ""))
end
local function to_latex_blocks(blocks)
  local s = pandoc.write(pandoc.Pandoc(blocks), "latex")
  return (s:gsub("%s+$", ""))
end

local function starts_with(s, prefix) return s:sub(1, #prefix) == prefix end

------------------------------------------------------------------------
-- Pass 1: Inline-Elemente
------------------------------------------------------------------------
local inline_pass = {
  Str = function(s)
    local word, punct = s.text:match("^(Skippable)(%p*)$")
    if not word then word, punct = s.text:match("^(Optional)(%p*)$") end
    if word then
      local pill = rawi("\\fwskip{" .. word .. "}")
      if punct == "" then return pill end
      return { pill, pandoc.Str(punct) }
    end
  end,
  Span = function(sp)
    if sp.classes:includes("sig") then
      return rawi("\\fwsig{" .. to_latex_inlines(sp.content) .. "}")
    end
  end,
}

------------------------------------------------------------------------
-- Pass 2: Blöcke
------------------------------------------------------------------------
local function table_to_latex(tbl)
  local st = pandoc.utils.to_simple_table(tbl)
  local first = stringify(st.headers[1] or {})
  local spec = TABLES[first]
  if not spec then
    io.stderr:write("tor2e.lua: unknown table type '" .. first .. "', default widths\n")
    local n = #st.headers
    local w = {}
    for i = 1, n do w[i] = 1 / n end
    spec = { widths = w, size = "normal" }
  end
  local cols = {}
  for i, w in ipairs(spec.widths) do
    cols[#cols + 1] = string.format(i == 1 and "B{%.3f}" or "P{%.3f}", w)
  end
  local out = { "\\begin{fwtable}{" .. spec.size .. "}",
                "\\begin{longtable}{@{}" .. table.concat(cols) .. "@{}}" }
  local head = {}
  for _, cell in ipairs(st.headers) do head[#head + 1] = "\\fwth{" .. to_latex_blocks(cell) .. "}" end
  out[#out + 1] = "\\rowcolor{fwthead}" .. table.concat(head, " & ") .. " \\\\ \\fwheadrule"
  out[#out + 1] = "\\endhead"
  for _, row in ipairs(st.rows) do
    local cells = {}
    for _, cell in ipairs(row) do cells[#cells + 1] = to_latex_blocks(cell) end
    out[#out + 1] = table.concat(cells, " & ") .. " \\\\ \\fwrowrule"
  end
  out[#out + 1] = "\\end{longtable}"
  out[#out + 1] = "\\end{fwtable}"
  return raw(table.concat(out, "\n"))
end

local letters = {}
local function letter_handout(div)
  -- Zeilen des Briefs (ohne Unterschrift) für die Handout-Seite sammeln
  local lines, cur, sig = {}, {}, ""
  local para = div.content[1]
  for _, el in ipairs(para.content) do
    if el.t == "LineBreak" then
      lines[#lines + 1] = cur; cur = {}
    elseif el.t == "RawInline" and el.text:match("^\\fwsig") then
      sig = el.text:match("^\\fwsig{(.*)}$") or ""
    else
      cur[#cur + 1] = el
    end
  end
  if #cur > 0 then lines[#lines + 1] = cur end
  local tex = {}
  for i, l in ipairs(lines) do
    local s = to_latex_inlines(l):gsub("^%s+", ""):gsub("%s+$", "")
    if s ~= "" then
      -- Leerzeile nach der Anrede und vor dem Schlusssatz, wie auf einem Brief
      local sep = ""
      if i > 1 then sep = (i == 2 or i == #lines) and "\\\\[0.9em]\n" or "\\\\\n" end
      tex[#tex + 1] = sep .. s
    end
  end
  local id = div.identifier ~= "" and div.identifier or "letter"
  local title = div.attributes["title"] or ("Handout: " .. id)
  letters[#letters + 1] = { id = id, title = title, text = table.concat(tex), sig = sig }
end

local chapter_count = 0
local block_pass = {
  Header = function(h)
    -- Ebenen hier selbst verschieben (## -> Kapitel, ### -> \subsection): pandocs
    -- --shift-heading-level-by greift erst nach den Filtern
    if h.level > 2 then
      h.level = h.level - 1
      return h
    end
    if h.level == 2 then
      local mode = h.classes:includes("nonotes") and "nonotes" or "notes"
      local out = {}
      chapter_count = chapter_count + 1
      -- the contents list closes the first page: it goes in front of the second chapter
      if chapter_count == 2 then out[#out + 1] = raw("\\fwindex") end
      out[#out + 1] = raw(string.format("\\fwchapter{%s}{%s}{%s}{%s}", mode, h.identifier,
        to_latex_inlines(h.content), stringify(h.content)))
      return out
    end
  end,

  Table = table_to_latex,

  Figure = function(fig)
    if not fig.classes:includes("map") then
      -- Klasse sitzt bei pandoc 3 am Bild selbst
      local img = nil
      pandoc.walk_block(fig, { Image = function(i) img = i end })
      if not (img and img.classes:includes("map")) then return nil end
    end
    local src
    pandoc.walk_block(fig, { Image = function(i) src = i.src end })
    local cap = to_latex_blocks(fig.caption.long)
    return raw("\\fwmap{" .. src .. "}{" .. cap .. "}")
  end,

  Div = function(div)
    if div.classes:includes("letter") then
      letter_handout(div)
      local out = { raw("\\begin{fwletter}") }
      for _, b in ipairs(div.content) do out[#out + 1] = b end
      out[#out + 1] = raw("\\end{fwletter}")
      return out
    end
  end,

  Blocks = function(blocks)
    local out = pandoc.Blocks({})
    local i = 1
    while i <= #blocks do
      local b = blocks[i]
      local handled = false
      if b.t == "Para" and b.content[1] and b.content[1].t == "Strong" then
        local label = stringify(b.content[1])
        if (starts_with(label, "Gabe der Wacht (Hausregel") or starts_with(label, "Gift of the Star (house rule)"))
            and blocks[i + 1] and blocks[i + 1].t == "BulletList"
            and blocks[i + 2] and blocks[i + 2].t == "Para" then
          out:insert(raw("\\begin{fwbox}[fw rule]"))
          out:insert(b); out:insert(blocks[i + 1]); out:insert(blocks[i + 2])
          out:insert(raw("\\end{fwbox}"))
          i = i + 3
          handled = true
        else
          for _, l in ipairs(BOX_LABELS) do
            if starts_with(label, l) then
              local opt = ""
              for _, s in ipairs(SPLIT_LABELS) do
                if label:find(s, 1, true) then opt = "[fw split]" end
              end
              out:insert(raw("\\begin{fwbox}" .. opt))
              out:insert(b)
              out:insert(raw("\\end{fwbox}"))
              i = i + 1
              handled = true
              break
            end
          end
        end
      end
      if not handled then
        out:insert(b)
        i = i + 1
      end
    end
    return out
  end,
}

-- Handout-Texte aller Briefe nach $FW_BUILD/letters.tex (\fwletter@<id>, \fwlettersig@<id>)
local write_pass = {
  Pandoc = function(doc)
    local dir = os.getenv("FW_BUILD") or "build"
    local f = assert(io.open(dir .. "/letters.tex", "w"))
    for _, l in ipairs(letters) do
      f:write("\\expandafter\\def\\csname fwletter@" .. l.id .. "\\endcsname{" .. l.text .. "}\n")
      f:write("\\expandafter\\def\\csname fwlettersig@" .. l.id .. "\\endcsname{" .. l.sig .. "}\n")
    end
    f:close()
    -- one handout page per letter, in text order
    local h = assert(io.open(dir .. "/handouts.tex", "w"))
    for _, l in ipairs(letters) do
      local t = l.title:gsub("[%%#&_]", function(c) return string.char(92) .. c end)
      h:write(string.char(92) .. "fwhandoutletter{h-" .. l.id .. "}{" .. t .. "}{" .. l.id .. "}" .. string.char(10))
    end
    h:close()
  end,
}

return { inline_pass, block_pass, write_pass }
