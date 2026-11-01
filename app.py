import streamlit as st
import math
from pattern_input import pattern_canvas

st.set_page_config(page_title="طراحی زمین - استاندارد BS 7430", layout="wide")

st.title("⚡ محاسبه‌گر دقیق مقاومت زمین")
st.markdown("ترسیم آرایش الکترودها (مشابه مثال‌های استاندارد BS 7430)")

# ================= سایدبار =================
with st.sidebar:
    st.header("۱. پارامترهای خاک و میله")
    rho = st.number_input("مقاومت ویژه خاک ρ (Ω·m)", value=350.0, step=10.0)
    rod_L = st.number_input("عمق میله L (m)", value=2.4, step=0.1)
    rod_d = st.number_input("قطر میله d (m)", value=0.016, step=0.001, format="%.3f")
    
    st.header("۲. تنظیمات مقیاس")
    st.info("برای تبدیل پیکسل به متر، تعداد پیکسل‌های معادل ۱ متر را وارد کنید.")
    pixels_per_meter = st.number_input("مقیاس (پیکسل در هر ۱ متر)", value=50.0, min_value=10.0, step=10.0)

# ================= بوم =================
st.subheader("بوم ترسیم")
st.info("💡 با ابزار «میله» روی بوم کلیک کنید. با ابزار «تسمه» کلیک کرده و ماوس/انگشت را بکشید تا خطوط اتصال رسم شوند.")
canvas_data = pattern_canvas()

# استخراج داده‌ها
rods = [obj for obj in canvas_data if obj['type'] == 'rod']
wires = [obj for obj in canvas_data if obj['type'] == 'wire']

col_info1, col_info2 = st.columns(2)
col_info1.metric("تعداد میله‌های ترسیم شده", len(rods))
col_info2.metric("طول کل تسمه‌ها (خطوط)", f"{len(wires)} خط")

if len(rods) > 0:
    # --- محاسبه فاصله‌ها ---
    distances = []
    min_spacing = 0
    avg_spacing = 0
    
    if len(rods) > 1:
        # پیدا کردن نزدیک‌ترین همسایه برای هر میله
        min_distances_per_rod = []
        for i in range(len(rods)):
            closest_dist = float('inf')
            for j in range(len(rods)):
                if i == j: continue
                px_dist = math.sqrt((rods[i]['x'] - rods[j]['x'])**2 + (rods[i]['y'] - rods[j]['y'])**2)
                m_dist = px_dist / pixels_per_meter
                distances.append(m_dist)
                if m_dist < closest_dist:
                    closest_dist = m_dist
            min_distances_per_rod.append(closest_dist)
        
        min_spacing = min(distances)
        avg_spacing = sum(distances) / len(distances)
        
        st.write(f"🔹 میانگین فاصله میله‌ها: **{avg_spacing:.2f} متر**")
        st.write(f"🔹 نزدیک‌ترین فاصله (s در فرمول): **{min_spacing:.2f} متر**")

    # ================= دکمه محاسبه =================
    if st.button("محاسبه مقاومت معادل", type="primary", use_container_width=True):
        n = len(rods)
        
        # 1. محاسبه مقاومت میله‌ها (فرمول BS 7430)
        if n == 1:
            R_rods = (rho / (2 * math.pi * rod_L)) * (math.log(8 * rod_L / rod_d) - 1)
        else:
            # استفاده از فاصله نزدیک‌ترین میله برای فرمول موازی
            s = max(min_spacing, 1.0) 
            lambda_f = 2 * math.log((1.781 * n) / 2.718)
            term = math.log(8 * rod_L / rod_d) - 1 + (lambda_f * rod_L / s)
            R_rods = (rho / (2 * math.pi * rod_L * n)) * term

        # 2. محاسبه مقاومت تسمه (اگر کشیده شده باشد)
        total_wire_px = 0
        for w in wires:
            px_len = math.sqrt((w['x2'] - w['x1'])**2 + (w['y2'] - w['y1'])**2)
            total_wire_px += px_len
        
        total_wire_m = total_wire_px / pixels_per_meter
        R_wire = 0
        
        if total_wire_m > 0:
            d_eq = 0.02 # فرض عرض تسمه 2 سانتی‌متر
            R_wire = (rho / (2 * math.pi * total_wire_m)) * math.log((total_wire_m**2) / (1.85 * 0.6 * d_eq))

        # 3. ترکیب نهایی (موازی)
        if R_rods > 0 and R_wire > 0:
            R_eq = (1 / ((1 / R_rods) + (1 / R_wire))) / 0.85 # ضریب اصلاح
        else:
            R_eq = R_rods if R_rods > 0 else R_wire

        st.header("📊 نتایج محاسبات")
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("مقاومت میله‌ها", f"{R_rods:.2f} Ω")
        if R_wire > 0:
            res_col2.metric("مقاومت تسمه‌ها", f"{R_wire:.2f} Ω", help=f"طول کل: {total_wire_m:.1f} متر")
        res_col3.metric("مقاومت معادل کل", f"{R_eq:.2f} Ω", delta_color="inverse")
        
        if R_eq <= 10:
            st.success("✅ مقاومت سیستم زمین در محدوده مجاز (زیر ۱۰ اهم) است.")
        else:
            st.warning("⚠️ مقاومت بالاتر از ۱۰ اهم است. توصیه می‌شود طول میله‌ها یا تعداد آن‌ها را افزایش دهید.")

else:
    st.info("برای شروع، با ابزار «میله» روی بوم کلیک کنید.")
