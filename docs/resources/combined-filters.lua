-- ============================================================================
-- Combined Pandoc Lua Filters for ACH Anthology
-- Combines functionality from: lightbox.lua, appendix.lua, latex-floats.lua
-- ============================================================================

-- ============================================================================
-- APPENDIX FILTER STATE
-- ============================================================================
local in_appendix = false
local appendix_counter = 0

-- ============================================================================
-- LATEX FLOATS (LISTINGS) FILTER STATE
-- ============================================================================
local ENV = "listing"
local listing_count = 0
local label_to_num = {}   -- label -> N (for all float types)
local label_to_id  = {}   -- label -> id string
local generated_ids = {}  -- to avoid collisions
local figure_count = 0
local table_count = 0
local section_counters = {0, 0, 0, 0, 0, 0}  -- Track section numbers at each level
local appendix_scan_counter = 0  -- Separate counter for scanning appendix headers in PASS 2
local current_appendix_letter = nil  -- Track current appendix letter during PASS 2

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

local function escape_html(s)
  s = s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;")
  return s
end

-- Convert minted blocks to HTML <pre><code class="language-...">...</code></pre>
local function minted_to_html(s)
  -- With options: \begin{minted}[...]{lang} ... \end{minted}
  s = s:gsub("\\begin{minted}(%b[])%s*{%s*(.-)%s*}%s*([%s%S]-)%s*\\end{minted}",
    function(_opts, lang, code)
      return string.format('<pre><code class="language-%s">%s</code></pre>', lang, escape_html(code))
    end
  )
  -- Without options: \begin{minted}{lang} ... \end{minted}
  s = s:gsub("\\begin{minted}%s*{%s*(.-)%s*}%s*([%s%S]-)%s*\\end{minted}",
    function(lang, code)
      return string.format('<pre><code class="language-%s">%s</code></pre>', lang, escape_html(code))
    end
  )
  return s
end

-- ============================================================================
-- PASS 1: RawBlock Processing (Appendix Detection + Listing Conversion)
-- ============================================================================

local function process_rawblock(el)
  if el.format ~= "latex" then return nil end

  -- APPENDIX: Detect \appendix command
  if el.text:match("\\appendix") then
    in_appendix = true
    io.stderr:write("DEBUG: Found \\appendix command, setting in_appendix = true\n")
    return {}  -- Remove the raw \appendix from output
  end

  -- LISTINGS: Handle \begin{listing}...\end{listing}
  local text = el.text
  local body = text:match("\\begin{" .. ENV .. "}%s*([%s%S]-)%s*\\end{" .. ENV .. "}")
  if not body then return nil end

  -- Find caption/label (optional)
  local caption_cmd = body:match("\\caption%s*%b{}")
  local caption = caption_cmd and caption_cmd:match("{(.*)}") or nil
  local label_cmd = body:match("\\label%s*%b{}")
  local label = label_cmd and label_cmd:match("{(.*)}") or nil

  -- Remove caption/label from body content
  if caption_cmd then body = body:gsub("\\caption%s*%b{}", "", 1) end
  if label_cmd   then body = body:gsub("\\label%s*%b{}", "", 1)   end

  -- Assign number
  listing_count = listing_count + 1
  local N = listing_count

  -- Ensure we have an id
  local id = label and label or ("listing-" .. N)
  -- Avoid duplicate ids
  if generated_ids[id] then
    local k = 2
    while generated_ids[id .. "-" .. k] do k = k + 1 end
    id = id .. "-" .. k
  end
  generated_ids[id] = true

  -- Save mappings for refs
  if label then
    label_to_num[label] = N
    label_to_id[label]  = id
  end

  -- Convert known inner environments (e.g., minted) to safe HTML
  body = minted_to_html(body)

  -- Build caption
  local figcaption
  if caption and caption ~= "" then
    figcaption = string.format("<figcaption>Listing %d: %s</figcaption>", N, caption)
  else
    figcaption = string.format("<figcaption>Listing %d</figcaption>", N)
  end

  -- Emit HTML figure
  local open = string.format('<figure class="float %s" id="%s">', ENV, id)
  local html = {
    pandoc.RawBlock("html", open),
    pandoc.RawBlock("html", '<div class="float-body ' .. ENV .. '">'),
    pandoc.RawBlock("html", body),
    pandoc.RawBlock("html", '</div>'),
    pandoc.RawBlock("html", figcaption),
    pandoc.RawBlock("html", '</figure>')
  }
  return html
end

-- ============================================================================
-- PASS 2: Scan Figures, Tables, and Headers (Build Label Map)
-- ============================================================================

local function scan_figures_and_tables(el)
  if el.t == "Figure" then
    figure_count = figure_count + 1
    if el.attr and el.attr.identifier and el.attr.identifier ~= "" then
      local id = el.attr.identifier
      label_to_num[id] = figure_count
      label_to_id[id] = id
    end
  elseif el.t == "Table" then
    -- Standalone table element
    if el.attr and el.attr.identifier and el.attr.identifier ~= "" then
      local id = el.attr.identifier
      table_count = table_count + 1
      label_to_num[id] = table_count
      label_to_id[id] = id
    end
  elseif el.t == "Div" then
    -- Check if this Div contains a table
    local has_table = false
    for i, block in ipairs(el.content) do
      if block.t == "Table" then
        has_table = true
        break
      end
    end

    -- If the Div contains a table and has an identifier, treat it as a labeled table
    if has_table and el.attr and el.attr.identifier and el.attr.identifier ~= "" then
      local id = el.attr.identifier
      table_count = table_count + 1
      label_to_num[id] = table_count
      label_to_id[id] = id
    end
  elseif el.t == "Header" then
    -- Check if this is a truly unnumbered section (not appendix with letter numbering)
    -- Appendix sections have class="unnumbered" but also have data-number="A", "B", etc.
    local has_unnumbered_class = el.classes and el.classes:includes("unnumbered")
    local has_data_number = el.attributes and el.attributes["data-number"]
    local is_truly_unnumbered = has_unnumbered_class and not has_data_number

    if not is_truly_unnumbered then
      local level = el.level
      local sec_num

      -- Check if this header has a data-number attribute set by process_appendix_header in PASS 1
      -- Appendix sections will have data-number="A", "B", etc. (letters, not starting with digit)
      if has_data_number and not has_data_number:match("^%d") and level == 1 then
        -- This is an appendix section with letter numbering already set in PASS 1
        sec_num = has_data_number
        -- Update the current appendix letter for subsections
        current_appendix_letter = has_data_number
        -- Reset section counters for subsections
        for i = 1, 6 do
          section_counters[i] = 0
        end
      elseif current_appendix_letter then
        -- This is a subsection/subsubsection within an appendix, OR a level-1 appendix
        if level == 1 then
          -- This is another level-1 appendix header (should have data-number, but handle gracefully)
          -- This case should not normally occur if PASS 1 worked correctly
          sec_num = current_appendix_letter
        else
          -- This is a subsection/subsubsection within an appendix
          -- Increment counter at this level
          section_counters[level] = section_counters[level] + 1

          -- Reset all deeper levels
          for i = level + 1, 6 do
            section_counters[i] = 0
          end

          -- Build section number string starting with the appendix letter
          -- (e.g., "A.1" or "A.2.3")
          local sec_parts = {current_appendix_letter}
          for i = 2, level do
            table.insert(sec_parts, tostring(section_counters[i]))
          end
          sec_num = table.concat(sec_parts, ".")
        end
      else
        -- Regular numeric section numbering
        -- Increment counter at this level
        section_counters[level] = section_counters[level] + 1

        -- Reset all deeper levels
        for i = level + 1, 6 do
          section_counters[i] = 0
        end

        -- Build section number string (e.g., "1" or "2.3" or "3.1.4")
        local sec_parts = {}
        for i = 1, level do
          table.insert(sec_parts, tostring(section_counters[i]))
        end
        sec_num = table.concat(sec_parts, ".")
      end

      -- Map label to section number
      if el.attr and el.attr.identifier and el.attr.identifier ~= "" then
        local id = el.attr.identifier
        label_to_num[id] = sec_num
        label_to_id[id] = id
      end
    end
    -- Note: truly unnumbered sections (from \section*{}) are not added to the label map
  end
  return nil
end

-- ============================================================================
-- PASS 3: Add section numbers to all headers
-- ============================================================================

local function add_section_numbers(el)
  -- Check if this is a truly unnumbered section (like "Acknowledgments")
  local has_unnumbered_class = el.classes and el.classes:includes("unnumbered")
  local has_data_number = el.attributes and el.attributes["data-number"]
  local is_truly_unnumbered = has_unnumbered_class and not has_data_number

  if not is_truly_unnumbered and el.attr and el.attr.identifier and el.attr.identifier ~= "" then
    local id = el.attr.identifier
    local sec_num = label_to_num[id]

    if sec_num then
      -- Check if this header already has a section number span (from PASS 1 appendix processing)
      local already_has_number = false
      for i, v in ipairs(el.content) do
        if v.t == "Span" and v.classes and v.classes:includes("header-section-number") then
          already_has_number = true
          break
        end
      end

      -- Only add numbering if it doesn't already have it
      if not already_has_number then
        -- Add the data-number attribute
        if not el.attributes then
          el.attributes = {}
        end
        el.attributes['data-number'] = tostring(sec_num)

        -- Add the section number span to the header content
        local new_content = pandoc.List({
          pandoc.Span({pandoc.Str(tostring(sec_num))}, {class = "header-section-number"}),
          pandoc.Space()
        })
        for i, v in ipairs(el.content) do
          new_content:insert(v)
        end

        el.content = new_content
        return el
      end
    end
  end
  return nil
end

-- ============================================================================
-- PASS 4: Process Figures for Lightbox (HTML Only)
-- ============================================================================

local function add_lightbox_to_figure(fig)
  -- Only process in HTML format
  if not FORMAT:match('html') then return nil end

  -- Get the image from the figure
  if fig.content and #fig.content > 0 then
    local image = nil

    -- Find the Image element in the figure content
    for _, block in ipairs(fig.content) do
      if block.t == 'Plain' or block.t == 'Para' then
        for _, inline in ipairs(block.content) do
          if inline.t == 'Image' then
            image = inline
            break
          end
        end
      end
      if image then break end
    end

    if image then
      -- Get the image source
      local src = image.src

      -- Get the caption text
      local caption = ""
      if fig.caption and fig.caption.long then
        caption = pandoc.utils.stringify(fig.caption.long)
      end

      -- Create raw HTML for the lightbox link
      local link_open = string.format(
        '<a href="%s" data-lightbox="figures" data-title="%s">',
        src,
        caption:gsub('"', '&quot;')
      )
      local link_close = '</a>'

      -- Modify the image to be wrapped in the lightbox link
      local wrapped_image = {
        pandoc.RawInline('html', link_open),
        image,
        pandoc.RawInline('html', link_close)
      }

      -- Replace the image in the figure content with the wrapped version
      for i, block in ipairs(fig.content) do
        if block.t == 'Plain' or block.t == 'Para' then
          for j, inline in ipairs(block.content) do
            if inline.t == 'Image' then
              -- Replace the image with the wrapped version
              local new_content = {}
              for k = 1, j - 1 do
                table.insert(new_content, block.content[k])
              end
              for _, wrapped in ipairs(wrapped_image) do
                table.insert(new_content, wrapped)
              end
              for k = j + 1, #block.content do
                table.insert(new_content, block.content[k])
              end
              block.content = new_content
              break
            end
          end
        end
      end
    end
  end

  return fig
end

-- ============================================================================
-- PASS 5: Add Table Numbers to Captions
-- ============================================================================

local function add_table_numbers(el)
  -- Process Divs that contain tables and have a table number assigned
  if el.t == "Div" and el.attr and el.attr.identifier and el.attr.identifier ~= "" then
    local id = el.attr.identifier
    local table_num = label_to_num[id]

    if table_num then
      -- Find the Table element inside the Div
      for i, block in ipairs(el.content) do
        if block.t == "Table" then
          -- Prepend "Table N: " to the caption
          if block.caption and block.caption.long and #block.caption.long > 0 then
            -- Get the first block of the caption
            local first_block = block.caption.long[1]
            if first_block and first_block.content then
              -- Prepend "Table N: " to the inline content
              local prefix = {
                pandoc.Str("Table"),
                pandoc.Space(),
                pandoc.Str(tostring(table_num) .. ":"),
                pandoc.Space()
              }
              -- Insert prefix at the beginning of the first block's content
              for j = #prefix, 1, -1 do
                table.insert(first_block.content, 1, prefix[j])
              end
            end
          end
          -- Return the modified element
          return el
        end
      end
    end
  end
  return nil
end

-- ============================================================================
-- PASS 6: Replace References (RawInline)
-- ============================================================================

local function replace_refs_inline(el)
  if el.format ~= "latex" then return nil end
  local t = el.text

  -- Strip \textzh{...} and just keep the content
  -- This allows CJK characters to pass through to HTML without the LaTeX macro
  t = t:gsub("\\textzh%s*{([^}]*)}", "%1")

  -- \autoref{label} -> "Figure N" or "Table N" or "Section N" linked to #id
  t = t:gsub("\\autoref%s*%b{}", function(braces)
    local label = braces:match("{(.*)}")
    if label and label_to_num[label] and label_to_id[label] then
      local N = label_to_num[label]
      local id = label_to_id[label]

      -- Determine the type based on the label prefix
      local ref_type = "Listing"  -- default
      if label:match("^fig:") then
        ref_type = "Figure"
      elseif label:match("^tab:") then
        ref_type = "Table"
      elseif label:match("^sec:") or label:match("^appdx:") or type(N) == "string" then
        -- Section references (including appendix sections)
        ref_type = "Section"
      end

      return string.format('<a href="#%s">%s %s</a>', id, ref_type, tostring(N))
    else
      return braces  -- leave unknown autorefs unchanged
    end
  end)

  -- \ref{label} -> number "N" linked to #id
  t = t:gsub("\\ref%s*%b{}", function(braces)
    local label = braces:match("{(.*)}")
    if label and label_to_num[label] and label_to_id[label] then
      local N = label_to_num[label]
      local id = label_to_id[label]
      return string.format('<a href="#%s">%s</a>', id, tostring(N))
    else
      return braces  -- leave unknown refs unchanged
    end
  end)

  if t ~= el.text then
    return pandoc.RawInline("html", t)
  end
  return nil
end

-- ============================================================================
-- PASS 7: Fill Link References
-- ============================================================================

local function fill_link_refs(el)
  if el.target and el.target:match("^#") then
    local label = el.target:sub(2)  -- remove the leading '#'

    if label_to_num[label] and label_to_id[label] then
      local N = label_to_num[label]
      -- Only fill in if the link text is empty
      if #el.content == 0 then
        return pandoc.Link(pandoc.Str(tostring(N)), el.target, el.title, el.attr)
      end
    end
  end
  return nil
end

-- ============================================================================
-- PASS 8: Process Headers for Appendix (handled in PASS 1)
-- ============================================================================

local function process_appendix_header(el)
  if in_appendix and el.level == 1 then
    appendix_counter = appendix_counter + 1
    local letter = string.char(64 + appendix_counter)  -- 65 = 'A'
    io.stderr:write("DEBUG: Processing header as appendix " .. letter .. " (in_appendix=" .. tostring(in_appendix) .. ")\n")

    -- Store the original identifier if it exists
    local original_id = el.identifier

    -- DO NOT change the identifier - keep it as-is so \ref{} commands can find it
    -- We'll just set the data-number attribute for display

    -- Set the data-number attribute to the letter
    if not el.attributes then
      el.attributes = {}
    end
    el.attributes['data-number'] = letter

    -- Add "unnumbered" class to prevent Pandoc from numbering this section
    if not el.classes:includes("unnumbered") then
      el.classes:insert("unnumbered")
    end

    -- Add the letter numbering to the content
    local letter_span = pandoc.Span(
      {pandoc.Str(letter)},
      {class = "header-section-number"}
    )
    local new_content = pandoc.List({letter_span, pandoc.Space()})
    for i, v in ipairs(el.content) do
      new_content:insert(v)
    end
    el.content = new_content
  end

  return el
end

-- ============================================================================
-- ORCHESTRATION: Multi-Pass Document Processing
-- ============================================================================

local function walk_doc_with_block(doc, handlers)
  local div = pandoc.Div(doc.blocks)
  local new_div = pandoc.walk_block(div, handlers, FORMAT, doc.meta)
  doc.blocks = new_div.content
  return doc
end

function Pandoc(doc)
  -- Reset state for this document
  in_appendix = false
  appendix_counter = 0
  appendix_scan_counter = 0
  listing_count = 0
  label_to_num = {}
  label_to_id = {}
  generated_ids = {}
  figure_count = 0
  table_count = 0
  section_counters = {0, 0, 0, 0, 0, 0}
  current_appendix_letter = nil

  -- PASS 1: RawBlock processing (appendix detection + listing conversion)
  --         AND Header processing for appendix numbering
  --         These must be in the same pass to maintain document order!
  doc = walk_doc_with_block(doc, {
    RawBlock = process_rawblock,
    Header = process_appendix_header
  })

  -- PASS 2: Scan for figures, tables, and headers to build label map
  doc = walk_doc_with_block(doc, { Block = scan_figures_and_tables })

  -- PASS 3: Add section numbers to all headers
  doc = walk_doc_with_block(doc, { Header = add_section_numbers })

  -- PASS 4: Add lightbox to figures (HTML only)
  doc = walk_doc_with_block(doc, { Figure = add_lightbox_to_figure })

  -- PASS 5: Add table numbers to captions
  doc = walk_doc_with_block(doc, { Block = add_table_numbers })

  -- PASS 6: Replace refs in raw inline LaTeX
  doc = walk_doc_with_block(doc, { RawInline = replace_refs_inline })

  -- PASS 7: Fill in Link elements for refs
  doc = walk_doc_with_block(doc, { Link = fill_link_refs })

  return doc
end
