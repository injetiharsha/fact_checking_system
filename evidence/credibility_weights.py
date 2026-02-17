# evidence/credibility_weights.py

TRUSTED_NEWS = [
    "reuters.com",
    "bbc.com",
    "apnews.com",
    "ndtv.com"
]

GOVERNMENT_SITES = [
    "gov.in",
    "pib.gov.in",
    "data.gov.in",
    "rbi.org.in"
]

INTERNATIONAL_ORGS = [
    "worldbank.org",
    "who.int",
    "un.org",
    "imf.org"
]


def get_weight(url):

    url = url.lower()

    for domain in GOVERNMENT_SITES:
        if domain in url:
            return 1.0

    for domain in INTERNATIONAL_ORGS:
        if domain in url:
            return 0.95

    for domain in TRUSTED_NEWS:
        if domain in url:
            return 0.85

    return 0.6
