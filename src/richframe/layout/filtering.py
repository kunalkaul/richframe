"""Filtering and sorting configuration models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Iterable, Mapping, Sequence

AxisLiteral = str  # we normalise values internally

__all__ = ["FilterConfig", "SortConfig", "coerce_filter_configs", "coerce_sort_configs"]


def _normalize_axis(axis: str | None) -> str:
    if axis is None:
        return "column"
    value = axis.lower()
    if value in {"column", "columns", "col"}:
        return "column"
    if value in {"row", "rows", "index"}:
        return "index"
    raise ValueError(f"Unsupported axis '{axis}' for filter/sort configuration")


def _ensure_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, (str, bytes)):
        raise TypeError("Iterable value expected for 'in' operator, received string")
    if not isinstance(value, Iterable):
        raise TypeError("Iterable value expected for 'in' operator")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class FilterConfig:
    """Declarative filter definition applied before table construction."""

    key: str
    operator: str
    value: Any
    upper: Any | None = None
    axis: str = "column"

    _VALID_OPERATORS: ClassVar[set[str]] = {
        "eq",
        "ne",
        "gt",
        "ge",
        "lt",
        "le",
        "contains",
        "in",
        "between",
    }
    _ALIASES: ClassVar[dict[str, str]] = {
        "==": "eq",
        "equals": "eq",
        "=": "eq",
        "!=": "ne",
        "<>": "ne",
        ">": "gt",
        ">=": "ge",
        "<": "lt",
        "<=": "le",
        "in": "in",
        "contains": "contains",
        "between": "between",
    }

    def __post_init__(self) -> None:  # noqa: D401 - dataclass validation
        object.__setattr__(self, "axis", _normalize_axis(self.axis))
        canonical = self._ALIASES.get(self.operator.lower(), self.operator.lower())
        if canonical not in self._VALID_OPERATORS:
            raise ValueError(f"Unsupported filter operator '{self.operator}'")
        object.__setattr__(self, "operator", canonical)
        if canonical == "between":
            if self.upper is None:
                raise ValueError("Between operator requires 'upper' value")
            if self.value is None:
                raise ValueError("Between operator requires lower bound 'value'")
        if canonical == "in":
            sequence = _ensure_sequence(self.value)
            object.__setattr__(self, "value", tuple(sequence))

    def to_dict(self) -> dict[str, Any]:
        data = {
            "key": self.key,
            "operator": self.operator,
            "value": self.value,
            "axis": self.axis,
        }
        if self.operator == "between":
            data["upper"] = self.upper
        return data

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "FilterConfig":
        key = data.get("key") or data.get("column") or data.get("field")
        if not key:
            raise ValueError("Filter mapping requires 'key'/'column' field")
        operator = data.get("operator") or data.get("op") or "eq"
        axis = data.get("axis") or data.get("orientation")
        upper = data.get("upper") or data.get("max")
        if "value" in data:
            value = data["value"]
        elif operator == "between":
            value = data.get("min")
        else:
            raise ValueError("Filter mapping requires 'value' field")
        return cls(
            key=str(key),
            operator=str(operator),
            value=value,
            upper=upper,
            axis=str(axis) if axis is not None else "column",
        )


@dataclass(frozen=True, slots=True)
class SortConfig:
    """Declarative sort definition applied before table construction."""

    key: str
    ascending: bool = True
    axis: str = "column"
    na_position: str = "last"

    _VALID_POSITIONS: ClassVar[set[str]] = {"first", "last"}

    def __post_init__(self) -> None:  # noqa: D401 - dataclass validation
        object.__setattr__(self, "axis", _normalize_axis(self.axis))
        position = self.na_position.lower()
        if position not in self._VALID_POSITIONS:
            raise ValueError("na_position must be 'first' or 'last'")
        object.__setattr__(self, "na_position", position)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "ascending": self.ascending,
            "axis": self.axis,
            "na_position": self.na_position,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SortConfig":
        key = data.get("key") or data.get("column") or data.get("field")
        if not key:
            raise ValueError("Sort mapping requires 'key'/'column' field")
        axis = data.get("axis") or data.get("orientation")
        ascending = data.get("ascending")
        if ascending is None:
            order = data.get("order") or data.get("direction")
            if order is None:
                ascending = True
            else:
                ascending = str(order).lower() not in {"desc", "descending", "down"}
        na_position = data.get("na_position") or data.get("na")
        return cls(
            key=str(key),
            ascending=bool(ascending),
            axis=str(axis) if axis is not None else "column",
            na_position=str(na_position).lower() if na_position is not None else "last",
        )


def coerce_filter_configs(
    configs: Sequence[FilterConfig | Mapping[str, Any]],
) -> tuple[FilterConfig, ...]:
    resolved: list[FilterConfig] = []
    for config in configs:
        if isinstance(config, FilterConfig):
            resolved.append(config)
        elif isinstance(config, Mapping):
            resolved.append(FilterConfig.from_mapping(config))
        else:
            raise TypeError("Filters must be FilterConfig instances or mappings")
    return tuple(resolved)


def coerce_sort_configs(
    configs: Sequence[SortConfig | Mapping[str, Any] | str],
) -> tuple[SortConfig, ...]:
    resolved: list[SortConfig] = []
    for config in configs:
        if isinstance(config, SortConfig):
            resolved.append(config)
            continue
        if isinstance(config, Mapping):
            resolved.append(SortConfig.from_mapping(config))
            continue
        if isinstance(config, str):
            if config.startswith("-"):
                resolved.append(SortConfig(key=config[1:], ascending=False))
            else:
                resolved.append(SortConfig(key=config, ascending=True))
            continue
        raise TypeError("Sorts must be SortConfig, mapping, or string expressions")
    return tuple(resolved)
