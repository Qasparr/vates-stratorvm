# ============================================================================
# 93
#
# VATES STRATORVM · google.py — the clear engine: a Google-dork composer.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Scientific Illuminism — Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# MECHANISM: structured flags in, one composed query out. The composer
# supports the standard documented operators — site:, filetype:,
# intitle:, inurl:, intext:, before:, after:, "exact phrases",
# -exclusions, and OR groups. Three things are then done with the query,
# in order of preference: (1) if the operator has set GOOGLE_API_KEY and
# GOOGLE_CX, it runs through the Google Custom Search JSON API — the
# sanctioned door; (2) always, the google.com/search URL for the query is
# printed for manual use. Google result pages are NEVER scraped.
#
# DOCTRINE: the composer is a NEUTRAL instrument — it assembles the
# operators it is given and invents none of its own. This package ships
# NO preset dorks: nothing aimed at credentials, passwords, keys, or
# exposed admin/login panels exists here, by design and on the record.
# ============================================================================

import json
import urllib.parse
import urllib.request

API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def _quote(value):
    """Quote an operator value when it contains whitespace."""
    return f'"{value}"' if " " in value else value


def build_query(terms, site=None, filetype=None, intitle=None,
                inurl=None, intext=None, before=None, after=None,
                exclude=(), or_terms=(), phrase=None):
    """MECHANISM: assemble the query left to right — the free terms (or
    the exact phrase), then each operator in a fixed, readable order,
    then exclusions, then the OR group. Deterministic output for the
    same input: a composed query is a document, not a surprise."""
    parts = []
    if phrase:
        parts.append(f'"{phrase}"')
    if terms:
        parts.append(terms)
    if site:
        parts.append(f"site:{site}")
    if filetype:
        parts.append(f"filetype:{filetype}")
    if intitle:
        parts.append(f"intitle:{_quote(intitle)}")
    if inurl:
        parts.append(f"inurl:{_quote(inurl)}")
    if intext:
        parts.append(f"intext:{_quote(intext)}")
    if before:
        parts.append(f"before:{before}")
    if after:
        parts.append(f"after:{after}")
    for term in exclude:
        parts.append(f"-{_quote(term)}")
    if or_terms:
        parts.append("(" + " OR ".join(_quote(t) for t in or_terms)
                     + ")")
    return " ".join(parts)


def search_url(query):
    """The google.com/search URL carrying the composed query."""
    return "https://www.google.com/search?q=" + \
        urllib.parse.quote_plus(query)


def run_custom_search(query, api_key, cx, num=10, timeout=30.0):
    """MECHANISM: one call to the Custom Search JSON API with the
    operator's own key and search-engine id. Returns a list of
    {title, link, snippet}. Raises on HTTP errors — a failed call is
    reported, never disguised as an empty result."""
    params = urllib.parse.urlencode(
        {"key": api_key, "cx": cx, "q": query, "num": num})
    request = urllib.request.Request(
        f"{API_ENDPOINT}?{params}",
        headers={"User-Agent": "vates-stratorvm/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return [{"title": item.get("title", ""),
             "link": item.get("link", ""),
             "snippet": item.get("snippet", "")}
            for item in data.get("items", [])]
