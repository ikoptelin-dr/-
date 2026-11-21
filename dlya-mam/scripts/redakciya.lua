-- Блоки ::: {custom-style="Редакция"} — текст серым (символьный стиль «РедакцияТекст»), включая списки и заголовки.
function Div(el)
  if el.attributes['custom-style'] == 'Редакция' then
    el.attributes['custom-style'] = nil
    return pandoc.walk_block(el, {
      Inlines = function(ils)
        return { pandoc.Span(ils, {['custom-style'] = 'РедакцияТекст'}) }
      end
    })
  end
end
