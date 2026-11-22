"""Разбор статьи на разделы (## ...) с признаком «серый/чёрный», FAQ-пунктами и хвостом."""
import re
def parse(path):
    t = open(path, encoding='utf-8').read()
    m = re.match(r'(---\n.*?\n---\n)', t, re.S); fm = m.group(1); body = t[m.end():]
    table = body[body.index('## Таблица утверждений'):]
    body = body[:body.index('## Таблица утверждений')]
    lines = body.split('\n'); grey = False; cur = None; secs = []; intro = []; title = ''
    for ln in lines:
        if ln.startswith('::: {custom-style'): grey = True; continue
        if ln.strip() == ':::': grey = False; continue
        if ln.startswith('# '): title = ln; continue
        if ln.startswith('## '):
            cur = {'h': ln[3:].strip(), 'lines': [], 'grey': grey}; secs.append(cur); continue
        if cur is None: intro.append((ln, grey))
        else:
            if cur['lines'] == [] and ln.strip() == '': continue
            cur['lines'].append((ln, grey))
    return dict(fm=fm, title=title, intro=intro, secs=secs, table=table)
def emit_lines(pairs):
    out = []; g = None; buf = []
    def flush():
        if not buf: return
        txt = '\n'.join(buf).strip('\n')
        if not txt.strip(): buf.clear(); return
        out.append(('::: {custom-style="Редакция"}\n' + txt + '\n:::') if g else txt); buf.clear()
    for ln, gr in pairs:
        if gr != g: flush(); g = gr
        buf.append(ln)
    flush(); return '\n\n'.join(out)
def faq_items(sec):
    items = []; q = None
    for ln, g in sec['lines']:
        m = re.match(r'^\*\*(.+?)\*\*\s*$', ln)
        if m: q = {'q': m.group(1), 'a': [], 'grey': g}; items.append(q)
        elif q is not None and ln.strip(): q['a'].append(ln)
    return items
