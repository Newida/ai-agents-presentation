#!/usr/bin/env python3
"""Build visual comparisons using only Python's standard library and TeX/Poppler.

Each theme gets a contact sheet of every logical slide (last overlay).
compare.png/pdf shows the same title, field-report and takeaway pages in all themes.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'variants'
BUILD = OUT / '.build'
ORIGINAL_THEMES = ('neon', 'terminal', 'swiss', 'aurora', 'paper')
PAPER_THEMES = ('paper-warm', 'paper-journal', 'paper-stone', 'paper-sage', 'paper-ink')
THEMES = ORIGINAL_THEMES + PAPER_THEMES
LABELS = {
    'neon': '01  NEON  /  Cyan, violet, synthwave grid',
    'terminal': '02  TERMINAL  /  Editor chrome, prompts, status bars',
    'swiss': '03  SWISS  /  Signal red, bold type, clean grid',
    'aurora': '04  AURORA  /  Violet-to-coral gradients, soft cards',
    'paper': '05  PAPER  /  Warm ivory, serif type, terracotta',
    'paper-warm': '01  WARM  /  Ivory, Palatino, muted brown',
    'paper-journal': '02  JOURNAL  /  White, Times-style serif, fine rules',
    'paper-stone': '03  STONE  /  Grey, Charter headings, sans-serif body',
    'paper-sage': '04  SAGE  /  Soft green, bold serif headings, sans-serif body',
    'paper-ink': '05  INK  /  Dark graphite, warm serif type',
}


def frame_ends(name):
    nav = (BUILD / f'{name}.nav').read_text()
    ends = [int(b) for _, b in re.findall(r'\\beamer@framepages \{(\d+)\}\{(\d+)\}', nav)]
    if not ends:
        raise ValueError(f'No frame data for {name}; run variants/build.sh first')
    return ends


def render(rows, stem, columns, dpi):
    # 16:9 slides, 0.4 cm gutters, a fixed 1 cm label per row.
    width = columns * 16 + (columns - 1) * .4 + 1.2
    height = len(rows) * 10.5 + 1.2
    tex = [r'\documentclass{article}',
           r'\usepackage[paperwidth=%.2fcm,paperheight=%.2fcm,margin=0.6cm]{geometry}' % (width, height),
           r'\usepackage{graphicx,xcolor,tgheros}\renewcommand\familydefault{\sfdefault}',
           r'\pagestyle{empty}\pagecolor[HTML]{E1E3E7}\setlength\parindent{0pt}',
           r'\begin{document}\offinterlineskip']
    for label, slides in rows:
        tex.append(r'\vbox to 0.8cm{\vfil\hbox{\fontsize{16}{18}\selectfont\bfseries\color[HTML]{252B36}%s}\vfil}' % label)
        graphics = [r'\includegraphics[width=16cm,page=%d]{variants/%s.pdf}' % (page, name)
                    for name, page in slides]
        tex.append(r'\hbox{' + r'\hspace{0.4cm}'.join(graphics) + '}')
        tex.append(r'\vskip0.7cm')
    tex.append(r'\end{document}')
    path = BUILD / f'{stem}.tex'
    path.write_text('\n'.join(tex))
    result = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error',
                             f'-output-directory={BUILD}', str(path)], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout)
    (OUT / f'{stem}.pdf').write_bytes((BUILD / f'{stem}.pdf').read_bytes())
    subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-singlefile',
                    str(OUT / f'{stem}.pdf'), str(OUT / stem)], check=True, cwd=ROOT)
    print(f'OK variants/{stem}.png and .pdf', flush=True)


def main(names):
    if not names:
        names = list(ORIGINAL_THEMES)
    if any(n not in THEMES for n in names):
        raise ValueError('Unknown theme')
    for name in names:
        pages = frame_ends(name)
        rows = []
        for start in range(0, len(pages), 3):
            label = LABELS[name] if not start else name.upper() + ' / continued'
            rows.append((label, [(name, p) for p in pages[start:start + 3]]))
        render(rows, f'sheet-{name}', 3, 80)
    if len(names) > 1:
        rows = []
        for name in names:
            ends = frame_ends(name)
            rows.append((LABELS[name], [(name, ends[i]) for i in (0, 6, -1)]))
        stem = 'paper-compare' if all(n in PAPER_THEMES for n in names) else 'compare'
        render(rows, stem, 3, 80)


if __name__ == '__main__':
    main(sys.argv[1:])
