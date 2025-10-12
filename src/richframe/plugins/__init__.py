"""Plugin system and built-in plugins for richframe."""
from .base import Plugin, PluginBase
from .color import ColorScalePlugin
from .databar import DataBarPlugin
from .icon import IconSetPlugin, IconRule
from .rules import conditional_format

__all__ = [
    "Plugin",
    "PluginBase",
    "ColorScalePlugin",
    "DataBarPlugin",
    "IconSetPlugin",
    "IconRule",
    "conditional_format",
]
