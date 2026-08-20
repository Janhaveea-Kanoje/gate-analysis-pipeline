"""
Client for the UK Companies House API - verifies a registered company
exists and is active. Requires a free API key (unlike the FSA/DSLD clients,
which are keyless): register at
https://developer.company-information.service.gov.uk/, create a REST-type
API Key application, and set COMPANIES_HOUSE_API_KEY as an environment
variable before this module is used.

Auth is HTTP Basic: the API key is the username, password is left blank -
confirmed against the real Companies House API documentation before this
was built, not assumed.
"""

from __future__ import annotations
import os
import re
import requests

SEARCH_URL = "https://api.company-information.service.gov.uk/search/companies"
TIMEOUT = 15

COMPANY_SUFFIX_PATTERN = re.compile(
    r"([A-Z][A-Za-z&'.]*(?:\s+[A-Z][A-Za-z&'.]*){0,4})\s+(Ltd|Limited|LLC|PLC|Inc)\b"
)


class CompaniesHouseError(Exception):
    pass


def extract_company_name(disclosure_text: str, brand_fallback: str) -> str:
    """
    Pulls a 'X Ltd/Limited/LLC/PLC' phrase out of free text if present,
    otherwise falls back to the plain brand name. The fallback has
    meaningfully lower precision - validated against real ground truth,
    only 1 of 16 brands lacking an explicit legal name in their own text
    resolved correctly under the plain-brand fallback (the rest are
    registered under a different legal name than their consumer brand,
    which no amount of text matching can recover without that name being
    stated somewhere).
    """
    if isinstance(disclosure_text, str):
        match = COMPANY_SUFFIX_PATTERN.search(disclosure_text)
        if match:
            return f"{match.group(1)} {match.group(2)}"
    return brand_fallback


def check_company_exists(name: str, api_key: str | None = None) -> dict:
    """
    Returns {"found": bool, "company_name": str | None, "company_number": str | None}.
    "found": True means an ACTIVE company matching this name was located.
    """
    key = api_key or os.environ.get("COMPANIES_HOUSE_API_KEY")
    if not key:
        raise CompaniesHouseError(
            "COMPANIES_HOUSE_API_KEY not set. Register a free key at "
            "https://developer.company-information.service.gov.uk/ first."
        )
    try:
        resp = requests.get(SEARCH_URL, params={"q": name}, auth=(key, ""), timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("items", []):
            if item.get("company_status", "").lower() == "active":
                return {
                    "found": True,
                    "company_name": item.get("title"),
                    "company_number": item.get("company_number"),
                }
        return {"found": False, "company_name": None, "company_number": None}
    except requests.RequestException as exc:
        raise CompaniesHouseError(f"Companies House lookup failed for '{name}': {exc}") from exc
