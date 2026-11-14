"""The impersonation handle-time model: arithmetic, bounds, and what it refuses to claim.

`src/impersonation_cost.py` backs the calculator on `impersonation-cost.html`.
Every figure it produces is derived from four numbers the reader supplies, and
the project has measured none of them on live traffic (`docs/claim-boundaries.md`
puts NHID-Clinical at the **Research** stage). So this file tests two things that
are equally load-bearing:

1. The arithmetic. Expected values below were worked out by hand from the stated
   assumptions, not by running the module, so a test can disagree with the code.
2. The claim boundary. The model must not describe its output as a saving, a
   recovery, or a measured figure, and it must carry the disclaimer sentence
   verbatim. A calculator that implies NHID-Clinical *saves* a payer this money
   would be asserting a result no pilot has produced.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.impersonation_cost import (  # noqa: E402
    DISCLAIMER,
    Assumptions,
    estimate,
)


def test_a_worked_example_in_round_numbers():
    """40,000 calls, a fifth undisclosed, 4.5 min each, $38 a staffed hour.

    By hand: 40,000 x 0.20 = 8,000 calls; 8,000 x 4.5 = 36,000 minutes;
    36,000 / 60 = 600 hours; 600 x 38 = $22,800 a month; x 12 = $273,600.
    """
    out = estimate(Assumptions(40_000, 4.5, 0.20, 38.00))
    assert out.undisclosed_calls_per_month == pytest.approx(8_000)
    assert out.hold_minutes_per_month == pytest.approx(36_000)
    assert out.hold_hours_per_month == pytest.approx(600)
    assert out.monthly_cost == pytest.approx(22_800.00)
    assert out.annual_cost == pytest.approx(273_600.00)


def test_a_worked_example_with_fractional_intermediates():
    """12,500 calls, 7.5% undisclosed, 3 min each, $52 a staffed hour.

    By hand: 937.5 calls; 2,812.5 minutes; 46.875 hours; $2,437.50 a month;
    $29,250 a year. The fractional call count is kept rather than rounded --
    rounding a rate-times-volume estimate at an intermediate step is how a
    model acquires precision it has not got.
    """
    out = estimate(Assumptions(12_500, 3.0, 0.075, 52.00))
    assert out.undisclosed_calls_per_month == pytest.approx(937.5)
    assert out.hold_minutes_per_month == pytest.approx(2_812.5)
    assert out.hold_hours_per_month == pytest.approx(46.875)
    assert out.monthly_cost == pytest.approx(2_437.50)
    assert out.annual_cost == pytest.approx(29_250.00)


def test_a_worked_example_where_every_assumption_is_at_its_extreme():
    """100 calls, all of them undisclosed, an hour on hold, $60 a staffed hour.

    By hand: 100 calls; 6,000 minutes; 100 hours; $6,000 a month; $72,000.
    """
    out = estimate(Assumptions(100, 60.0, 1.0, 60.00))
    assert out.undisclosed_calls_per_month == pytest.approx(100)
    assert out.hold_hours_per_month == pytest.approx(100)
    assert out.monthly_cost == pytest.approx(6_000.00)
    assert out.annual_cost == pytest.approx(72_000.00)


def test_a_single_call_at_half_a_minute_of_staffed_time():
    """1 call, half undisclosed, 1 min hold, $120 a staffed hour.

    By hand: 0.5 calls; 0.5 minutes; 1/120 of an hour; 120 / 120 = $1.00 a
    month; $12.00 a year. Chosen because the hour figure is not representable
    exactly, so a model that rounded hours before multiplying would miss.
    """
    out = estimate(Assumptions(1, 1.0, 0.5, 120.00))
    assert out.monthly_cost == pytest.approx(1.00)
    assert out.annual_cost == pytest.approx(12.00)


def test_zero_anywhere_zeroes_the_cost():
    for assumptions in (
        Assumptions(0, 4.5, 0.20, 38.00),
        Assumptions(40_000, 0.0, 0.20, 38.00),
        Assumptions(40_000, 4.5, 0.0, 38.00),
        Assumptions(40_000, 4.5, 0.20, 0.0),
    ):
        assert estimate(assumptions).monthly_cost == 0
        assert estimate(assumptions).annual_cost == 0


@pytest.mark.parametrize(
    "assumptions",
    [
        Assumptions(-1, 4.5, 0.20, 38.00),
        Assumptions(40_000, -0.1, 0.20, 38.00),
        Assumptions(40_000, 4.5, -0.01, 38.00),
        Assumptions(40_000, 4.5, 1.01, 38.00),
        Assumptions(40_000, 4.5, 0.20, -1.0),
    ],
)
def test_an_impossible_assumption_is_refused_rather_than_computed(assumptions):
    """A share above 1 or a negative volume is a typo, not a scenario.

    Returning a number for it would publish a figure no reading of the inputs
    supports.
    """
    with pytest.raises(ValueError):
        estimate(assumptions)


def test_the_disclaimer_is_the_sentence_that_was_agreed():
    assert DISCLAIMER == (
        "These figures are user-supplied assumptions. "
        "NHID-Clinical has not measured them on live traffic."
    )


def test_the_model_never_describes_its_output_as_a_saving_or_a_measurement():
    """The output is a cost carried under an assumption, not a benefit.

    `monthly_cost` is the handle time spent on calls the reader *assumes* come
    from undisclosed automated callers. It is not an amount disclosure would
    recover, and nothing here has been measured, so the vocabulary of saving,
    recovery, ROI and measurement stays out of the field names and labels.
    """
    import src.impersonation_cost as model

    forbidden = ("saving", "savings", "saved", "recover", "roi", "measured",
                 "benefit", "payback", "guarantee")
    surface = " ".join(
        [f.name for f in model.FIELDS]
        + [f.label for f in model.FIELDS]
        + [f.name for f in model.INPUTS]
        + [f.label for f in model.INPUTS]
    ).lower()
    found = [word for word in forbidden if word in surface]
    assert not found, f"the model's own labels claim {found}"
