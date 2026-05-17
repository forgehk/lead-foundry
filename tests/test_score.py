"""Tests for ICP scoring."""

from lead_foundry.models import Lead
from lead_foundry.score import ICP, score_one

ICP_DATA = {
    "name": "test",
    "rules": [
        {"field": "industry", "contains": ["wellness"], "weight": 30},
        {"field": "company_size", "between": [10, 200], "weight": 25},
        {"field": "country", "equals": "US", "weight": 15},
        {"field": "title", "contains": ["founder", "ceo"], "weight": 20},
        {"field": "email", "has_valid_mx": True, "weight": 10},
    ],
    "verdicts": {"hot": 70, "warm": 40},
}

def test_hot_lead():
    icp = ICP.from_dict(ICP_DATA)
    lead = Lead(
        industry="wellness supplements",
        company_size=42,
        country="US",
        title="Founder",
        email="maya@calmwell.io",
    )
    sl = score_one(lead, icp)
    assert sl.score == 100
    assert sl.verdict == "hot"
    assert len(sl.matched_rules) == 5

def test_cold_lead():
    icp = ICP.from_dict(ICP_DATA)
    lead = Lead(industry="industrial manufacturing", company_size=12000, country="US",
                title="Director of Procurement", email="x@bigcorp.com")
    sl = score_one(lead, icp)
    # only country + email match -> 15 + 10 = 25 -> cold (since < warm threshold of 40)
    assert sl.verdict == "cold"

def test_warm_lead():
    icp = ICP.from_dict(ICP_DATA)
    lead = Lead(industry="wellness", company_size=300, country="US",
                title="Director", email="x@example.com")
    sl = score_one(lead, icp)
    # industry (30) + country (15) + email (10) = 55 -> warm
    assert sl.verdict == "warm"
    assert 40 <= sl.score < 70

def test_score_capped_at_100():
    rules = [{"field": "country", "equals": "US", "weight": 80} for _ in range(3)]
    icp = ICP.from_dict({"rules": rules, "verdicts": {"hot": 70, "warm": 40}})
    lead = Lead(country="US")
    sl = score_one(lead, icp)
    assert sl.score == 100
