"""
app.py - طراحی و تحلیل سیستم زمین (Streamlit)
  تب ۱: تحلیل آرایش دلخواه میله‌ها (ویرایش مختصات، پیش‌تنظیم، CSV) + نقشه + توزیع جریان
  تب ۲: مشاور طراحی: از داده‌های اولیه تا پیشنهاد آرایش، طول، جنس و مقطع
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import earthing_calc as ec
from pattern_input import pattern_canvas

st.set_page_config(page_title="طراحی سیستم زمین", layout="wide")
st.markdown(
    """
<style>
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
[data-testid="stAlert"], label { direction: rtl; text-align: right; }
.katex, [data-testid="stLatex"] { direction: ltr; }
</style>
""",
    unsafe_allow_html=True,
)
st.title("⚡ طراحی و تحلیل سیستم زمین")

# ------------------------------------------------------------
# پارامترهای مشترک (سایدبار)
# ------------------------------------------------------------
with st.sidebar:
    st.header("خاک و هدف")
    rho_meas = st.number_input("مقاومت ویژه اندازه‌گیری‌شده ρ (Ω·m)", min_value=1.0, value=350.0, step=10.0)
    season = st.number_input(
        "ضریب فصلی/اطمینان", min_value=1.0, value=1.0, step=0.1,
        help="برای طراحی در بدترین حالت (خاک خشک) ρ در این ضریب ضرب می‌شود. مقدار را با داده محلی تعیین کنید.",
    )
    rho = rho_meas * season
    st.caption(f"ρ طراحی = {rho:.1f} Ω·m")
    target = st.number_input("مقاومت هدف (Ω)", min_value=0.05, value=10.0, step=0.5)
    st.header("میله")
    rod_dia_mm = st.number_input("قطر میله (mm)", min_value=5.0, value=16.0, step=0.5)
    rod_dia = rod_dia_mm / 1000.0

tab_calc, tab_design, tab_help = st.tabs(["🧮 تحلیل آرایش دلخواه", "🧠 مشاور طراحی", "📘 راهنما و محدودیت‌ها"])

# ============================================================
# تب ۱ - تحلیل آرایش دلخواه
# ============================================================
with tab_calc:
    if "layout_df" not in st.session_state:
        st.session_state.layout_df = pd.DataFrame(ec.EXAMPLE_BOOK, columns=["x", "y"])
        st.session_state.ver = 0

    rod_len = st.number_input("طول (عمق) هر میله L (m)", min_value=0.5, value=2.4, step=0.1)

    MODE_DRAW = "✋ ترسیم با لمس (مثل قفل صفحه)"
    MODE_TABLE = "📋 جدول مختصات"
    st.session_state.setdefault("canvas_pts", [])
    st.session_state.setdefault("canvas_ver", 0)

    def to_table(df_: pd.DataFrame) -> None:
        st.session_state.layout_df = df_.copy()
        st.session_state.ver += 1
        st.session_state.input_mode = MODE_TABLE

    st.subheader("۱) چیدمان میله‌ها")
    mode = st.radio("روش ورود چیدمان", [MODE_DRAW, MODE_TABLE], horizontal=True, key="input_mode")

    if mode == MODE_DRAW:
        g1, g2, g3 = st.columns(3)
        cols_n = int(g1.number_input("ستون‌های نقطه", min_value=3, max_value=30, value=10, step=1))
        rows_n = int(g2.number_input("ردیف‌های نقطه", min_value=3, max_value=30, value=8, step=1))
        pitch = g3.number_input("فاصله بین نقاط (m)", min_value=0.1, value=2.0, step=0.5)
        st.session_state.canvas_pts = [
            p for p in st.session_state.canvas_pts if p[0] < cols_n and p[1] < rows_n
        ]
        val = pattern_canvas(
            cols_n, rows_n, pitch, st.session_state.canvas_pts,
            key=f"cv_{st.session_state.canvas_ver}_{cols_n}_{rows_n}",
        )
        if val and "points" in val:
            st.session_state.canvas_pts = [list(map(int, p)) for p in val["points"]]
        pts_df = pd.DataFrame(
            [(i * pitch, j * pitch) for i, j in st.session_state.canvas_pts], columns=["x", "y"]
        )
        st.caption(
            "روی نقطه‌ها بکشید یا لمس کنید تا میله اضافه شود؛ لمس یا کشیدن روی میله‌ی موجود آن را حذف می‌کند. "
            "برای فاصله‌های غیرمضرب (مثلاً ۳٫۶ m) چیدمان را به جدول منتقل و عدد را اصلاح کنید."
        )
        st.button("انتقال به جدول برای ویرایش دقیق", on_click=to_table, args=(pts_df,))
    else:
        kind = st.selectbox(
            "ساخت سریع چیدمان",
            ["مثال کتاب (۹ میله)", "روی یک خط", "حلقه (چندضلعی منتظم)", "شبکه مستطیلی"],
        )
        c1, c2, c3, c4 = st.columns(4)
        n_in = rows_in = cols_in = 0
        s_in = sx_in = sy_in = 0.0
        if kind in ("روی یک خط", "حلقه (چندضلعی منتظم)"):
            n_in = int(c1.number_input("تعداد میله", min_value=1, value=4, step=1))
            s_in = c2.number_input("فاصله/ضلع (m)", min_value=0.1, value=3.0, step=0.5)
        elif kind == "شبکه مستطیلی":
            rows_in = int(c1.number_input("تعداد ردیف", min_value=1, value=3, step=1))
            cols_in = int(c2.number_input("تعداد ستون", min_value=1, value=3, step=1))
            sx_in = c3.number_input("فاصله افقی (m)", min_value=0.1, value=4.0, step=0.5)
            sy_in = c4.number_input("فاصله عمودی (m)", min_value=0.1, value=4.0, step=0.5)

        if st.button("ایجاد / جایگزینی چیدمان"):
            if kind == "مثال کتاب (۹ میله)":
                pts = ec.EXAMPLE_BOOK
            elif kind == "روی یک خط":
                pts = ec.layout_line(n_in, s_in)
            elif kind == "حلقه (چندضلعی منتظم)":
                pts = ec.layout_ring(n_in, s_in)
            else:
                pts = ec.layout_grid(rows_in, cols_in, sx_in, sy_in)
            st.session_state.layout_df = pd.DataFrame(pts, columns=["x", "y"])
            st.session_state.ver += 1
            st.rerun()

        uploaded = st.file_uploader("یا بارگذاری فایل CSV با ستون‌های x,y (متر)", type=["csv"])
        if uploaded is not None and st.session_state.get("last_upload") != uploaded.file_id:
            try:
                df_up = pd.read_csv(uploaded)
                df_up.columns = [str(c).strip().lower() for c in df_up.columns]
                st.session_state.layout_df = df_up[["x", "y"]].astype(float)
                st.session_state.ver += 1
                st.session_state.last_upload = uploaded.file_id
                st.rerun()
            except Exception:
                st.error("فایل CSV باید ستون‌های x و y (عددی) داشته باشد.")

        st.caption("جدول زیر قابل ویرایش است؛ مختصات هر میله را به متر وارد کنید (ردیف جدید با + اضافه می‌شود).")
        edited = st.data_editor(
            st.session_state.layout_df,
            num_rows="dynamic",
            key=f"editor_{st.session_state.ver}",
            column_config={
                "x": st.column_config.NumberColumn("x (m)", format="%.2f"),
                "y": st.column_config.NumberColumn("y (m)", format="%.2f"),
            },
        )
        pts_df = edited.dropna().astype(float).reset_index(drop=True)

    st.subheader("۲) نتیجه")
    try:
        if pts_df.empty:
            raise ec.InputError("حداقل یک میله وارد کنید.")
        res = ec.group_resistance(rho, rod_len, rod_dia, list(map(tuple, pts_df[["x", "y"]].values)))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("تعداد میله", res.n)
        m2.metric("یک میله", f"{res.r_single:.2f} Ω")
        m3.metric("مقاومت معادل مجموعه", f"{res.r_eq:.2f} Ω")
        m4.metric("ضریب بهره‌وری η", f"{res.eta:.2f}")
        if res.r_eq <= target:
            st.success(f"✅ {res.r_eq:.2f} Ω ≤ هدف {target} Ω")
        else:
            st.error(f"❌ {res.r_eq:.2f} Ω > هدف {target} Ω")

        if res.n > 1 and res.min_spacing < rod_len:
            st.warning("⚠️ کمترین فاصله بین میله‌ها کمتر از طول میله است؛ بهره‌وری پایین می‌آید.")
        st.caption(
            f"مقایسه روش‌ها: هم‌پتانسیل (اصلی) {res.r_eq:.2f} Ω | میانگین با جریان برابر {res.r_avg:.2f} Ω | "
            f"روش ساده BS 7430 (میدان دور) {res.r_simple:.2f} Ω"
        )

        plot = pts_df.copy()
        plot["no"] = [str(i + 1) for i in range(len(plot))]
        plot["share"] = res.shares * 100
        xr = max(plot.x.max() - plot.x.min(), 1.0)
        yr = max(plot.y.max() - plot.y.min(), 1.0)
        height = int(min(420, max(180, 520 * yr / xr)))
        base = alt.Chart(plot)
        enc_x = alt.X("x:Q", title="x (m)", scale=alt.Scale(zero=False, nice=True, padding=25))
        enc_y = alt.Y("y:Q", title="y (m)", scale=alt.Scale(zero=False, nice=True, padding=25))
        points = base.mark_circle(size=260).encode(
            x=enc_x, y=enc_y,
            color=alt.Color("share:Q", title="سهم جریان (%)", scale=alt.Scale(scheme="orangered")),
            tooltip=[alt.Tooltip("no:N", title="شماره"), alt.Tooltip("x:Q"), alt.Tooltip("y:Q"),
                     alt.Tooltip("share:Q", title="سهم جریان %", format=".1f")],
        )
        labels = base.mark_text(dy=-16, fontSize=12).encode(x=enc_x, y=enc_y, text="no:N")
        st.altair_chart((points + labels).properties(width="container", height=height))

        table = plot[["no", "x", "y", "share"]].rename(
            columns={"no": "شماره", "x": "x (m)", "y": "y (m)", "share": "سهم جریان (%)"})
        st.dataframe(table.round(2), hide_index=True)

        with st.expander("روش محاسبه"):
            st.latex(r"R_{11}=\frac{\rho}{2\pi L}\left(\ln\frac{8L}{d}-1\right)")
            st.latex(r"R_{ij}=\frac{\rho}{4\pi L^{2}}\iint\left[\frac{1}{\sqrt{s^2+(z-\zeta)^2}}+\frac{1}{\sqrt{s^2+(z+\zeta)^2}}\right]dz\,d\zeta")
            st.latex(r"R_{eq}=\frac{1}{\mathbf 1^{T}Z^{-1}\mathbf 1}")
            st.caption(
                "میله‌ها هم‌پتانسیل در نظر گرفته می‌شوند و جریان هر میله از حل دستگاه Z·I=V به‌دست می‌آید؛ "
                "به همین دلیل میله‌های کناری/گوشه سهم بیشتری از جریان دارند. اثر هادی افقی رابط در نتیجه "
                "لحاظ نشده است (محافظه‌کارانه)."
            )
    except ec.InputError as exc:
        st.error(str(exc))

# ============================================================
# تب ۲ - مشاور طراحی
# ============================================================
with tab_design:
    st.subheader("داده‌های اولیه پروژه")
    a1, a2, a3 = st.columns(3)
    lx = a1.number_input("طول زمین در دسترس (m)", min_value=2.0, value=30.0, step=1.0)
    ly = a2.number_input("عرض زمین در دسترس (m)", min_value=2.0, value=30.0, step=1.0)
    max_len = a3.selectbox("حداکثر طول عملی میله (m)", [3.0, 4.5, 6.0, 9.0, 12.0], index=2)
    b1, b2, b3 = st.columns(3)
    fault_ka = b1.number_input("جریان خطای زمین عبوری از الکترود (kA)", min_value=0.1, value=10.0, step=0.5)
    clear_t = b2.number_input("زمان قطع خطا (s)", min_value=0.05, value=1.0, step=0.05)
    min_eta = b3.slider("حداقل ضریب بهره‌وری قابل قبول η", 0.3, 0.9, 0.5, 0.05)
    c1, c2, c3 = st.columns(3)
    soil_type = c1.selectbox("خورندگی خاک", ["معمولی", "خورنده (کلرید/سولفات بالا یا pH پایین)"])
    steel_bonded = c2.checkbox("به آرماتور/سازه فولادی متصل می‌شود", value=True)
    depth = c3.number_input("عمق دفن هادی افقی (m)", min_value=0.3, value=0.7, step=0.1)
    d1, d2, d3 = st.columns(3)
    material = d1.selectbox("جنس مورد بررسی برای مقطع", list(ec.MATERIAL_CONSTANTS))
    theta_i = d2.number_input("دمای اولیه (°C)", value=30.0)
    theta_f = d3.number_input("دمای نهایی مجاز (°C)", value=300.0,
                              help="به نوع هادی و اتصال بستگی دارد؛ باید با استاندارد تأیید شود.")

    lengths = tuple(v for v in ec.SEARCH_LENGTHS if v <= max_len)

    @st.cache_data(show_spinner=False)
    def cached_rods(rho_, d_, lx_, ly_, lengths_):
        return ec.search_rod_layouts(rho_, d_, lx_, ly_, lengths_)

    @st.cache_data(show_spinner=False)
    def cached_grid(rho_, lx_, ly_, depth_, d_, lengths_):
        return ec.search_grid_with_rods(rho_, lx_, ly_, depth_, 0.01, d_, lengths_)

    st.subheader("نتایج مشاور")
    st.markdown("**مقاومت یک میله به تفکیک طول** (ρ طراحی = %.0f Ω·m)" % rho)
    single_rows = []
    for length in lengths:
        r1 = ec.rod_self_resistance(rho, length, rod_dia)
        single_rows.append({"طول میله (m)": length, "مقاومت یک میله (Ω)": round(r1, 1),
                            "حداقل تعداد در حالت ایده‌آل": int(-(-r1 // target))})
    st.dataframe(pd.DataFrame(single_rows), hide_index=True)

    rods_df = cached_rods(rho, rod_dia, lx, ly, lengths)
    ok = rods_df[(rods_df.R <= target) & (rods_df.eta >= min_eta)].sort_values(["total_len", "R"])
    best_option = None
    st.markdown("**گزینه‌های فقط‌میله‌ای که هدف را برآورده می‌کنند** (مرتب بر اساس کمترین مجموع طول میله)")
    if ok.empty:
        st.warning("هیچ آرایش فقط‌میله‌ای در این زمین با شرایط داده‌شده به هدف نمی‌رسد. بهترین‌های موجود:")
        show = rods_df.sort_values("R").head(5)
    else:
        show = ok.head(8)
        best_option = ok.iloc[0]
    st.dataframe(
        show.rename(columns={"desc": "آرایش", "L": "طول میله (m)", "n": "تعداد", "R": "R (Ω)",
                             "eta": "η", "total_len": "مجموع طول (m)", "s_over_L": "کمترین s/L"})
        [["آرایش", "طول میله (m)", "تعداد", "R (Ω)", "η", "مجموع طول (m)", "کمترین s/L"]].round(2),
        hide_index=True,
    )

    grid_df = cached_grid(rho, lx, ly, depth, rod_dia, lengths)
    if not grid_df.empty:
        st.markdown("**شبکه افقی + میله (Schwarz / IEEE 80)** — بهترین گزینه‌ها")
        gshow = grid_df.sort_values("R").head(6).rename(
            columns={"mesh": "تقسیمات هر ضلع", "Lc": "طول هادی (m)", "n": "تعداد میله",
                     "L": "طول میله (m)", "R": "Rg (Ω)", "total_len": "مجموع طول (m)"})
        st.dataframe(gshow.round(2), hide_index=True)
        if (grid_df.R <= target).any():
            cheapest = grid_df[grid_df.R <= target].sort_values("total_len").iloc[0]
            st.info(f"کم‌هزینه‌ترین شبکه برآورنده هدف: {int(cheapest.mesh)} تقسیم، "
                    f"{cheapest.Lc:.0f} m هادی، {int(cheapest.n)} میله {cheapest.L:g} m → {cheapest.R:.2f} Ω")

    st.markdown("**مقطع هادی (اتصال کوتاه)**")
    try:
        i_a = fault_ka * 1000
        s_main = ec.min_cross_section(i_a, clear_t, material, theta_i, theta_f)
        n_for_share = int(best_option.n) if best_option is not None else 4
        s_rod = ec.min_cross_section(i_a * min(1.0, 2.0 / n_for_share), clear_t, material, theta_i, theta_f)
        import math
        d_rod_min = math.sqrt(4 * s_rod / math.pi)
        st.write(
            f"حداقل مقطع الکتریکی هادی اصلی ({material}): **{s_main:.0f} mm²** | "
            f"برای هر میله (با فرض سهم حدود دو برابر میانگین): {s_rod:.0f} mm² ≈ قطر {d_rod_min:.1f} mm"
        )
        st.caption("حداقل ابعاد مکانیکی و ضخامت خوردگی را باید جداگانه از IEC/BS EN 62561-2 و BS 7430 لحاظ کنید؛ "
                   "معمولاً عامل تعیین‌کننده قطر میله همین‌هاست، نه جریان.")
    except ec.InputError as exc:
        st.error(str(exc))

    if best_option is not None:
        gpr = fault_ka * 1000 * best_option.R
        st.write(f"ولتاژ بالارفتن پتانسیل زمین (GPR) تقریبی با بهترین گزینه: **{gpr / 1000:.2f} kV** "
                 "(ولتاژ تماس/گام باید جداگانه طبق BS EN 50522 / IEEE 80 بررسی شود).")

    st.subheader("پیشنهادهای مهندسی")
    notes: list[str] = []
    if rho > 300:
        notes.append("خاک پرمقاومت است؛ پیش از هر چیز اندازه‌گیری چندلایه (Wenner) انجام شود. اگر لایه عمیق‌تر "
                     "مقاومت کمتری دارد، میله‌های عمیق‌تر (چندتکه‌ای با کوپلینگ) بسیار مؤثرتر از افزایش تعداد میله‌اند.")
    if ok.empty:
        notes.append("برای رسیدن به هدف: میله‌های بلندتر، شبکه افقی بزرگ‌تر، اتصال به الکترود دور یا الکترودهای "
                     "طبیعی (پی/آرماتور)، و در نهایت بهبود خاک (بنتونیت/GEM) را بررسی کنید.")
    else:
        notes.append("برای کاهش هزینه معمولاً میله‌های بلندتر و کم‌تعدادتر از تعداد زیاد میله کوتاه کارآمدتر است؛ "
                     "فاصله میله‌ها را ≥ طول میله بگیرید.")
    if soil_type != "معمولی":
        notes.append("خاک خورنده: مس‌اندود/استیل ضدزنگ یا مس را ترجیح دهید و ضخامت خوردگی را افزایش دهید.")
    if steel_bonded and material == "مس":
        notes.append("اتصال مس برهنه به فولاد/آرماتور دفن‌شده خوردگی گالوانیک ایجاد می‌کند؛ یا فولاد گالوانیزه "
                     "هم‌جنس یا جداسازی/حفاظت کاتدی را در نظر بگیرید.")
    if lx * ly < 400:
        notes.append("زمین کوچک است؛ افزایش تعداد میله در فضای محدود بهره‌وری را سریع کم می‌کند.")
    notes.append("مقدار نهایی باید با اندازه‌گیری میدانی (روش افت پتانسیل) تأیید و در بدترین فصل بازبینی شود.")
    for n_ in notes:
        st.write("• " + n_)

# ============================================================
# تب ۳ - راهنما
# ============================================================
with tab_help:
    st.markdown(
        """
**محدودیت‌ها**
- خاک همگن یک‌لایه؛ فرکانس قدرت؛ بدون اثر اندوکتانس و رفتار گذرا.
- میله‌ها هم‌طول، هم‌قطر و عمودی که از سطح خاک شروع می‌شوند.
- اثر هادی افقی بین میله‌ها در تب ۱ لحاظ نمی‌شود؛ برای آن از تب مشاور (Schwarz) استفاده کنید.
- ضرایب k1 و k2 در روش Schwarz تقریب Sverak از منحنی‌های IEEE 80 هستند (نسبت ابعاد ۱ تا ۸).
- مقطع هادی با روش آدیاباتیک IEC 60949 محاسبه می‌شود؛ ثابت‌های K و β و دمای نهایی باید با استاندارد تأیید شوند.
- این برنامه جایگزین مطالعه ولتاژ تماس/گام و اندازه‌گیری میدانی نیست.

**مراجع:** BS 7430:2011+A1:2015 | IEEE Std 80-2013 | IEC 60949 | BS EN 50522 | IEC 62561-2
"""
    )
