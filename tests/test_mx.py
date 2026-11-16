"""Tests for the live MX check behind `has_valid_mx` (no network needed)."""

import dns.exception
import dns.rdata
import dns.rdataclass
import dns.rdatatype
import dns.resolver
import pytest

from lead_foundry.models import Lead
from lead_foundry.score import ICP, MXChecker, dns_mx_lookup, score_one


def _mx(text):
    return dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.MX, text)


class FakeResolver:
    """Answers from a dict of (domain, rdtype) -> list of records or an exception."""

    def __init__(self, answers):
        self.answers = answers
        self.queries = []

    def resolve(self, domain, rdtype):
        self.queries.append((domain, rdtype))
        result = self.answers.get((domain, rdtype), dns.resolver.NoAnswer())
        if isinstance(result, Exception):
            raise result
        return result


def test_domain_with_mx_is_deliverable():
    r = FakeResolver({("calmwell.io", "MX"): [_mx("10 mx1.calmwell.io.")]})
    assert dns_mx_lookup("calmwell.io", resolver=r) is True


def test_nxdomain_is_not_deliverable():
    r = FakeResolver({("nope.invalid", "MX"): dns.resolver.NXDOMAIN()})
    assert dns_mx_lookup("nope.invalid", resolver=r) is False


def test_null_mx_is_not_deliverable():
    r = FakeResolver({("noreply.example", "MX"): [_mx("0 .")]})
    assert dns_mx_lookup("noreply.example", resolver=r) is False


def test_no_mx_falls_back_to_address_record():
    r = FakeResolver({("peakfit.com", "A"): ["203.0.113.7"]})
    assert dns_mx_lookup("peakfit.com", resolver=r) is True
    assert r.queries == [("peakfit.com", "MX"), ("peakfit.com", "A")]


def test_no_mx_and_no_address_is_not_deliverable():
    r = FakeResolver({})
    assert dns_mx_lookup("parked.example", resolver=r) is False


def test_timeout_is_unknown_not_false():
    r = FakeResolver({("slow.example", "MX"): dns.exception.Timeout()})
    assert dns_mx_lookup("slow.example", resolver=r) is None


def test_checker_caches_per_domain():
    calls = []

    def lookup(domain):
        calls.append(domain)
        return True

    checker = MXChecker(lookup=lookup)
    assert checker.has_mx("CalmWell.io") is True
    assert checker.has_mx("calmwell.io.") is True
    assert calls == ["calmwell.io"]


RULE = {"field": "email", "has_valid_mx": True, "weight": 10}


def test_rule_uses_the_checker_when_mx_lookup_is_on():
    icp = ICP.from_dict({"rules": [RULE], "mx_lookup": True})
    icp.mx_checker = MXChecker(lookup=lambda d: d == "calmwell.io")
    assert score_one(Lead(email="maya@calmwell.io"), icp).score == 10
    assert score_one(Lead(email="x@gone.example"), icp).score == 0


def test_unknown_result_earns_no_points():
    icp = ICP.from_dict({"rules": [RULE]})
    icp.mx_checker = MXChecker(lookup=lambda d: None)
    assert score_one(Lead(email="maya@calmwell.io"), icp).score == 0


def test_bad_shape_never_reaches_dns():
    def lookup(domain):
        pytest.fail("lookup should not run for a malformed email")

    icp = ICP.from_dict({"rules": [RULE]})
    icp.mx_checker = MXChecker(lookup=lookup)
    assert score_one(Lead(email="not-an-email"), icp).score == 0


def test_mx_lookup_is_off_by_default():
    icp = ICP.from_dict({"rules": [RULE]})
    assert icp.mx_checker is None
    assert score_one(Lead(email="maya@calmwell.io"), icp).score == 10
