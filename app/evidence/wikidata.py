import requests

WIKIDATA_API = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"

# Common entities
ENTITY_MAP = {
    "india": "Q668",
    "europe": "Q46",
    "asia": "Q48"
}

def check_country_continent(country: str, continent: str):
    """
    Returns True/False if country is in continent using Wikidata
    """
    country = country.lower()
    continent = continent.lower()

    if country not in ENTITY_MAP or continent not in ENTITY_MAP:
        return None

    country_id = ENTITY_MAP[country]
    continent_id = ENTITY_MAP[continent]

    url = WIKIDATA_API.format(country_id)
    data = requests.get(url, timeout=3).json()

    claims = data["entities"][country_id]["claims"]

    # P30 = continent property
    if "P30" not in claims:
        return False

    continents = [
        c["mainsnak"]["datavalue"]["value"]["id"]
        for c in claims["P30"]
    ]

    return continent_id in continents
