import math

def single_rod_R(rho, L, d):
    """مقاومت یک میله منفرد - BS 7430"""
    if L <= d or d <= 0: return 0.0
    return (rho / (2 * math.pi * L)) * (math.log(8 * L / d) - 1)

def calculate_equivalent_resistance(rho, rod_L, rod_d, n_rods, spacing_m, strip_L=0, strip_w=0, strip_h=0.6):
    """
    محاسبه مقاومت معادل بر اساس فرمول‌های BS 7430
    ورودی‌ها بر حسب متر و اهم-متر هستند.
    """
    R_rods = 0.0
    R_strip = 0.0
    R_eq = 0.0
    
    # 1. محاسبه میله‌های عمودی
    if n_rods > 0:
        if n_rods == 1:
            R_rods = single_rod_R(rho, rod_L, rod_d)
        else:
            # فرمول میله‌های موازی با فاصله (BS 7430 Cl 9.5.4)
            lambda_f = 2 * math.log((1.781 * n_rods) / 2.718)
            term = math.log(8 * rod_L / rod_d) - 1 + (lambda_f * rod_L / spacing_m)
            R_rods = (rho / (2 * math.pi * rod_L * n_rods)) * term

    # 2. محاسبه نوار/سیم افقی (در صورت وجود)
    if strip_L > 0 and strip_w > 0:
        d_eq = strip_w / 2.0
        # جلوگیری از خطای لگاریتمی
        if (strip_L**2) > (1.85 * strip_h * d_eq):
            R_strip = (rho / (2 * math.pi * strip_L)) * math.log((strip_L**2) / (1.85 * strip_h * d_eq))

    # 3. ترکیب (موازی با ضریب اصلاح همپوشانی)
    if R_rods > 0 and R_strip > 0:
        R_parallel = 1 / ((1 / R_rods) + (1 / R_strip))
        R_eq = R_parallel / 0.85  # ضریب محافظه‌کارانه 0.85
    elif R_rods > 0:
        R_eq = R_rods
    elif R_strip > 0:
        R_eq = R_strip

    return {
        "R_rods": R_rods,
        "R_strip": R_strip,
        "R_eq": R_eq
    }