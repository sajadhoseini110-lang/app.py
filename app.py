"""
محاسبه‌گر مقاومت سیستم زمین
  1) میله‌های عمودی موازی  - BS 7430 (روش ضریب λ، میدان دور)
  2) ترکیب شبکه + میله     - معادلات Schwarz مطابق IEEE Std 80 (ضرایب k1,k2 به روش Sverak)

محدودیت‌ها: خاک همگن، فرکانس قدرت (بدون اندوکتانس)، الکترود در تماس کامل با خاک.
توجه: فرمول‌ها و ضرایب پیش از استفاده در پروژه باید با متن استاندارد تطبیق داده شوند.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st


class InputError(ValueError):
    """ورودی نامعتبر یا خارج از دامنه اعتبار فرمول."""


# ============================================================
# محاسبات (توابع خالص، قابل تست)
# ============================================================
def single_rod_resistance(rho: float, length: float, diameter: float) -> float:
    """مقاومت یک میله عمودی: R = rho/(2*pi*L) * (ln(8L/d) - 1).  d = قطر (m)."""
    if rho <= 0 or length <= 0 or diameter <= 0:
        raise InputError("ρ، طول و قطر میله باید مثبت باشند.")
    if length <= diameter:
        raise InputError("طول میله باید از قطر آن بزرگ‌تر باشد.")
    return rho / (2 * math.pi * length) * (math.log(8 * length / diameter) - 1)


def rod_positions(n: int, s: float, layout: str) -> list[tuple[float, float]]:
    """مختصات میله‌ها: 'line' روی یک خط، 'ring' روی رئوس n‌ضلعی منتظم با ضلع s."""
    if layout == "ring" and n >= 3:
        radius = s / (2 * math.sin(math.pi / n))
        return [
            (radius * math.cos(2 * math.pi * i / n), radius * math.sin(2 * math.pi * i / n))
            for i in range(n)
        ]
    return [(i * s, 0.0) for i in range(n)]


def parallel_rods_resistance(
    rho: float, length: float, diameter: float, n: int, s: float, layout: str = "line"
) -> float:
    """
    مقاومت n میله موازی (روش ضریب λ در BS 7430 به شکل کلی):
        Rn = R/n + (1/n^2) * sum_{i!=j} rho/(2*pi*d_ij)
    برای میله‌های هم‌فاصله روی خط، این رابطه دقیقاً همان Rn = (R/n)(1+λα) است با
        λ = (2/n) * sum_{k=1}^{n-1} (n-k)/k      (n=2:1.00، 3:1.67، 4:2.17، 10:3.86)
    مقاومت متقابل ρ/(2π d) برای d ≳ L معتبر است؛ برای d < L مقاومت متقابل بیش‌برآورد می‌شود.
    """
    r1 = single_rod_resistance(rho, length, diameter)
    if n < 1:
        raise InputError("تعداد میله باید حداقل ۱ باشد.")
    if n == 1:
        return r1
    if s <= 0:
        raise InputError("فاصله میله‌ها باید مثبت باشد.")
    pts = rod_positions(n, s, layout)
    inv_sum = 0.0
    for i, (xi, yi) in enumerate(pts):
        for j, (xj, yj) in enumerate(pts):
            if i != j:
                inv_sum += 1.0 / math.hypot(xi - xj, yi - yj)
    return r1 / n + rho / (2 * math.pi) * inv_sum / n**2


# ضرایب Sverak برای k1,k2 (x = نسبت طول به عرض شبکه)، سه عمق نسبی h/sqrt(A)
_DEPTH_POINTS = (0.0, 0.1, 1 / 6)


def _k_at(point: int, x: float) -> tuple[float, float]:
    if point == 0:
        return -0.04 * x + 1.41, 0.15 * x + 5.50
    if point == 1:
        return -0.05 * x + 1.20, 0.10 * x + 4.68
    return -0.05 * x + 1.13, 0.10 * x + 4.40


def schwarz_k_factors(x: float, h: float, area: float) -> tuple[float, float]:
    """k1,k2 با درون‌یابی خطی بین سه منحنی عمق (0، √A/10، √A/6)؛ x = L/W ≥ 1."""
    if x < 1 or h < 0 or area <= 0:
        raise InputError("نسبت ابعاد باید ≥ ۱ و عمق ≥ ۰ و مساحت > ۰ باشد.")
    r = min(h / math.sqrt(area), _DEPTH_POINTS[-1])
    for idx in range(2):
        lo, hi = _DEPTH_POINTS[idx], _DEPTH_POINTS[idx + 1]
        if r <= hi:
            t = (r - lo) / (hi - lo)
            k1a, k2a = _k_at(idx, x)
            k1b, k2b = _k_at(idx + 1, x)
            return k1a + t * (k1b - k1a), k2a + t * (k2b - k2a)
    return _k_at(2, x)


def _positive(value: float, name: str) -> float:
    if value is None or value <= 0:
        raise InputError(f"جمله لگاریتمی {name} غیرمثبت شد؛ پارامترها خارج از دامنه فرمول‌اند.")
    return value


def schwarz_resistance(
    rho: float,
    grid_len: float,
    grid_wid: float,
    conductor_len: float,
    depth: float,
    conductor_dia: float,
    n_rods: int,
    rod_len: float,
    rod_dia: float,
) -> dict[str, float | None]:
    """
    معادلات Schwarz (IEEE Std 80):
      R1 = ρ/(π Lc) [ln(2Lc/a') + k1 Lc/√A − k2],      a' = √(a·2h)
      R2 = ρ/(2π n Lr) [ln(4Lr/b) − 1 + 2 k1 Lr/√A (√n − 1)^2]
      Rm = ρ/(π Lc) [ln(2Lc/Lr) + k1 Lc/√A − k2 + 1]
      Rg = (R1 R2 − Rm^2)/(R1 + R2 − 2 Rm)
    a = شعاع هادی، b = شعاع میله. برای n=0 نتیجه Rg = R1 است.
    """
    if min(rho, grid_len, grid_wid, conductor_len, depth, conductor_dia) <= 0:
        raise InputError("همه پارامترهای شبکه باید مثبت باشند.")
    area = grid_len * grid_wid
    sqrt_a = math.sqrt(area)
    x = max(grid_len, grid_wid) / min(grid_len, grid_wid)
    k1, k2 = schwarz_k_factors(x, depth, area)

    a_eq = math.sqrt(conductor_dia / 2 * 2 * depth)
    r1 = rho / (math.pi * conductor_len) * _positive(
        math.log(2 * conductor_len / a_eq) + k1 * conductor_len / sqrt_a - k2, "R1"
    )
    if n_rods == 0:
        return {"R1": r1, "R2": None, "Rm": None, "Rg": r1, "k1": k1, "k2": k2}

    if rod_len <= 0 or rod_dia <= 0 or rod_len <= rod_dia:
        raise InputError("طول/قطر میله نامعتبر است.")
    b = rod_dia / 2
    r2 = rho / (2 * math.pi * n_rods * rod_len) * _positive(
        math.log(4 * rod_len / b) - 1
        + 2 * k1 * rod_len / sqrt_a * (math.sqrt(n_rods) - 1) ** 2,
        "R2",
    )
    rm = rho / (math.pi * conductor_len) * _positive(
        math.log(2 * conductor_len / rod_len) + k1 * conductor_len / sqrt_a - k2 + 1, "Rm"
    )
    denom = r1 + r2 - 2 * rm
    if denom <= 1e-9:
        raise InputError("مخرج Rg غیرمثبت شد؛ پارامترها خارج از دامنه اعتبار روش Schwarz هستند.")
    rg = (r1 * r2 - rm**2) / denom
    if rg <= 0:
        raise InputError("Rg غیرفیزیکی شد؛ هندسه ورودی را بازبینی کنید.")
    return {"R1": r1, "R2": r2, "Rm": rm, "Rg": rg, "k1": k1, "k2": k2}


# ============================================================
# رابط کاربری
# ============================================================
RTL_CSS = """
<style>
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
[data-testid="stAlert"], label, .stRadio { direction: rtl; text-align: right; }
[data-testid="stLatex"], .katex { direction: ltr; }
</style>
"""

METHOD_BS = "BS 7430 (میله‌های موازی)"
METHOD_SCH = "Schwarz / IEEE 80 (شبکه + میله)"


def main() -> None:
    st.set_page_config(page_title="طراحی سیستم زمین", layout="wide")
    st.markdown(RTL_CSS, unsafe_allow_html=True)
    st.title("⚡ محاسبه مقاومت سیستم زمین")
    st.caption("BS 7430 (میله‌های موازی) | Schwarz / IEEE Std 80 (شبکه + میله)")

    method = st.radio("روش محاسبه", [METHOD_BS, METHOD_SCH], horizontal=True)

    with st.sidebar:
        st.header("خاک و هدف")
        rho = st.number_input("مقاومت ویژه ρ (Ω·m)", min_value=1.0, value=100.0, step=10.0)
        target = st.number_input("مقاومت هدف (Ω)", min_value=0.1, value=10.0, step=0.5)

        st.header("میله‌های عمودی")
        rod_len = st.number_input("طول میله L (m)", min_value=0.5, value=3.0, step=0.5)
        rod_dia = st.number_input("قطر میله d (m)", min_value=0.005, value=0.016, step=0.001, format="%.3f")

        if method == METHOD_BS:
            n_rods = int(st.number_input("تعداد میله n", min_value=1, value=4, step=1))
            spacing = st.number_input("فاصله بین میله‌ها s (m)", min_value=0.5, value=3.0, step=0.5)
            layout_label = st.radio("چیدمان", ["روی یک خط", "حلقه (رئوس چندضلعی منتظم)"])
            layout = "line" if layout_label == "روی یک خط" else "ring"
        else:
            n_rods = int(st.number_input("تعداد میله n (۰ = فقط شبکه)", min_value=0, value=4, step=1))
            st.header("شبکه افقی")
            grid_len = st.number_input("طول شبکه (m)", min_value=1.0, value=10.0, step=1.0)
            grid_wid = st.number_input("عرض شبکه (m)", min_value=1.0, value=10.0, step=1.0)
            cond_len = st.number_input("طول کل هادی Lc (m)", min_value=1.0, value=40.0, step=5.0)
            depth = st.number_input("عمق دفن h (m)", min_value=0.1, value=0.6, step=0.1)
            cond_dia = st.number_input(
                "قطر هادی (m) - برای نوار، قطر معادل", min_value=0.005, value=0.01, step=0.001, format="%.3f"
            )

    st.header("📊 نتایج")
    notes: list[str] = []
    try:
        if method == METHOD_BS:
            r_single = single_rod_resistance(rho, rod_len, rod_dia)
            r_total = parallel_rods_resistance(rho, rod_len, rod_dia, n_rods, spacing, layout)
            c1, c2, c3 = st.columns(3)
            c1.metric("یک میله", f"{r_single:.2f} Ω")
            c2.metric(f"{n_rods} میله موازی", f"{r_total:.2f} Ω")
            c3.metric("ضریب بهره‌وری η", f"{r_single / (n_rods * r_total):.2f}")
            if n_rods > 1 and spacing < rod_len:
                notes.append("s < L: اثر متقابل بیش‌برآورد می‌شود؛ برای بهره‌وری مناسب s ≥ L توصیه می‌شود.")
            if rod_len / rod_dia < 20:
                notes.append("نسبت L/d کمتر از ۲۰ است؛ دقت فرمول میله کاهش می‌یابد.")
            result = r_total

            def sweep(k: int) -> float:
                return parallel_rods_resistance(rho, rod_len, rod_dia, k, spacing, layout)

            sweep_range, sweep_label = range(1, 21), "تعداد میله"
        else:
            res = schwarz_resistance(
                rho, grid_len, grid_wid, cond_len, depth, cond_dia, n_rods, rod_len, rod_dia
            )
            result = res["Rg"]
            cols = st.columns(4)
            cols[0].metric("R1 شبکه", f"{res['R1']:.2f} Ω")
            cols[1].metric("R2 میله‌ها", "-" if res["R2"] is None else f"{res['R2']:.2f} Ω")
            cols[2].metric("Rm متقابل", "-" if res["Rm"] is None else f"{res['Rm']:.2f} Ω")
            cols[3].metric("Rg نهایی", f"{result:.2f} Ω")
            st.caption(f"k1 = {res['k1']:.3f} ، k2 = {res['k2']:.3f}")
            if depth / math.sqrt(grid_len * grid_wid) > 1 / 6:
                notes.append("h/√A بیشتر از 1/6 است؛ ضرایب k1,k2 در حد منحنی عمق 1/6 نگه داشته شدند.")
            if max(grid_len, grid_wid) / min(grid_len, grid_wid) > 8:
                notes.append("نسبت ابعاد شبکه بیش از ۸ است؛ خارج از دامنه منحنی‌های k1,k2.")
            if cond_len < 2 * (grid_len + grid_wid):
                notes.append("Lc کمتر از محیط شبکه است؛ هندسه ورودی با شبکه بسته سازگار نیست.")

            def sweep(k: int) -> float:
                return schwarz_resistance(
                    rho, grid_len, grid_wid, cond_len, depth, cond_dia, k, rod_len, rod_dia
                )["Rg"]

            sweep_range, sweep_label = range(0, 21), "تعداد میله"

        if result <= target:
            st.success(f"✅ {result:.2f} Ω ≤ هدف {target} Ω")
        else:
            st.error(f"❌ {result:.2f} Ω > هدف {target} Ω")
        for note in notes:
            st.warning("⚠️ " + note)

        rows = []
        for k in sweep_range:
            try:
                rows.append({sweep_label: k, "R (Ω)": sweep(k)})
            except InputError:
                continue
        if rows:
            st.subheader("حساسیت نسبت به تعداد میله")
            st.line_chart(pd.DataFrame(rows).set_index(sweep_label))

    except InputError as exc:
        st.error(str(exc))

    with st.expander("فرمول‌ها"):
        if method == METHOD_BS:
            st.latex(r"R = \frac{\rho}{2\pi L}\left(\ln\frac{8L}{d}-1\right)")
            st.latex(r"R_n = \frac{R}{n}(1+\lambda\alpha),\quad \alpha=\frac{\rho}{2\pi R s}")
            st.latex(r"\lambda_{line} = \frac{2}{n}\sum_{k=1}^{n-1}\frac{n-k}{k}")
        else:
            st.latex(r"R_1=\frac{\rho}{\pi L_c}\left[\ln\frac{2L_c}{a'}+k_1\frac{L_c}{\sqrt A}-k_2\right]")
            st.latex(r"R_2=\frac{\rho}{2\pi n L_r}\left[\ln\frac{4L_r}{b}-1+\frac{2k_1L_r}{\sqrt A}(\sqrt n-1)^2\right]")
            st.latex(r"R_m=\frac{\rho}{\pi L_c}\left[\ln\frac{2L_c}{L_r}+k_1\frac{L_c}{\sqrt A}-k_2+1\right]")
            st.latex(r"R_g=\frac{R_1R_2-R_m^2}{R_1+R_2-2R_m}")

    with st.expander("محدودیت‌ها و فرضیات"):
        st.markdown(
            "- خاک همگن (یک‌لایه)؛ برای خاک چندلایه نتیجه معتبر نیست.\n"
            "- فرکانس قدرت و مقاومت خالص؛ اندوکتانس و رفتار گذرا (صاعقه) لحاظ نشده است.\n"
            "- مقاومت متقابل میله‌ها به شکل میدان دور تقریب زده شده و برای s ≥ L دقیق‌تر است.\n"
            "- ضرایب k1,k2 تقریب Sverak از منحنی‌های IEEE 80 هستند و برای نسبت ابعاد ۱ تا ۸ تعریف شده‌اند.\n"
            "- نتیجه تحلیلی جایگزین اندازه‌گیری میدانی (روش افت پتانسیل) و تأیید طراحی نیست.\n"
            "- پیش از استفاده در پروژه، فرمول‌ها و ضرایب با متن استاندارد تطبیق داده شوند."
        )

    st.divider()
    st.caption("مراجع: BS 7430:2011+A1:2015 | IEEE Std 80-2013")


if __name__ == "__main__":
    main()
