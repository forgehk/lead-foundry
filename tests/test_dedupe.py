"""Tests for the dedupe stage."""

from lead_foundry.dedupe import completeness, dedupe_by_domain
from lead_foundry.models import Lead

def test_completeness_counts_nonempty():
    assert completeness(Lead()) == 0
    assert completeness(Lead(email="x@y.com")) == 1
    assert completeness(Lead(email="x@y.com", phone="+1...", company="X")) == 3

def test_dedupe_keeps_more_complete():
    a = Lead(email="m@calmwell.io", domain="calmwell.io")
    b = Lead(
        email="m@calmwell.io", domain="calmwell.io",
        first_name="Maya", last_name="Patel", company="CalmWell"
    )
    out = dedupe_by_domain([a, b])
    assert len(out) == 1
    assert out[0].first_name == "Maya"

def test_dedupe_preserves_no_domain():
    a = Lead(email="m@calmwell.io", domain="calmwell.io")
    b = Lead(first_name="Anonymous")
    out = dedupe_by_domain([a, b])
    assert len(out) == 2
