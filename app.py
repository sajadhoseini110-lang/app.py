import streamlit as st
import math
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="طراحی زمین", layout="wide")

st.title("⚡ محاسبه‌گر دقیق مقاومت زمین")
st.markdown("با استفاده از ابزارهای زیر، میله‌ها و تسمه‌ها را روی بوم ترسیم کنید.")

# ================= سایدبار =================
with st.sidebar:
    st.header("۱. پارامترهای خاک و میله")
    rho = st.number_input("مقاومت ویژه خاک ρ (Ω·m)", value=350.0, step=10.0)
    rod_L = st.number_input("عمق میله L (m)", value=2.4, step=0.1)
    rod_d = st.number_input("قطر میله d (m)", value=0.016, step=0.001, format="%.3f")
    
    st.header("۲. تنظیمات مقیاس")
    st.info("برای تبدیل پیکسل به متر، مقیاس را وارد کنید.")
    pixels_per_meter = st.number_input("مقیاس (پیکسل در هر ۱ متر)", value=50.0, min_value=10.0, step=10.0)
    strip_width_m = st.number_input("عرض تسمه (متر)", value=0.04, step=0.01)

# ================= بوم ترسیم =================
st.subheader("بوم ترسیم")
st.info("💡 برای گذاشتن **میله**، از ابزار دایره (Circle) استفاده کنید. برای کشیدن **تسمه**، از ابزار خط (Line) استفاده کنید.")

# انتخاب ابزار ترسیم
col1, col2 = st.columns(2)
with col1:
    drawing_mode = st.radio("ابزار ترسیم:", ("circle", "line"), horizontal=True, format_func=lambda x: "دایره (میله)" if x == "circle" else "خط (تسمه)")

# رسم بوم
canvas_result = st_canvas(
    fill_color="rgba(255, 0, 0, 0.8)",  # رنگ قرمز برای میله‌ها
    stroke_width=3,
    stroke_color="#000000",            # رنگ مشکی برای خطوط
    background_color="#FFFFFF",        # پس‌زمینه سفید اجباری
    height=400,
    width=700,
    drawing_mode=drawing_mode,
    key="canvas",
)

# ================= پردازش داده‌ها =================
if canvas_result.json_data is not None:
    objects = canvas_result.json_data["objects"]
    
    rods = [obj for obj in objects if obj["type"] == "circle"]
    wires = [obj for obj in objects if obj["type"] == "line"]
    
    col_info1, col_info2 = st.columns(2)
    col_info1.metric("تعداد میله‌ها", len(rods))
    col_info2.metric("تعداد خطوط تسمه", len(wires))

    if len(rods) > 0:
        # استخراج مختصات مرکز میله‌ها
        rod_coords = []
        for r in rods:
            cx = r["left"] + r["radius"]
            cy = r["top"] + r["radius"]
            rod_coords.append((cx, cy))

        # محاسبه فاصله‌ها
        distances = []
        if len(rod_coords) > 1:
            for i in range(len(rod_coords)):
                for j in range(i+1, len(rod_coords)):
                    px_dist = math.sqrt((rod_coords[i][0] - rod_coords[j][0])**2 + (rod_coords[i][1] - rod_coords[j][1])**2)
                    m_dist = px_dist / pixels_per_meter
                    distances.append(m_dist)
            
            min_spacing = min(distances)
            st.write(f"🔹 نزدیک‌ترین فاصله میله‌ها (s): **{min_spacing:.2f} متر**")

        # ================= محاسبه =================
        if st.button("محاسبه مقاومت معادل", type="primary", use_container_width=True):
            n = len(rods)
            
            # 1. مقاومت میله‌ها
            if n == 1:
                R_rods = (rho / (2 * math.pi * rod_L)) * (math.log(8 * rod_L / rod_d) - 1)
            else:
                s = max(min(distances), 1.0) # استفاده از نزدیک‌ترین فاصله
                lambda_f = 2 * math.log((1.781 * n) / 2.718)
                term = math.log(8 * rod_L / rod_d) - 1 + (lambda_f * rod_L / s)
                R_rods = (rho / (2 * math.pi * rod_L * n)) * term

            # 2. مقاومت تسمه (خطوط)
            total_wire_px = 0
            for w in wires:
                # محاسبه طول خط با در نظر گرفتن چرخش
                px_len = math.sqrt((w["x2"] - w["x1"])**2 + (w["y2"] - w["y1"])**2)
                # اگر خط درگ شده باشد، فابریک طول را در scaleX ذخیره می‌کند
                if "scaleX" in w:
                    px_len *= w["scaleX"]
                total_wire_px += px_len
            
            total_wire_m = total_wire_px / pixels_per_meter
            R_wire = 0
            
            if total_wire_m > 0:
                d_eq = strip_width_m / 2
                # جلوگیری از خطای لگاریتمی با بررسی مقدار
                log_arg = (total_wire_m**2) / (1.85 * 0.6 * d_eq)
                if log_arg > 1:
                    R_wire = (rho / (2 * math.pi * total_wire_m)) * math.log(log_arg)
                else:
                    R_wire = (rho / (2 * math.pi * total_wire_m)) * math.log(1.1) # حداقل مقدار

            # 3. ترکیب نهایی
            if R_rods > 0 and R_wire > 0:
                R_eq = (1 / ((1 / R_rods) + (1 / R_wire))) / 0.85
            else:
                R_eq = R_rods if R_rods > 0 else R_wire

            st.header("📊 نتایج محاسبات")
            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("مقاومت میله‌ها", f"{R_rods:.2f} Ω")
            if R_wire > 0:
                res_col2.metric("مقاومت تسمه", f"{R_wire:.2f} Ω", help=f"طول کل: {total_wire_m:.1f} متر")
            res_col3.metric("مقاومت نهایی", f"{R_eq:.2f} Ω")
            
            if R_eq <= 10:
                st.success("✅ مقاومت در محدوده مجاز (زیر ۱۰ اهم) است.")
            else:
                st.warning("⚠️ مقاومت بالای ۱۰ اهم است. طول یا تعداد میله‌ها را افزایش دهید.")
    else:
        st.info("هنوز هیچ میله‌ای ترسیم نکرده‌اید. با ابزار دایره روی بوم کلیک کنید.")