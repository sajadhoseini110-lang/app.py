from pathlib import Path
import streamlit.components.v1 as components

# مسیر پوشه pattern_canvas
_FRONTEND = Path(__file__).parent / "pattern_canvas"

# تعریف کامپوننت
_component_func = components.declare_component("pattern_canvas", path=str(_FRONTEND))

def pattern_canvas(key="pattern_canvas"):
    """
    فراخوانی کامپوننت بوم ترسیم.
    خروجی یک لیست از رشته‌هاست (مثلاً ['0,1', '2,3']) که مختصات نقاط انتخاب شده را نشان می‌دهد.
    """
    return _component_func(key=key, default=[])