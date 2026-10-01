"""Curated presentation palette selection and non-destructive token resolution.

New documents: explicit choice > stored choice > topic match > neutral.
Existing literal colors are preserved. Only @role tokens are resolved for PPTX.
"""
from pathlib import Path
import copy
import json
import re

CATALOG = Path(__file__).resolve().parents[1] / 'assets' / 'presentation-palettes.json'

def catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))

def choose_palette(topic='', explicit=None, stored=None):
    presets = catalog()
    selected = explicit if explicit and explicit != 'auto' else stored
    if selected and selected != 'auto':
        return selected, 'explicit' if explicit and explicit != 'auto' else 'saved'
    topic = str(topic).casefold()
    ranked = []
    for name, preset in presets.items():
        hits = 0
        for keyword in preset['keywords']:
            word = keyword.casefold()
            found = bool(re.search(r'(?<![a-z0-9])' + re.escape(word) + r'(?![a-z0-9])', topic)) if word.isascii() else word in topic
            hits += int(found)
        ranked.append((hits, name))
    best = max(ranked, key=lambda item: item[0])
    return (best[1], 'topic') if best[0] else ('neutral', 'fallback')

def colors_for(name):
    presets = catalog()
    if name in presets:
        return presets[name]['colors']
    # Existing HTML palette names remain valid when reused by PPTX preferences.
    css = (CATALOG.parent / 'css' / 'palettes.css').read_text(encoding='utf-8')
    block = re.search(r'html\[data-palette="' + re.escape(name) + r'"\]\s*\{([^}]+)\}', css)
    if not block:
        raise ValueError('Unknown palette: ' + str(name))
    tokens = dict(re.findall(r'--([a-z-]+):\s*#([a-fA-F0-9]{6})', block.group(1)))
    return {role:tokens[token] for role,token in {'ink':'ink','muted':'muted','paper':'surface-2','line':'line','accent':'accent','secondary':'ink-2','accentSoft':'accent-soft','white':'surface','onAccent':'on-accent'}.items()}

def apply_scene_palette(scene, topic=None, explicit=None, stored=None):
    result = copy.deepcopy(scene)
    # A palette embedded in an existing scene is an authored choice.
    chosen, reason = choose_palette(topic or scene.get('topic') or scene.get('title',''), explicit or scene.get('palette'), stored)
    colors = colors_for(chosen)
    def resolve(value):
        if isinstance(value, str) and value.startswith('@'):
            role, separator, strength = value[1:].partition('/')
            if role not in colors:
                raise ValueError('Unknown color role: ' + role)
            color = colors[role]
            if separator:
                if not strength.isdigit() or not 0 <= int(strength) <= 100:
                    raise ValueError('Color tint must be 0..100: ' + value)
                ratio = int(strength) / 100
                color = ''.join(f'{round(int(color[i:i+2],16)*ratio + 255*(1-ratio)):02X}' for i in (0,2,4))
            return color
        return value
    for slide in result.get('slides', []):
        for element in slide.get('elements', []):
            for key in ('color','fill','lineColor','headerFill','headerColor'):
                if key in element: element[key] = resolve(element[key])
            for series in element.get('series', []):
                if 'color' in series: series['color'] = resolve(series['color'])
                if 'colors' in series: series['colors'] = [resolve(v) for v in series['colors']]
    result['palette'] = chosen
    return result, chosen, reason
