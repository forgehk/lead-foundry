"""Tests for field-level normalization."""

from lead_foundry.normalize import (
    extract_domain,
    normalize_country,
    normalize_email,
    normalize_lead,
    normalize_name,
    normalize_phone,
)
from lead_foundry.models import Lead

def test_email_basic():
    assert normalize_email("Maya@Example.com") == "maya@example.com"
    assert normalize_email("  user@x.io  ") == "user@x.io"

def test_email_invalid():
    assert normalize_email("not-an-email") == ""
    assert normalize_email("") == ""

def test_phone_us_10_digit():
    assert normalize_phone("(714) 555-0182") == "+17145550182"
    assert normalize_phone("714-555-0182") == "+17145550182"

def test_phone_us_11_digit():
    assert normalize_phone("17145550182") == "+17145550182"

def test_phone_international():
    assert normalize_phone("+49 30 5550022").startswith("+49")

def test_name_titlecase():
    assert normalize_name("MAYA") == "Maya"
    assert normalize_name("maya") == "Maya"
    assert normalize_name("McGee") == "McGee"

def test_country_aliases():
    assert normalize_country("USA") == "US"
    assert normalize_country("united states") == "US"
    assert normalize_country("uk") == "GB"
    assert normalize_country("Germany") == "DE"

def test_extract_domain_from_email():
    assert extract_domain("maya@CalmWell.io") == "calmwell.io"

def test_extract_domain_from_url():
    assert extract_domain("https://www.calmwell.io/about") == "calmwell.io"

def test_normalize_lead_derives_domain():
    lead = Lead(email="x@example.com")
    normalize_lead(lead)
    assert lead.domain == "example.com"
