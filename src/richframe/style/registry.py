"""Utilities for deduplicating styles into CSS class definitions."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .model import BaseStyle

__all__ = ["StyleRegistry", "StyleDefinition"]


@dataclass(slots=True, frozen=True)
class StyleDefinition:
    """Associated style with the class name used in the stylesheet."""

    class_name: str
    style: BaseStyle


class StyleRegistry:
    """Assign deterministic class names to style declarations."""

    def __init__(self, *, prefix: str = "rf") -> None:
        self._prefix = prefix
        self._lookup: Dict[BaseStyle, str] = {}
        self._order: List[BaseStyle] = []

    def register(self, style: BaseStyle | None) -> str | None:
        if style is None or style.is_empty():
            return None
        existing = self._lookup.get(style)
        if existing is not None:
            return existing
        class_name = self._generate_class_name(style)
        self._lookup[style] = class_name
        self._order.append(style)
        return class_name

    def definitions(self) -> Iterable[StyleDefinition]:
        for style in self._order:
            yield StyleDefinition(self._lookup[style], style)

    def stylesheet(self) -> str:
        lines = [
            f".{definition.class_name} {{ {definition.style.css_text()} }}"
            for definition in self.definitions()
        ]
        return "\n".join(lines)

    def _generate_class_name(self, style: BaseStyle) -> str:
        digest = hashlib.sha1(style.css_text().encode("utf-8")).hexdigest()[:8]
        return f"{self._prefix}-{digest}"
