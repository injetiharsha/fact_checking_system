TRUSTED_DOMAINS = [
    "bbc.com",
    "reuters.com",
    "who.int",
    "cdc.gov",
    "ndtv.com",
    "thehindu.com",
    "aljazeera.com",
    "theguardian.com"
]

def is_trusted(url: str) -> bool:
    return any(domain in url for domain in TRUSTED_DOMAINS)
