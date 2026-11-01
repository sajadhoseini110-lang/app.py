import math
from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="GroundStudio | تحلیل سیستم زمین",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- UI / styling -----------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap');
      html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: 'Vazirmatn', Tahoma, sans-serif;
      }
      .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px;}
      .hero {
        padding: 1.15rem 1.4rem; border-radius: 16px;
        background: linear-gradient(120deg, #e8f5f3 0%, #f6f9fc 70%);
        border: 1px solid #d7e8e6; margin-bottom: 1rem;
      }
      .hero h1 {font-size: 1.8rem; margin: 0; color: #16354a;}
      .hero p {margin: .35rem 0 0; color: #587080;}
      .note {padding: .8rem 1rem; background: #fff8e8; border: 1px solid #f0ddb0;
             border-radius: 10px; color: #6d5725; line-height: 1.8;}
      div[data-testid="stMetric"] {background: white; border: 1px solid #e3eaf0;
        padding: .8rem 1rem; border-radius: 12px;}
      h2, h3 {color: #16354a;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>⚡ GroundStudio</h1>
      <p>ابزار مقدماتی ترسیم هندسه و برآورد مقاومت یک الکترود قائم در خاک همگن</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def rod_resistance(rho: float, length_m: float, diameter_m: float) -> float:
    """Approximate resistance of one vertical rod in homogeneous soil."""
    if rho <= 0 or length_m <= 0 or diameter_m <= 0:
        raise ValueError("مقادیر باید مثبت باشند.")
    if diameter_m >= length_m:
        raise ValueError("قطر الکترود باید از طول آن کوچک‌تر باشد.")
    return rho / (2 * math.pi * length_m) * (math.log(4 * length_m / diameter_m) - 1)


def initial_electrodes(n: int = 9, spacing: float = 3.6) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ID": [f"E{i + 1}" for i in range(n)],
            "X (m)": [round(i * spacing, 2) for i in range(n)],
            "Y (m)": [0.0 for _ in range(n)],
        }
    )


if "electrodes" not in st.session_state:
    st.session_state.electrodes = initial_electrodes()
if "next_id" not in st.session_state:
    st.session_state.next_id = 10

# ----------------------------- Sidebar inputs -----------------------------
with st.sidebar:
    st.header("مشخصات پروژه")
    project_name = st.text_input("نام پروژه", "پروژه نمونه سیستم زمین")
    rho = st.number_input(
        "مقاومت ویژه خاک ρ (Ω·m)", min_value=1.0, max_value=100000.0,
        value=350.0, step=10.0,
        help="مقدار اندازه‌گیری‌شده یا مقدار فرضی ورودی را وارد کنید.",
    )
    rod_length = st.number_input(
        "طول الکترود L (m)", min_value=0.1, max_value=100.0,
        value=2.4, step=0.1,
    )
    rod_diameter_mm = st.number_input(
        "قطر الکترود d (mm)", min_value=1.0, max_value=200.0,
        value=16.0, step=1.0,
    )
    st.divider()
    st.caption("تغییر مشخصات بالا، برآورد مقاومت یک الکترود را به‌روزرسانی می‌کند.")

diameter_m = rod_diameter_mm / 1000.0
try:
    r_single = rod_resistance(rho, rod_length, diameter_m)
    calc_error = None
except ValueError as exc:
    r_single = float("nan")
    calc_error = str(exc)

# ----------------------------- Main layout -----------------------------
tab_layout, tab_calc, tab_notes = st.tabs(
    ["📐 هندسه و الکترودها", "🧮 محاسبات", "ℹ️ راهنما و محدودیت‌ها"]
)

with tab_layout:
    left, right = st.columns([1.1, 1.8], gap="large")

    with left:
        st.subheader("مدیریت الکترودها")
        st.write("مختصات هر الکترود را مستقیماً در جدول ویرایش کن.")
        edited = st.data_editor(
            st.session_state.electrodes,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="electrode_editor",
            column_config={
                "ID": st.column_config.TextColumn("شناسه", required=True),
                "X (m)": st.column_config.NumberColumn("X (m)", min_value=-10000.0, max_value=10000.0, step=0.5, format="%.2f", required=True),
                "Y (m)": st.column_config.NumberColumn("Y (m)", min_value=-10000.0, max_value=10000.0, step=0.5, format="%.2f", required=True),
            },
        )

        # Keep a clean, unique set of IDs and numeric coordinates.
        edited = edited.copy()
        edited["ID"] = edited["ID"].astype(str).str.strip()
        edited["X (m)"] = pd.to_numeric(edited["X (m)"], errors="coerce")
        edited["Y (m)"] = pd.to_numeric(edited["Y (m)"], errors="coerce")
        valid = (
            edited["ID"].ne("").all()
            and edited["ID"].is_unique
            and edited[["X (m)", "Y (m)"]].notna().all().all()
        )
        if valid:
            st.session_state.electrodes = edited.reset_index(drop=True)
        else:
            st.error("شناسه‌ها باید خالی یا تکراری نباشند و مختصات باید عددی باشند. آخرین داده معتبر حفظ شد.")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("＋ افزودن الکترود", use_container_width=True):
                current = st.session_state.electrodes
                new_id = f"E{st.session_state.next_id}"
                max_x = float(current["X (m)"].max()) if not current.empty else 0.0
                y = float(current["Y (m)"].iloc[-1]) if not current.empty else 0.0
                row = pd.DataFrame([{"ID": new_id, "X (m)": round(max_x + 2.0, 2), "Y (m)": y}])
                st.session_state.electrodes = pd.concat([current, row], ignore_index=True)
                st.session_state.next_id += 1
                st.rerun()
        with c2:
            if st.button("↺ بازنشانی نمونه", use_container_width=True):
                st.session_state.electrodes = initial_electrodes()
                st.session_state.next_id = 10
                st.rerun()
        with c3:
            csv = st.session_state.electrodes.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇ دریافت CSV", csv, file_name="groundstudio_electrodes.csv", mime="text/csv", use_container_width=True)

    with right:
        st.subheader("نمای پلان")
        plot_df = st.session_state.electrodes.copy()
        fig = go.Figure()
        if len(plot_df) > 1:
            # Connecting line is only a visual guide, not a claim of electrical continuity.
            fig.add_trace(
                go.Scatter(
                    x=plot_df["X (m)"], y=plot_df["Y (m)"],
                    mode="lines", line=dict(color="#159c91", width=2, dash="dot"),
                    name="راهنمای هندسه", hoverinfo="skip",
                )
            )
        fig.add_trace(
            go.Scatter(
                x=plot_df["X (m)"], y=plot_df["Y (m)"],
                mode="markers+text",
                text=plot_df["ID"], textposition="top center",
                marker=dict(size=13, color="#126d68", line=dict(width=2, color="white")),
                customdata=plot_df[["ID"]],
                hovertemplate="<b>%{customdata[0]}</b><br>X = %{x:.2f} m<br>Y = %{y:.2f} m<extra></extra>",
                name="الکترودها",
            )
        )
        fig.update_layout(
            height=520, margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="white", plot_bgcolor="#fbfcfe",
            xaxis_title="X (m)", yaxis_title="Y (m)",
            xaxis=dict(showgrid=True, gridcolor="#e4eaf0", zeroline=True, zerolinecolor="#b7c6d2"),
            yaxis=dict(showgrid=True, gridcolor="#e4eaf0", zeroline=True, zerolinecolor="#b7c6d2", scaleanchor="x", scaleratio=1),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})
        st.caption("برای اصلاح مختصات از جدول سمت چپ استفاده کن. خطوط فقط راهنمای هندسه‌اند و اتصال الکتریکی واقعی را اثبات نمی‌کنند.")

with tab_calc:
    st.subheader("برآورد مقاومت یک الکترود قائم")
    if calc_error:
        st.error(calc_error)
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("مقاومت ویژه خاک", f"{rho:,.1f} Ω·m")
        m2.metric("طول الکترود", f"{rod_length:.2f} m")
        m3.metric("قطر الکترود", f"{rod_diameter_mm:.1f} mm")
        m4.metric("مقاومت تقریبی یک الکترود", f"{r_single:.2f} Ω")

        st.markdown("#### رابطه مورد استفاده")
        st.latex(r"R \\approx \\frac{\\rho}{2\\pi L}\\left[\\ln\\left(\\frac{4L}{d}\\right)-1\\right]")
        st.markdown(
            f"""
            با جایگذاری داده‌های ورودی:

            - مقاومت ویژه خاک: \\(\\rho = {rho:.2f}\\;\\Omega\\cdot m\\)
            - طول الکترود: \\(L = {rod_length:.3f}\\;m\\)
            - قطر الکترود: \\(d = {diameter_m:.4f}\\;m\\)
            - نتیجه: \\(R \\approx {r_single:.3f}\\;\\Omega\\)
            """
        )
        st.info("این رابطه یک برآورد تقریبی برای یک الکترود قائم منفرد در خاک همگن است؛ مقاومت کل گروه از ضرب یا تقسیم ساده این عدد بر تعداد الکترودها به دست نمی‌آید.")

        st.markdown("#### مشخصات هندسه")
        st.dataframe(st.session_state.electrodes, use_container_width=True, hide_index=True)
        report = StringIO()
        report.write(f"GroundStudio - گزارش مقدماتی\nپروژه: {project_name}\n")
        report.write(f"مقاومت ویژه خاک: {rho:.3f} ohm-m\n")
        report.write(f"طول الکترود: {rod_length:.3f} m\nقطر الکترود: {rod_diameter_mm:.3f} mm\n")
        report.write(f"مقاومت تقریبی یک الکترود: {r_single:.4f} ohm\n\n")
        report.write("مختصات الکترودها:\n")
        report.write(st.session_state.electrodes.to_string(index=False))
        st.download_button(
            "⬇ دریافت گزارش متنی",
            data=report.getvalue().encode("utf-8-sig"),
            file_name="groundstudio_report.txt",
            mime="text/plain",
        )

with tab_notes:
    st.subheader("دامنه اعتبار و محدودیت‌ها")
    st.markdown(
        """
        **این نسخه ابزار مقدماتی است و برای تأیید ایمنی یا تحویل طراحی نهایی کافی نیست.**

        - مدل خاک، همگن و با مقاومت ویژه ثابت فرض شده است.
        - محاسبه فقط مقاومت تقریبی یک الکترود قائم منفرد را تخمین می‌زند.
        - اثر متقابل الکترودها، هادی‌های مدفون، الکترود فونداسیونی، لایه‌بندی خاک و تغییرات فصلی مدل نشده‌اند.
        - ولتاژ گام و تماس، افزایش پتانسیل زمین (GPR)، جریان خطا و زمان قطع حفاظت محاسبه نمی‌شوند.
        - خطوط بین نقاط صرفاً راهنمای بصری هستند؛ اتصال واقعی باید در مدل جداگانه تعریف شود.
        - برای طراحی پست، ارزیابی گام/تماس یا انطباق با IEEE Std 80، تحلیل معتبر و داده‌های پروژه لازم است.

        **پیشنهاد روند کار:** ابتدا مقاومت ویژه خاک را با روش مناسب اندازه‌گیری و مدل خاک را تعیین کن؛ سپس هندسه، جریان خطا، زمان قطع و معیارهای ایمنی را وارد یک فرایند طراحی و اعتبارسنجی‌شده کن.
        """
    )

st.divider()
st.caption("GroundStudio • نسخه مقدماتی • نتایج صرفاً تخمینی‌اند و جایگزین مطالعه مهندسی و بررسی استاندارد نیستند.")
