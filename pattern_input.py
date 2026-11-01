"""pattern_input.py - کامپوننت ترسیم لمسی چیدمان الکترودها (شبیه الگوی قفل صفحه).

کامپوننت بدون نیاز به build است؛ پوشه pattern_canvas باید کنار این فایل در مخزن باشد.
"""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND = Path(__file__).parent / "pattern_canvas"
_component = components.declare_component("earthing_pattern_canvas", path=str(_FRONTEND))


def pattern_canvas(cols: int, rows: int, pitch: float, points: list[list[int]], key: str):
    """نقاط انتخاب‌شده را به شکل {'points': [[i, j], ...]} برمی‌گرداند (i ستون، j ردیف از پایین)."""
    return _component(cols=cols, rows=rows, pitch=pitch, points=points, key=key, default=None)
