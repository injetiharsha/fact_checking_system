INDIA_STATE_SOURCE_HINTS = {
    "andhra_pradesh": {
        "languages": ["telugu", "english"],
        "source_domains": ["eenadu.net", "sakshi.com", "thehansindia.com"],
    },
    "assam": {
        "languages": ["assamese", "english"],
        "source_domains": ["assamtribune.com", "sentinelassam.com", "nenow.in"],
    },
    "bihar": {
        "languages": ["hindi", "urdu", "english"],
        "source_domains": ["prabhatkhabar.com", "livehindustan.com", "hindustantimes.com"],
    },
    "gujarat": {
        "languages": ["gujarati", "english"],
        "source_domains": ["sandesh.com", "gujaratsamachar.com", "indianexpress.com"],
    },
    "karnataka": {
        "languages": ["kannada", "english"],
        "source_domains": ["vijaykarnataka.com", "prajavani.net", "deccanherald.com"],
    },
    "kerala": {
        "languages": ["malayalam", "english"],
        "source_domains": ["manoramaonline.com", "mathrubhumi.com", "thehindu.com"],
    },
    "maharashtra": {
        "languages": ["marathi", "english", "hindi"],
        "source_domains": ["lokmat.com", "maharashtratimes.com", "indianexpress.com"],
    },
    "odisha": {
        "languages": ["odia", "english"],
        "source_domains": ["sambadepaper.com", "odishatv.in", "newindianexpress.com"],
    },
    "punjab": {
        "languages": ["punjabi", "english", "hindi"],
        "source_domains": ["ajitjalandhar.com", "tribuneindia.com", "hindustantimes.com"],
    },
    "rajasthan": {
        "languages": ["hindi", "english"],
        "source_domains": ["patrika.com", "bhaskar.com", "theprint.in"],
    },
    "tamil_nadu": {
        "languages": ["tamil", "english"],
        "source_domains": ["dinamalar.com", "dinamani.com", "thehindu.com"],
    },
    "telangana": {
        "languages": ["telugu", "english", "urdu"],
        "source_domains": ["eenadu.net", "sakshi.com", "thehansindia.com"],
    },
    "uttar_pradesh": {
        "languages": ["hindi", "urdu", "english"],
        "source_domains": ["amarujala.com", "jagran.com", "livehindustan.com"],
    },
    "west_bengal": {
        "languages": ["bengali", "english"],
        "source_domains": ["anandabazar.com", "bartamanpatrika.com", "telegraphindia.com"],
    },
    "delhi": {
        "languages": ["hindi", "english"],
        "source_domains": ["hindustantimes.com", "indianexpress.com", "thehindu.com"],
    },
}


def get_india_state_source_hints(state_name: str | None) -> dict:
    if not state_name:
        return {"languages": [], "source_domains": []}
    return INDIA_STATE_SOURCE_HINTS.get(state_name, {"languages": [], "source_domains": []})
