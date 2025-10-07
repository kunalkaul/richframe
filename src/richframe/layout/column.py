"""Column layout configuration objects."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

__all__ = ["ColumnConfig", "ColumnLayout"]


@dataclass(frozen=True, slots=True)
class ColumnConfig:
    """Per-column layout options."""

    id: str
    width: str | None = None
    align: str | None = None
    visible: bool = True
    sticky: bool = False

    def apply(self, overrides: Mapping[str, object]) -> ColumnConfig:
        updates = {
            key: value
            for key, value in overrides.items()
            if hasattr(self, key)
        }
        return replace(self, **updates)


class ColumnLayout:
    """Container for column configuration keyed by column id."""

    def __init__(self, configs: Iterable[ColumnConfig] | None = None) -> None:
        self._configs: dict[str, ColumnConfig] = {}
        for config in configs or []:
            self._configs[str(config.id)] = config

    def get(self, column_id: str) -> ColumnConfig | None:
        return self._configs.get(column_id)

    def set(self, config: ColumnConfig) -> None:
        self._configs[str(config.id)] = config

    def items(self) -> Iterable[tuple[str, ColumnConfig]]:
        return self._configs.items()

    def visible_columns(self, order: Iterable[str]) -> list[str]:
        return [
            column_id
            for column_id in order
            if self._configs.get(column_id, ColumnConfig(column_id)).visible
        ]

    def sticky_columns(self) -> list[str]:
        return [column_id for column_id, cfg in self._configs.items() if cfg.sticky]
