# evidence/credibility_weights.py

from urllib.parse import urlparse


TRUSTED_NEWS = [
    "reuters.com",
    "bbc.com",
    "apnews.com",
    "ndtv.com",
    "nytimes.com",
    "theguardian.com"
]

GOVERNMENT_SITES = [
    "gov.in",
    "pib.gov.in",
    "data.gov.in",
    "rbi.org.in",
    "nasa.gov",
    "census.gov"
]

INTERNATIONAL_ORGS = [
    "worldbank.org",
    "who.int",
    "un.org",
    "imf.org",
    "oecd.org"
]

SCIENCE_SOURCES = [
    "nature.com",
    "science.org",
    "ourworldindata.org",
    "wikipedia.org"
]

LOW_TRUST = [
    "facebook.com",
    "answers.com",
    "medium.com",
    "blogspot",
    "reddit.com",
    "quora.com"
]

BAD_DOMAINS = [
    "grokipedia.com"
]


def get_weight(url):

    try:
        domain = urlparse(url).netloc.lower()
    except:
        domain = url.lower()

    # Block completely
    for d in BAD_DOMAINS:
        if d in domain:
            return 0.0

    # Government sources
    for d in GOVERNMENT_SITES:
        if d in domain:
            return 1.0

    # International organizations
    for d in INTERNATIONAL_ORGS:
        if d in domain:
            return 0.95

    # Scientific / reference
    for d in SCIENCE_SOURCES:
        if d in domain:
            return 0.9

    # Trusted news
    for d in TRUSTED_NEWS:
        if d in domain:
            return 0.85

    # Low trust
    for d in LOW_TRUST:
        if d in domain:
            return 0.2

    # Default unknown source
    return 0.65