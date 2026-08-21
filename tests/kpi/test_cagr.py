from src.analytics.cagr import calculate_cagr


def test_cagr_normal_growth():
    cagr, flag = calculate_cagr(100, 150, 5)

    assert cagr is not None
    assert flag is None
    assert round(cagr, 2) == 8.45


def test_cagr_decline_to_loss():
    cagr, flag = calculate_cagr(100, -20, 5)

    assert cagr is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_turnaround():
    cagr, flag = calculate_cagr(-20, 100, 5)

    assert cagr is None
    assert flag == "TURNAROUND"


def test_cagr_both_negative():
    cagr, flag = calculate_cagr(-20, -30, 5)

    assert cagr is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_zero_base():
    cagr, flag = calculate_cagr(0, 100, 5)

    assert cagr is None
    assert flag == "ZERO_BASE"


def test_cagr_insufficient_years():
    cagr, flag = calculate_cagr(100, 150, 0)

    assert cagr is None
    assert flag == "INSUFFICIENT"