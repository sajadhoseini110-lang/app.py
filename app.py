import streamlit as st
import math
from earthing_calc import calculate_equivalent_resistance
from pattern_input import pattern_canvas

st.set_page_config(page_title="طراحی زمین", layout="wide")

st.title("⚡ محاسبه‌گر مقاومت زمین")
st.markdown("آرایش الکترودها را روی بوم انتخاب کنید و مقاومت معادل را محاسبه کنید.")

# ================= سایدبار =================
with st.sidebar:
    st.header("تنظیمات خاک و الکترود")
    rho = st.number_input("مقاومت ویژه خاک ρ (Ω·m)", value=100.0, step=10.0)
    
    st.subheader("میله‌های عمودی")
    rod_L = st.number_input("طول میله L (m)", value=3.0, step=0.5)
    rod_d = st.number_input("قطر میله d (m)", value=0.016, step=0.001, format="%.3f")
    
    st.subheader("نوار اتصال افقی (اختیاری)")
    use_strip = st.checkbox("افزودن نوار افقی")
    if use_strip:
        strip_L = st.number_input("طول کل نوار (m)", value=20.0)
        strip_w = st.number_input("عرض نوار (m)", value=0.04, step=0.01)

# ================= بخش بوم =================
st.subheader("۱. آرایش الکترودها را انتخاب کنید")
st.info("روی نقاط شبکه کلیک کنید تا الکترودها را (شبیه الگوی قفل گوشی) بچینید. هر نقطه نماینده یک میله است.")
selected_points = pattern_canvas(key="canvas1")

n_rods = len(selected_points)
spacing = 3.0 # فاصله فرضی پیش‌فرض

if n_rods > 0:
    st.success(f"شما {n_rods} الکترود را انتخاب کرده‌اید.")
    
    # محاسبه فاصله متوسط اگر بیش از یک نقطه انتخاب شده باشد
    if n_rods > 1:
        coords = [list(map(int, p.split(','))) for p in selected_points]
        distances = []
        for i in range(len(coords)):
            for j in range(i+1, len(coords)):
                # فاصله اقلیدسی روی شبکه
                dist = math.sqrt((coords[i][0] - coords[j][0])**2 + (coords[i][1] - coords[j][1])**2)
                distances.append(dist)
        if distances:
            avg_grid_dist = sum(distances) / len(distances)
            # فرض: هر خانه شبکه 1 متر است
            spacing = max(avg_grid_dist, 1.0) 
            st.write(f"میانگین فاصله الکترودها روی بوم: {spacing:.2f} متر")

    # ================= دکمه محاسبه =================
    if st.button("محاسبه مقاومت معادل", type="primary"):
        with st.spinner("در حال محاسبه..."):
            results = calculate_equivalent_resistance(
                rho=rho, rod_L=rod_L, rod_d=rod_d, n_rods=n_rods, spacing_m=spacing,
                strip_L=strip_L if use_strip else 0,
                strip_w=strip_w if use_strip else 0
            )
            
            st.header("📊 نتایج")
            col1, col2, col3 = st.columns(3)
            
            if results["R_rods"] > 0:
                col1.metric("مقاومت میله‌ها", f"{results['R_rods']:.2f} Ω")
            if results["R_strip"] > 0:
                col2.metric("مقاومت نوار افقی", f"{results['R_strip']:.2f} Ω")
            
            col3.metric("مقاومت معادل کل", f"{results['R_eq']:.2f} Ω")
            
            if results["R_eq"] > 10:
                st.warning("مقاومت بالای 10 اهم است. توصیه می‌شود تعداد الکترودها یا طول میله را افزایش دهید.")
            else:
                st.success("مقاومت در محدوده قابل قبول است.")

else:
    st.warning("لطفاً حداقل یک الکترود را روی بوم انتخاب کنید.")