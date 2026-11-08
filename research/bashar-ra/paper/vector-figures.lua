-- The paired PDF and PNG figures have identical approved source-run provenance.
function Image(image)
  image.src = image.src:gsub('%.png$', '.pdf')
  return image
end

function Header(header)
  if (header.level == 1 and header.identifier == 'references') or header.identifier == 'official-excerpts-add-a-distinct-bounded-comparison' then
    return {pandoc.RawBlock('latex', '\\clearpage'), header}
  elseif header.level <= 2 then
    return {pandoc.RawBlock('latex', '\\FloatBarrier'), header}
  end
  return header
end

function Table(tbl)
  local count = #tbl.colspecs
  local headings = {}
  if tbl.head.rows[1] then
    for _, cell in ipairs(tbl.head.rows[1].cells) do
      table.insert(headings, pandoc.utils.stringify(cell.contents))
    end
  end
  local heading = table.concat(headings, ' ')
  local widths = nil
  if count == 5 then
    widths = {0.40, 0.10, 0.18, 0.14, 0.18}
  elseif count == 4 and (heading:match('Stratum') or heading:match('Supplementary stratum')) then
    widths = {0.31, 0.10, 0.14, 0.45}
  elseif count == 4 then
    widths = {0.16, 0.44, 0.20, 0.20}
  elseif count == 3 and heading:match('Planned work') then
    widths = {0.24, 0.48, 0.28}
  elseif count == 3 and heading:match('Corrected case') then
    widths = {0.16, 0.38, 0.46}
  elseif count == 3 then
    widths = {0.50, 0.25, 0.25}
  end
  if widths then
    for i = 1, count do tbl.colspecs[i][2] = widths[i] end
  end
  return tbl
end
