"""Field-level normalization."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import Lead

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)

def normalize_email(raw: str) -> str:
    """Lowercase, strip, validate basic shape; gmail dots/aliases preserved (not collapsed)."""
    if not raw:
        return ""
    e = raw.strip().lower()
    # collapse whitespace
    e = re.sub(r"\s+", "", e)
    if not EMAIL_RE.match(e):
        return ""
    return e

def normalize_phone(raw: str, default_country: str = "1") -> str:
    """Best-effort E.164. Strip everything non-digit; prepend country code if missing.

    For US numbers (10 digits) this works perfectly. For other countries the
    user can pre-format with a leading '+' and we won't add a duplicate code.
    """
    if not raw:
        return ""
    digits = re.sub(r"[^\d+]", "", raw)
    if not digits:
        return ""
    if digits.startswith("+"):
        return digits
    # bare digits
    if len(digits) == 10 and default_country == "1":
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1") and default_country == "1":
        return "+" + digits
    # otherwise assume already country-prefixed
    return "+" + digits

def normalize_name(raw: str) -> str:
    if not raw:
        return ""
    # collapse whitespace, title-case but preserve common particles
    parts = [p for p in re.split(r"\s+", raw.strip()) if p]
    return " ".join(_titlecase_piece(p) for p in parts)

def _titlecase_piece(p: str) -> str:
    # don't title-case McX/MacX style names: keep first letter cap and rest preserved
    if len(p) > 2 and p[:2].lower() == "mc":
        return "Mc" + p[2:].capitalize()
    if len(p) > 3 and p[:3].lower() == "mac":
        return "Mac" + p[3:].capitalize()
    return p[:1].upper() + p[1:].lower()

def extract_domain(email_or_url: str) -> str:
    if not email_or_url:
        return ""
    s = email_or_url.strip().lower()
    if "@" in s:
        s = s.rsplit("@", 1)[1]
    elif "://" in s:
        s = urlparse(s).netloc or s
    # strip www.
    if s.startswith("www."):
        s = s[4:]
    # strip path
    s = s.split("/")[0].split("?")[0].split("#")[0]
    return s

def normalize_country(raw: str) -> str:
    """Map common variations to ISO-3166 alpha-2."""
    if not raw:
        return ""
    s = raw.strip().lower()
    mapping = {
        "us": "US", "usa": "US", "u.s.": "US", "u.s.a.": "US",
        "united states": "US", "united states of america": "US", "america": "US",
        "uk": "GB", "united kingdom": "GB", "great britain": "GB", "england": "GB",
        "canada": "CA", "ca": "CA",
        "mexico": "MX", "mx": "MX",
        "germany": "DE", "de": "DE", "deutschland": "DE",
        "france": "FR", "fr": "FR",
        "japan": "JP", "jp": "JP",
        "china": "CN", "cn": "CN",
    }
    if s in mapping:
        return mapping[s]
    # already alpha-2?
    if len(s) == 2 and s.isalpha():
        return s.upper()
    return raw.strip()

def normalize_lead(lead: Lead) -> Lead:
    """Apply all field normalizers to a lead in-place and return it."""
    lead.email = normalize_email(lead.email)
    lead.phone = normalize_phone(lead.phone)
    lead.first_name = normalize_name(lead.first_name)
    lead.last_name = normalize_name(lead.last_name)
    lead.country = normalize_country(lead.country)

    # derive domain if missing
    if not lead.domain:
        lead.domain = extract_domain(lead.email or lead.website)
    else:
        lead.domain = extract_domain(lead.domain)

    return lead
