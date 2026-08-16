"""Inline SVG icons (Tabler Icons, MIT-licensed, self-hosted in
static/photos/icons/) — inlined at the call site rather than referenced via
a <use href="sprite.svg#name"> sprite, since cross-file <use> has a real
history of breaking on Safari/iOS and guests hit this app on whatever phone
they own.
"""

import functools
import re
from pathlib import Path

from django import template
from django.contrib.staticfiles import finders
from django.utils.safestring import mark_safe

register = template.Library()

_COMMENT_RE = re.compile(r"<!--.*?-->\s*", re.DOTALL)


@functools.lru_cache(maxsize=64)
def _load(name):
    path = finders.find(f"photos/icons/{name}.svg")
    if not path:
        raise template.TemplateSyntaxError(f"Unknown icon '{name}'")
    svg = Path(path).read_text(encoding="utf-8")
    return _COMMENT_RE.sub("", svg).strip()


@register.simple_tag
def icon(name, size=20, cls=""):
    svg = _load(name).replace('width="24"', f'width="{size}"').replace('height="24"', f'height="{size}"')
    if cls:
        svg = svg.replace("<svg", f'<svg class="{cls}"', 1)
    return mark_safe(svg)
