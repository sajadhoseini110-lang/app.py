import math

import earthing_calc as ec


def test_single_rod_matches_formula():
    r = ec.rod_self_resistance(100, 3, 0.016)
    assert abs(r - 100 / (2 * math.pi * 3) * (math.log(8 * 3 / 0.016) - 1)) < 1e-9


def test_far_rods_are_independent():
    g = ec.group_resistance(100, 3, 0.016, [(0, 0), (1e5, 0)])
    assert abs(g.r_eq - g.r_single / 2) / g.r_single < 1e-3


def test_mutual_far_field_limit():
    r12 = ec.rod_mutual_resistance(100, 3, 500)
    assert abs(r12 - 100 / (2 * math.pi * 500)) / r12 < 1e-3


def test_equipotential_not_above_equal_current():
    g = ec.group_resistance(350, 2.4, 0.016, ec.EXAMPLE_BOOK)
    assert g.r_eq <= g.r_avg + 1e-9
    assert abs(g.shares.sum() - 1) < 1e-9


def test_schwarz_without_rods_equals_r1():
    r = ec.schwarz_resistance(100, 10, 10, 40, 0.6, 0.01, 0, 3, 0.016)
    assert r["Rg"] == r["R1"]
