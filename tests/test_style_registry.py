from __future__ import annotations

from typing import Any

import pytest

from richframe.style import CellStyle, StyleRegistry


def test_style_registry_reuses_class_for_identical_styles() -> None:
    registry = StyleRegistry(prefix="test")

    style_a = CellStyle(background_color="#ffffff")
    style_b = CellStyle(background_color="#ffffff")

    class_a = registry.register(style_a)
    class_b = registry.register(style_b)

    assert class_a == class_b
    assert registry.stylesheet().count("background-color: #ffffff") == 1


def test_style_registry_handles_hash_collisions(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = StyleRegistry(prefix="test")

    def fake_sha1(_: bytes) -> Any:
        class FakeHash:
            def hexdigest(self) -> str:
                return "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

        return FakeHash()

    monkeypatch.setattr("richframe.style.registry.hashlib.sha1", fake_sha1)

    style_a = CellStyle(color="#000000")
    style_b = CellStyle(color="#111111")

    class_a = registry.register(style_a)
    class_b = registry.register(style_b)

    assert class_a is not None and class_b is not None
    assert class_a != class_b
