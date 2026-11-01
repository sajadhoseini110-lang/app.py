"""
earthing_calc.py - هسته محاسباتی (بدون وابستگی به Streamlit، قابل تست)

روش اصلی برای گروه میله‌ها (آرایش دلخواه):
  - مقاومت شخصی هر میله: R11 = ρ/(2πL)·(ln(8L/d) − 1)      [BS 7430 / Dwight]
  - مقاومت متقابل دو میله موازی هم‌طول (جریان یکنواخت، نیم‌فضا با تصویر آینه‌ای): انتگرال تحلیلی
  - اتصال موازی میله‌ها (هم‌پتانسیل): R_eq = 1 / (1ᵀ Z⁻¹ 1)
    این روش توزیع نابرابر جریان بین میله‌ها (میله‌های گوشه جریان بیشتری می‌گیرند) را هم لحاظ می‌کند.
  - برای مقایسه، روش ساده میانگین‌گیری (فرض جریان برابر و مقاومت متقابل میدان دور ρ/2πd)
    که معادل فرم ضریب λ در BS 7430 است نیز گزارش می‌شود.
معادلات Schwarz (IEEE Std 80) برای شبکه افقی + میله، با ضرایب k1,k2 به روش Sverak.

محدودیت‌ها: خاک همگن، فرکانس قدرت، میله‌های عمودی هم‌طول و هم‌قطر که از سطح خاک شروع می‌شوند،
اثر هادی افقی رابط بین میله‌ها در نتیجه میله‌ای لحاظ نشده (محافظه‌کارانه).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


class InputError(ValueError):
    """ورودی نامعتبر یا خارج از دامنه اعتبار فرمول."""


SEARCH_LENGTHS = (1.5, 2.4, 3.0, 4.5, 6.0, 9.0, 12.0)


# ------------------------------------------------------------
# میله‌ها
# ------------------------------------------------------------
def rod_self_resistance(rho: float, length: float, diameter: float) -> float:
    """R = ρ/(2πL)·(ln(8L/d) − 1)،  d = قطر (m)."""
    if rho <= 0 or length <= 0 or diameter <= 0:
        raise InputError("ρ، طول و قطر میله باید مثبت باشند.")
    if length <= 4 * diameter:
        raise InputError("طول میله باید از چهار برابر قطر بزرگ‌تر باشد.")
    return rho / (2 * math.pi * length) * (math.log(8 * length / diameter) - 1)


def _mutual_array(rho: float, length: float, dist: np.ndarray) -> np.ndarray:
    """مقاومت متقابل دو میله موازی هم‌طول L با فاصله dist (جریان یکنواخت، نیم‌فضا)."""
    s = np.asarray(dist, dtype=float)
    a1 = np.arcsinh(length / s)
    a2 = np.arcsinh(2 * length / s)
    h1 = np.hypot(length, s)
    h2 = np.hypot(2 * length, s)
    i1 = 2 * (length * a1 - h1 + s)
    i2 = 2 * h1 - s - h2 + 2 * length * (a2 - a1)
    return rho / (4 * math.pi * length**2) * (i1 + i2)


def rod_mutual_resistance(rho: float, length: float, distance: float) -> float:
    if distance <= 0:
        raise InputError("فاصله باید مثبت باشد.")
    return float(_mutual_array(rho, length, np.array(distance)))


@dataclass
class GroupResult:
    n: int
    r_single: float
    r_eq: float           # اتصال هم‌پتانسیل (روش اصلی)
    r_avg: float          # فرض جریان برابر با مقاومت متقابل دقیق
    r_simple: float       # روش ساده BS 7430 (میدان دور، جریان برابر)
    eta: float            # ضریب بهره‌وری = R_single / (n · R_eq)
    shares: np.ndarray    # سهم جریان هر میله (مجموع = 1)
    min_spacing: float


def _distance_matrix(xy: np.ndarray) -> np.ndarray:
    diff = xy[:, None, :] - xy[None, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def group_resistance(
    rho: float, length: float, diameter: float, pts: list[tuple[float, float]]
) -> GroupResult:
    xy = np.asarray(pts, dtype=float)
    n = len(xy)
    if n < 1:
        raise InputError("حداقل یک میله لازم است.")
    r_self = rod_self_resistance(rho, length, diameter)
    if n == 1:
        return GroupResult(1, r_self, r_self, r_self, r_self, 1.0, np.array([1.0]), float("inf"))

    dist = _distance_matrix(xy)
    off = ~np.eye(n, dtype=bool)
    min_s = float(dist[off].min())
    if min_s <= diameter:
        raise InputError("فاصله دو میله از قطر میله کمتر یا برابر است (میله‌ها روی هم افتاده‌اند).")

    safe = np.where(off, dist, 1.0)
    z = np.where(off, _mutual_array(rho, length, safe), r_self)
    try:
        current = np.linalg.solve(z, np.ones(n))
    except np.linalg.LinAlgError as exc:
        raise InputError("ماتریس مقاومت منفرد شد؛ چیدمان را بازبینی کنید.") from exc
    r_eq = 1.0 / current.sum()
    r_avg = float(z.sum() / n**2)
    r_simple = r_self / n + rho / (2 * math.pi) * float((1.0 / safe[off]).sum()) / n**2
    eta = r_self / (n * r_eq)
    return GroupResult(n, r_self, r_eq, r_avg, r_simple, eta, current / current.sum(), min_s)


# ------------------------------------------------------------
# چیدمان‌ها
# ------------------------------------------------------------
def layout_line(n: int, s: float) -> list[tuple[float, float]]:
    return [(i * s, 0.0) for i in range(n)]


def layout_ring(n: int, side: float) -> list[tuple[float, float]]:
    """رئوس n‌ضلعی منتظم با ضلع side (n≥3)."""
    if n < 3:
        return layout_line(n, side)
    r = side / (2 * math.sin(math.pi / n))
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def layout_grid(rows: int, cols: int, sx: float, sy: float) -> list[tuple[float, float]]:
    return [(j * sx, i * sy) for i in range(rows) for j in range(cols)]


def layout_perimeter(lx: float, ly: float, n: int) -> list[tuple[float, float]]:
    """n میله هم‌فاصله روی محیط مستطیل lx × ly."""
    p = 2 * (lx + ly)
    pts = []
    for k in range(n):
        t = k * p / n
        if t < lx:
            pts.append((t, 0.0))
        elif t < lx + ly:
            pts.append((lx, t - lx))
        elif t < 2 * lx + ly:
            pts.append((lx - (t - lx - ly), ly))
        else:
            pts.append((0.0, ly - (t - 2 * lx - ly)))
    return pts


# مثال ۳-۱۲ کتاب: ۹ میله، مربع ۴ متری + ردیف با فاصله ۳٫۶ متر
EXAMPLE_BOOK = [
    (0.0, 0.0), (4.0, 0.0), (7.6, 0.0), (11.2, 0.0), (14.8, 0.0), (18.4, 0.0), (22.0, 0.0),
    (0.0, -4.0), (4.0, -4.0),
]


# ------------------------------------------------------------
# Schwarz / IEEE 80 (شبکه افقی + میله)
# ------------------------------------------------------------
_DEPTH_POINTS = (0.0, 0.1, 1 / 6)


def _k_at(point: int, x: float) -> tuple[float, float]:
    if point == 0:
        return -0.04 * x + 1.41, 0.15 * x + 5.50
    if point == 1:
        return -0.05 * x + 1.20, 0.10 * x + 4.68
    return -0.05 * x + 1.13, 0.10 * x + 4.40


def schwarz_k_factors(x: float, h: float, area: float) -> tuple[float, float]:
    """ضرایب Sverak؛ x = L/W ≥ 1. نیاز به تأیید با متن IEEE 80 دارد."""
    if x < 1 or h < 0 or area <= 0:
        raise InputError("نسبت ابعاد باید ≥ ۱، عمق ≥ ۰ و مساحت > ۰ باشد.")
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
    if value <= 0:
        raise InputError(f"جمله لگاریتمی {name} غیرمثبت شد؛ پارامترها خارج از دامنه فرمول‌اند.")
    return value


def schwarz_resistance(
    rho: float, grid_len: float, grid_wid: float, conductor_len: float, depth: float,
    conductor_dia: float, n_rods: int, rod_len: float, rod_dia: float,
) -> dict[str, float | None]:
    if min(rho, grid_len, grid_wid, conductor_len, depth, conductor_dia) <= 0:
        raise InputError("همه پارامترهای شبکه باید مثبت باشند.")
    area = grid_len * grid_wid
    sqrt_a = math.sqrt(area)
    x = max(grid_len, grid_wid) / min(grid_len, grid_wid)
    k1, k2 = schwarz_k_factors(x, depth, area)
    a_eq = math.sqrt(conductor_dia / 2 * 2 * depth)
    r1 = rho / (math.pi * conductor_len) * _positive(
        math.log(2 * conductor_len / a_eq) + k1 * conductor_len / sqrt_a - k2, "R1")
    if n_rods == 0:
        return {"R1": r1, "R2": None, "Rm": None, "Rg": r1, "k1": k1, "k2": k2}
    if rod_len <= 4 * rod_dia:
        raise InputError("طول/قطر میله نامعتبر است.")
    b = rod_dia / 2
    r2 = rho / (2 * math.pi * n_rods * rod_len) * _positive(
        math.log(4 * rod_len / b) - 1 + 2 * k1 * rod_len / sqrt_a * (math.sqrt(n_rods) - 1) ** 2, "R2")
    rm = rho / (math.pi * conductor_len) * _positive(
        math.log(2 * conductor_len / rod_len) + k1 * conductor_len / sqrt_a - k2 + 1, "Rm")
    denom = r1 + r2 - 2 * rm
    if denom <= 1e-9:
        raise InputError("مخرج Rg غیرمثبت شد؛ خارج از دامنه اعتبار روش Schwarz.")
    rg = (r1 * r2 - rm**2) / denom
    if rg <= 0:
        raise InputError("Rg غیرفیزیکی شد؛ هندسه ورودی را بازبینی کنید.")
    return {"R1": r1, "R2": r2, "Rm": rm, "Rg": rg, "k1": k1, "k2": k2}


# ------------------------------------------------------------
# جستجوی طرح (مشاور)
# ------------------------------------------------------------
def search_rod_layouts(
    rho: float, diameter: float, lx: float, ly: float, lengths: tuple[float, ...], max_n: int = 40
) -> pd.DataFrame:
    """ارزیابی آرایش‌های خط / محیطی / شبکه مستطیلی برای هر طول میله."""
    rows = []
    long_side = max(lx, ly)

    def add(kind, desc, length, pts):
        try:
            g = group_resistance(rho, length, diameter, pts)
        except InputError:
            return
        rows.append({
            "kind": kind, "desc": desc, "L": length, "n": g.n, "R": g.r_eq,
            "eta": g.eta, "total_len": g.n * length, "s_over_L": g.min_spacing / length,
        })

    for length in lengths:
        add("single", "یک میله", length, [(0.0, 0.0)])
        for n in range(2, max_n + 1):
            add("line", f"روی یک خط، فاصله {long_side / (n - 1):.2f} m", length,
                layout_line(n, long_side / (n - 1)))
        for n in range(4, max_n + 1):
            add("perimeter", f"روی محیط {lx:g}×{ly:g} m", length, layout_perimeter(lx, ly, n))
        for r in range(2, 9):
            for c in range(r, 9):
                add("grid", f"شبکه {r}×{c}، فاصله {lx / (c - 1):.2f}×{ly / (r - 1):.2f} m", length,
                    layout_grid(r, c, lx / (c - 1), ly / (r - 1)))
    return pd.DataFrame(rows)


def search_grid_with_rods(
    rho: float, lx: float, ly: float, depth: float, cond_dia: float, rod_dia: float,
    lengths: tuple[float, ...],
) -> pd.DataFrame:
    """شبکه افقی m×m + میله (Schwarz)."""
    rows = []
    if max(lx, ly) / min(lx, ly) > 8:
        return pd.DataFrame(rows)
    for m in (1, 2, 3, 4, 6):
        lc = (m + 1) * (lx + ly)
        for n_r in (0, 4, 8, 12):
            for length in (lengths if n_r else (None,)):
                try:
                    res = schwarz_resistance(rho, lx, ly, lc, depth, cond_dia, n_r, length or 1.0, rod_dia)
                except InputError:
                    continue
                rows.append({
                    "mesh": m, "Lc": lc, "n": n_r, "L": length or 0.0, "R": res["Rg"],
                    "total_len": lc + n_r * (length or 0.0),
                })
    return pd.DataFrame(rows)


# ------------------------------------------------------------
# مقطع هادی (اتصال کوتاه، روش آدیاباتیک IEC 60949 / BS EN 50522)
# ------------------------------------------------------------
MATERIAL_CONSTANTS = {"مس": (226.0, 234.5), "فولاد": (78.0, 202.0), "آلومینیوم": (148.0, 228.0)}


def min_cross_section(current_a: float, time_s: float, material: str, theta_i: float, theta_f: float) -> float:
    """S[mm²] = I·√t / (K·√ln((θf+β)/(θi+β)))"""
    if current_a <= 0 or time_s <= 0:
        raise InputError("جریان و زمان باید مثبت باشند.")
    if theta_f <= theta_i:
        raise InputError("دمای نهایی باید از دمای اولیه بیشتر باشد.")
    k, beta = MATERIAL_CONSTANTS[material]
    return current_a * math.sqrt(time_s) / (k * math.sqrt(math.log((theta_f + beta) / (theta_i + beta))))
