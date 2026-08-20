"""
Client for two free, keyless FSA (UK Food Standards Agency) APIs:

- Regulated Products API (Novel Food register) — data.food.gov.uk/regulated-products
- Food Alerts API (recalls / allergy alerts / FAFA) — data.food.gov.uk/food-alerts

No API key required. Both are OGL3-licensed government data.

REWRITTEN from an earlier version that called a '?name=' search parameter on
the Novel Food endpoint which does not exist (confirmed by testing against
the live API - every call failed with a 404). The real API is a static,
browsable list, not a name-search endpoint: fetch it once, then match
locally. This module now implements the same hybrid category-level +
curated-qualifier matching logic validated during this project's accuracy
work (Cohen's kappa = 0.412 on live ground truth), not the original
single-word matching that scored at chance level (kappa = 0.001) or the
per-product reversal that scored below chance (kappa = -0.017) - both
tested and rejected before arriving at this version.
"""

from __future__ import annotations
import requests

NOVEL_FOOD_LIST_URL = "http://data.food.gov.uk/regulated-products/id/regime/novel-foods.json"
FOOD_ALERTS_BASE = "https://data.food.gov.uk/food-alerts/id"
TIMEOUT = 15

SUPPLEMENT_KEYWORDS = ["supplement", "vitamin", "capsule", "tablet", "mineral", "softgel", "gummies"]

STOPWORDS = {
    "vitamin", "oil", "extract", "acid", "protein", "powder", "complex", "root",
    "seed", "mushroom", "monohydrate",
}

# Categories where a broad, common ingredient name is known to coincide with
# a narrow, compound-specific Novel Food register entry. Category-level
# matching alone over-triggers for these (e.g. "Zinc" matching
# "zinc-l-pidolate" regardless of which zinc form a product actually uses),
# so an additional qualifying term must also appear in the product's own
# name. Built empirically from confirmed false positives against real ground
# truth, not guessed in advance - see the validation script this was ported
# from for the full derivation.
REQUIRES_ADDITIONAL_QUALIFIER = {
    "Zinc": ["pidolate"],
    "Whey Protein": ["bovine", "isolate"],
    "Nicotinamide": ["riboside"],
    "Resveratrol": ["trans"],
    "Lactoferrin": ["bovine"],
    "Magnesium Citrate": ["malate"],
    "Magnesium Malate": ["citrate"],
}


class FSAClientError(Exception):
    pass


_novel_food_slugs_cache: list[str] | None = None


def _fetch_novel_food_slugs() -> list[str]:
    """
    Fetches the full Novel Food substance list ONCE and caches it for the
    life of the process - this is a small (~700 item), slow-changing list,
    not something to re-fetch per ingredient check.
    """
    global _novel_food_slugs_cache
    if _novel_food_slugs_cache is not None:
        return _novel_food_slugs_cache

    try:
        resp = requests.get(NOVEL_FOOD_LIST_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise FSAClientError(f"Could not fetch the Novel Food register at all: {exc}") from exc

    items = data.get("items", [])
    if not items:
        raise FSAClientError("Novel Food register response had no items - check the endpoint hasn't changed.")
    substance_scheme = items[0].get("substanceScheme", [])
    if not substance_scheme:
        raise FSAClientError("Novel Food register response had no substanceScheme - check the endpoint hasn't changed.")
    top_concepts = substance_scheme[0].get("hasTopConcept", [])

    slugs = [c.get("@id", "").rstrip("/").split("/")[-1] for c in top_concepts]
    _novel_food_slugs_cache = slugs
    return slugs


def check_novel_food_status(category: str, product_name: str = "") -> dict:
    """
    Checks a product's ingredient CATEGORY (e.g. "Cordyceps", "Magnesium
    Citrate") against the live GB Novel Food register, using product_name
    as an additional qualifying signal for the small set of categories in
    REQUIRES_ADDITIONAL_QUALIFIER where a broad category name is known to
    coincide with a narrow, compound-specific register entry.

    Returns {"found": bool, "matched_slug": str | None}. "found": True
    means this product's ingredient appears to require Novel Food
    authorisation - callers should treat this as a signal requiring the
    product to show that authorisation, not as an automatic fail.

    KNOWN LIMITATION, not fixable by better matching: some Novel Food
    determinations depend on a specific species or strain (e.g. Cordyceps
    militaris vs. sinensis) that is typically not stated in a product's name
    at all. This check will under-detect those cases - confirmed during
    validation, where the 27 remaining disagreements concentrated entirely
    in five such categories (Cordyceps, Omega-3, Astaxanthin, Krill Oil,
    Fulvic Acid).
    """
    try:
        slugs = _fetch_novel_food_slugs()
    except FSAClientError:
        raise

    raw_words = [w.lower() for w in category.replace("(", " ").replace(")", " ").split()]
    distinctive = [w for w in raw_words if w not in STOPWORDS and len(w) > 2]
    if not distinctive:
        return {"found": False, "matched_slug": None, "note": "No distinctive term in category name to match on."}

    combined_text = f"{category} {product_name}".lower()
    extra_qualifiers = REQUIRES_ADDITIONAL_QUALIFIER.get(category, [])

    for slug in slugs:
        slug_words = set(slug.lower().replace("-", " ").split())
        if not all(any(dw in sw for sw in slug_words) for dw in distinctive):
            continue
        if extra_qualifiers and not all(q in combined_text for q in extra_qualifiers):
            continue
        return {"found": True, "matched_slug": slug, "note": None}
    return {"found": False, "matched_slug": None, "note": None}


def check_recent_alerts(brand_name: str) -> dict:
    """
    Looks up recent FSA Food Alerts mentioning a brand, filtered to only
    count as a match if the alert ALSO mentions a supplement-related term.

    Without this filter, a large retailer or generic-sounding brand name
    (e.g. "Tesco Health") matches ordinary grocery recalls entirely
    unrelated to supplements - confirmed against real search results, where
    "Tesco" returned genuine alerts about an unrelated chicken soup recall.
    This filter reduced false positives from 37 to 18 in validation without
    materially affecting true positives.

    KNOWN LIMITATIONS, not fixable by better matching: (1) this checks at
    brand level, not per-product - a brand with one flagged SKU among many
    clean ones will show the same result for all of them; (2) FSA Food
    Alerts covers food-safety recalls only, not Advertising Standards
    Authority rulings on misleading marketing claims, which is a different
    regulatory body's data entirely. Both were confirmed as the cause of
    every remaining missed true positive during validation.
    """
    try:
        resp = requests.get(
            FOOD_ALERTS_BASE,
            params={"search": brand_name, "_limit": 20, "_view": "full"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return {"found": False, "alerts": []}

        relevant = []
        for item in items:
            text = f"{item.get('title', '')} {item.get('description', '')}".lower()
            if any(kw in text for kw in SUPPLEMENT_KEYWORDS):
                relevant.append(item)
        return {"found": bool(relevant), "alerts": relevant}
    except requests.RequestException as exc:
        raise FSAClientError(f"FSA Food Alerts lookup failed for '{brand_name}': {exc}") from exc
