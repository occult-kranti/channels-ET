function Image(image)
  image.src = image.src:gsub('%.png$', '.pdf')
  return image
end
function Header(header)
  if header.level == 1 and (header.identifier == 'references' or header.identifier:match('^appendix')) then
    return {pandoc.RawBlock('latex', '\\clearpage'), header}
  elseif header.level <= 2 then
    return {pandoc.RawBlock('latex', '\\FloatBarrier'), header}
  end
  return header
end
function Table(tbl)
  local n = #tbl.colspecs
  local h = ''
  if tbl.head.rows[1] then
    for _, cell in ipairs(tbl.head.rows[1].cells) do h = h .. ' ' .. pandoc.utils.stringify(cell.contents) end
  end
  local w = nil
  if n == 3 and h:match('Reference') then w = {.25,.36,.39}
  elseif n == 3 then w = {.60,.16,.24}
  elseif n == 4 and h:match('Direct%-attribution') then w = {.18,.52,.14,.16}
  elseif n == 4 and h:match('Publisher') then w = {.43,.16,.18,.23}
  elseif n == 4 then w = {.40,.18,.18,.24}
  elseif n == 5 then w = {.40,.15,.15,.15,.15} end
  if w then for i=1,n do tbl.colspecs[i][2]=w[i] end end
  return tbl
end
