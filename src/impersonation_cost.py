"""Handle-time cost of undisclosed automated callers, under the reader's own assumptions.

This module is the single source of truth for the calculator published at
`impersonation-cost.html`: the arithmetic, the field labels, the input bounds,
the placeholder defaults, and the disclaimer sentence. The page is generated
from here by `scripts/build_impersonation_calculator.py`, so the browser cannot
drift from the model, and `tests/test_impersonation_calculator_page.py` fails if
the committed page stops matching a fresh render.

## What it computes, and what it does not

Given four numbers the reader supplies, it reports the staffed time, and the
cost of that time, spent holding calls that -- *under the reader's assumed
share* -- come from automated callers that never disclosed themselves.

It does not estimate a saving. The cost is carried whether or not those callers
disclose; disclosure changes who the staff knows they are talking to, not the
length of the call. Anyone reading the output as "what NHID-Clinical would save
us" has read it wrong, and `tests/test_impersonation_cost.py` keeps the saving,
recovery and ROI vocabulary out of the labels so the page cannot drift into
implying it.

Nor is any input a figure this project has established. `docs/claim-boundaries.md`
puts NHID-Clinical at the **Research** stage: there is an open reference
implementation and its tests, and no measurement of live payer traffic. The
defaults below are round placeholders that exist to demonstrate the arithmetic,
chosen for being obviously arbitrary rather than for resembling any real call
centre. `DISCLAIMER` says so on the page, and the repo's number-drift guard
(`scripts/check_number_drift.py`) exists because stale published figures are a
recurring failure here -- a calculator that published an industry number as
fact would be exactly that failure with extra steps.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

#: Stated verbatim on the page, next to every figure it produces.
DISCLAIMER = (
    "These figures are user-supplied assumptions. "
    "NHID-Clinical has not measured them on live traffic."
)

MINUTES_PER_HOUR = 60
MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class Field:
    """One number on the page: what it is called, and how it is written out."""
    name: str
    label: str
    unit: str = ""
    #: Decimal places when rendered. Money gets 2; a count of calls gets 1,
    #: because a share of a volume is legitimately fractional and rounding it
    #: to a whole call would imply a precision the assumption has not got.
    places: int = 0
    money: bool = False
    help: str = ""
    default: float = 0.0
    minimum: float = 0.0
    maximum: float | None = None
    step: float = 1.0


INPUTS: Tuple[Field, ...] = (
    Field(
        name="monthly_inbound_calls",
        label="Inbound calls a month",
        unit="calls",
        places=0,
        help="Every inbound call the line takes in a month, human and automated alike.",
        default=10_000,
        minimum=0,
        maximum=10_000_000,
        step=100,
    ),
    Field(
        name="average_hold_minutes",
        label="Average hold time per call",
        unit="minutes",
        places=1,
        help="Time a caller spends holding, before and during the call.",
        default=4.0,
        minimum=0,
        maximum=240,
        step=0.5,
    ),
    Field(
        name="undisclosed_share",
        label="Assumed share of callers that are undisclosed automated agents",
        unit="percent",
        places=1,
        help=(
            "Your assumption, not a finding. Nobody can currently count these "
            "callers, which is the gap the disclosure controls address."
        ),
        default=10.0,
        minimum=0,
        maximum=100,
        step=0.5,
    ),
    Field(
        name="cost_per_staffed_hour",
        label="Loaded cost of a staffed hour",
        unit="dollars per hour",
        places=2,
        money=True,
        help="Wages plus benefits, tooling and overhead, per hour of staffed time.",
        default=45.00,
        minimum=0,
        maximum=1_000,
        step=1.0,
    ),
)

FIELDS: Tuple[Field, ...] = (
    Field("undisclosed_calls_per_month",
          "Calls a month from undisclosed agents, under your assumption",
          unit="calls", places=1),
    Field("hold_minutes_per_month", "Hold minutes a month on those calls",
          unit="minutes", places=1),
    Field("hold_hours_per_month", "Staffed hours a month on those calls",
          unit="hours", places=1),
    Field("monthly_cost", "Handle-time cost a month", unit="dollars",
          places=2, money=True),
    Field("annual_cost", "Handle-time cost a year", unit="dollars",
          places=2, money=True),
)


@dataclass(frozen=True)
class Assumptions:
    """The four numbers the reader supplies. `undisclosed_share` is a fraction.

    The page collects the share as a percentage because that is how a reader
    thinks about it; the conversion happens at the edge so the model only ever
    handles one representation.
    """
    monthly_inbound_calls: float
    average_hold_minutes: float
    undisclosed_share: float
    cost_per_staffed_hour: float


@dataclass(frozen=True)
class Estimate:
    undisclosed_calls_per_month: float
    hold_minutes_per_month: float
    hold_hours_per_month: float
    monthly_cost: float
    annual_cost: float


def estimate(assumptions: Assumptions) -> Estimate:
    """Four assumptions in, five derived figures out.

    Raises `ValueError` rather than returning a number for an impossible
    assumption: a negative volume or a share above 100% is a typo, and
    computing it would put a figure on the page that no reading of the inputs
    supports.
    """
    a = assumptions
    if a.monthly_inbound_calls < 0:
        raise ValueError("monthly_inbound_calls cannot be negative")
    if a.average_hold_minutes < 0:
        raise ValueError("average_hold_minutes cannot be negative")
    if not 0 <= a.undisclosed_share <= 1:
        raise ValueError("undisclosed_share is a fraction between 0 and 1")
    if a.cost_per_staffed_hour < 0:
        raise ValueError("cost_per_staffed_hour cannot be negative")

    calls = a.monthly_inbound_calls * a.undisclosed_share
    minutes = calls * a.average_hold_minutes
    hours = minutes / MINUTES_PER_HOUR
    monthly = hours * a.cost_per_staffed_hour
    return Estimate(
        undisclosed_calls_per_month=calls,
        hold_minutes_per_month=minutes,
        hold_hours_per_month=hours,
        monthly_cost=monthly,
        annual_cost=monthly * MONTHS_PER_YEAR,
    )
