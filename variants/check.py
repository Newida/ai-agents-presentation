#!/usr/bin/env python3
"""Check the default/variant structure and important late-overlay content."""
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'variants'
BUILD = OUT / '.build'
THEMES = ('neon', 'terminal', 'swiss', 'aurora', 'paper',
          'paper-warm', 'paper-journal', 'paper-stone', 'paper-sage', 'paper-ink')


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def frame_ranges(path):
    return [tuple(map(int, pair)) for pair in re.findall(
        r'\\beamer@framepages \{(\d+)\}\{(\d+)\}', path.read_text())]


def normalized_text(pdf, page):
    s = command('pdftotext', '-f', str(page), '-l', str(page), str(pdf), '-')
    return re.sub(r'\s+', ' ', s).lower()


def main(names):
    names = names or THEMES
    if any(name not in THEMES for name in names):
        raise ValueError('Unknown theme')
    baseline = frame_ranges(BUILD / 'original.nav')
    assert len(baseline) == 14, baseline
    for name in names:
        # The only changes permitted in generated content are theme selection,
        # frame fitting and themed pros/cons symbols. Notes and overlays survive.
        source = (ROOT / 'main.tex').read_text()
        expected = source.replace(r'\begin{frame}', r'\begin{frame}[shrink=0]')
        expected = re.sub(r'(\\item(?:<[^>]*>)?)\[\+\]', r'\1[\\deckplus]', expected)
        expected = re.sub(r'(\\item(?:<[^>]*>)?)\[--\]', r'\1[\\deckminus]', expected)
        expected = r'\def\decktheme{' + name + '}\n' + expected
        assert (BUILD / f'{name}.tex').read_text() == expected, name
        path = OUT / f'{name}.pdf'
        log = (BUILD / f'{name}.log').read_text()
        assert not re.search(r'^!|^Overfull|Missing character|^LaTeX Font Warning|^Package .* Warning', log, re.M), name
        assert frame_ranges(BUILD / f'{name}.nav') == baseline, name
        info = command('pdfinfo', str(path))
        assert re.search(r'^Pages:\s+51$', info, re.M), name
        for index, phrases in {
            6: ('ask your agent', 'by hand', 'every two weeks'),
            9: ('dear management', 'spending their own money'),
            10: ('680', '145', 'rule of thumb'),
            11: ('still untested', '26/27'),
            12: ('rough comparison', '125 people'),
            13: ('for the individual', 'for the institute', 'bottlenecks', 'consider self-hosting'),
        }.items():
            text = normalized_text(path, baseline[index][1])
            assert all(phrase in text for phrase in phrases), (name, index, text)
        # Catch text outside the physical slide, even if TeX didn't warn.
        # Poppler reports text hidden by the vector chart's intentional crop too;
        # its zoom overlay is checked visually instead of treating hidden text as overflow.
        xml = command('pdftotext', '-bbox', str(path), '-')
        root = ET.fromstring(xml)
        for page_no, page in enumerate(root.findall('.//{*}page'), 1):
            if page_no == baseline[4][1]:
                continue
            width, height = float(page.attrib['width']), float(page.attrib['height'])
            for word in page.findall('.//{*}word'):
                x0, y0, x1, y1 = (float(word.attrib[a]) for a in ('xMin','yMin','xMax','yMax'))
                assert min(x0,y0) >= -1.5 and x1 <= width+1.5 and y1 <= height+1.5, (name, page_no, word.text, word.attrib)
        print(f'PASS {name}: 14 frames / 51 pages; content, overlays, text bounds and layout checked')
    source = (ROOT / 'main.tex').read_text()
    assert source.count('% TODO: Transition to david presentation: Voice to text, VScode, /goal, Claude orchestrating small local subagents') == 1


if __name__ == '__main__':
    main(sys.argv[1:])
