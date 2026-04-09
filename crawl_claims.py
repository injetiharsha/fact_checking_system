import requests
import json
from bs4 import BeautifulSoup
import time
import random


# Diverse sources: Fact-checkers, science orgs, NASA, news portals, Twitter search (via scraping public claims)
BASE_SOURCES = [
    # Fact-checkers
    "https://www.snopes.com/fact-check/",
    "https://www.politifact.com/factchecks/",
    "https://www.altnews.in/english/",
    "https://www.factly.in/",
    "https://www.boomlive.in/",
    "https://fullfact.org/news/",
    "https://www.factcheck.org/",
    "https://africacheck.org/fact-checks",
    "https://sciencefeedback.co/",
    "https://healthfeedback.org/",
    # Science and space
    "https://www.nasa.gov/news/all-news/",
    "https://www.science.org/news",
    # Major news portals (headlines as claims)
    "https://www.bbc.com/news",
    "https://www.cnn.com/world",
    "https://www.reuters.com/news/world",
    "https://www.nytimes.com/section/world",
    # Twitter search (public claims, limited)
    "https://nitter.net/search?f=tweets&q=claim+OR+rumor+OR+hoax+since%3A2026-03-01&src=typed_query",
]

# Add more sources for each topic (news, science, sports, entertainment, etc.)
EXTRA_SOURCES = [
    # Science
    "https://www.sciencenews.org/",
    "https://www.nature.com/news/",
    "https://www.scientificamerican.com/",
    # Sports
    "https://www.espn.com/",
    "https://www.bbc.com/sport",
    "https://www.sportskeeda.com/",
    # Entertainment
    "https://www.hollywoodreporter.com/",
    "https://www.billboard.com/",
    "https://www.rollingstone.com/",
    # General news
    "https://www.aljazeera.com/news/",
    "https://www.dw.com/en/top-stories/s-9097",
    "https://www.indiatoday.in/",
    "https://www.ndtv.com/",
    "https://www.abc.net.au/news/",
    "https://www.cbc.ca/news",
    "https://www.channelnewsasia.com/world",
    # Tech
    "https://techcrunch.com/",
    "https://www.theverge.com/tech",
    "https://www.wired.com/",
    # Health
    "https://www.medicalnewstoday.com/",
    "https://www.webmd.com/news",
    # Environment
    "https://www.nationalgeographic.com/environment",
    "https://www.climatechangenews.com/",
    # Law/Crime
    "https://www.lawfareblog.com/",
    "https://www.livelaw.in/",
    # History
    "https://www.history.com/news",
    # Geography
    "https://www.geographyrealm.com/",
    # Economics/Business
    "https://www.economist.com/",
    "https://www.business-standard.com/",
    "https://www.ft.com/world",
]

ALL_SOURCES = BASE_SOURCES + EXTRA_SOURCES

HEADERS = {"User-Agent": "Mozilla/5.0"}


import re
from collections import defaultdict
import pandas as pd

# --- Assign context topic using the 14-topic schema ---
CONTEXT_TOPICS = [
    "SCIENCE", "HEALTH", "TECHNOLOGY", "HISTORY", "POLITICS_GOVERNMENT", "ECONOMICS_BUSINESS",
    "GEOGRAPHY", "SPACE_ASTRONOMY", "ENVIRONMENT_CLIMATE", "SOCIETY_CULTURE", "LAW_CRIME",
    "SPORTS", "ENTERTAINMENT", "GENERAL_FACTUAL"
]

KEYWORD_MAP = {
    "SCIENCE": ["physics", "chemistry", "biology", "experiment", "scientist", "laboratory", "genetics", "research", "theory", "quantum", "molecule", "cell", "dna", "evolution", "biotech", "microbiology", "zoology", "botany", "astronomy", "neuroscience", "ecology", "mathematics", "mathematician", "statistics", "hypothesis", "peer review", "discovery"],
    "HEALTH": ["health", "medicine", "covid", "disease", "hospital", "doctor", "nutrition", "vaccine", "virus", "bacteria", "infection", "treatment", "surgery", "clinic", "nurse", "patient", "symptom", "diagnosis", "therapy", "mental health", "wellness", "public health", "epidemic", "pandemic", "pharmacy", "drug", "prescription", "immunity", "diabetes", "cancer", "cardiac", "blood pressure", "cholesterol", "malaria", "fever", "flu", "allergy", "injury", "ambulance", "icu", "operation", "medication"],
    "TECHNOLOGY": ["technology", "internet", "ai", "artificial intelligence", "software", "hardware", "smartphone", "computer", "mobile", "app", "application", "robot", "robotics", "machine learning", "deep learning", "cloud", "server", "database", "algorithm", "gadget", "device", "electronics", "semiconductor", "chip", "processor", "cyber", "digital", "blockchain", "crypto", "bitcoin", "data", "network", "wifi", "bluetooth", "web", "website", "programming", "code", "developer", "engineer", "it", "information technology", "startup", "innovation", "automation", "virtual reality", "vr", "ar", "augmented reality", "iot", "wearable", "drone", "camera", "display", "screen", "keyboard", "mouse", "printer", "usb", "charger", "battery"],
    "HISTORY": ["history", "ancient", "medieval", "independence", "war", "empire", "revolution", "battle", "dynasty", "king", "queen", "historical", "freedom", "partition", "colonial", "british raj", "timeline", "era", "century", "decade", "archaeology", "artifact", "monument", "heritage", "civilization", "treaty", "constitution", "historic", "legend", "mythology", "prehistory", "inscription", "excavation", "museum"],
    "POLITICS_GOVERNMENT": ["parliament", "government", "election", "policy", "minister", "united nations", "pib", "president", "prime minister", "cabinet", "assembly", "senate", "congress", "bill", "law", "governor", "mayor", "mla", "mp", "political", "vote", "voting", "democracy", "republic", "constitution", "ordinance", "gazette", "notification", "bureaucrat", "secretary", "commission", "committee", "municipal", "council", "public sector", "scheme", "initiative", "manifesto", "campaign", "diplomat", "ambassador", "embassy", "consulate", "policy maker", "regulation", "legislation", "judiciary", "executive", "legislature", "state", "central government", "district collector", "chief minister", "cm", "goi", "govt", "politician", "politics"],
    "ECONOMICS_BUSINESS": ["economy", "gdp", "inflation", "stock", "rbi", "business", "market", "trade", "finance", "financial", "bank", "banking", "loan", "investment", "investor", "share", "equity", "mutual fund", "bond", "currency", "rupee", "dollar", "exchange rate", "interest rate", "budget", "tax", "taxation", "income tax", "gst", "revenue", "profit", "loss", "turnover", "dividend", "capital", "asset", "liability", "debt", "credit", "fiscal", "monetary", "policy", "businessman", "entrepreneur", "startup", "industry", "industrial", "manufacturing", "export", "import", "commerce", "merger", "acquisition", "ipo", "stock market", "nse", "bse", "sebi", "insurance", "premium", "salary", "wage", "employment", "unemployment", "job", "labour", "labor", "retail", "wholesale", "supply chain", "logistics", "e-commerce", "venture capital", "angel investor"],
    "GEOGRAPHY": ["river", "mountain", "ocean", "continent", "city", "country", "himalayas", "sahara", "desert", "valley", "island", "peninsula", "plateau", "plain", "lake", "sea", "bay", "gulf", "strait", "cape", "delta", "forest", "jungle", "hill", "peak", "summit", "volcano", "earthquake", "tsunami", "glacier", "tundra", "rainforest", "savanna", "steppe", "prairie", "archipelago", "longitude", "latitude", "equator", "tropic", "arctic", "antarctic", "map", "atlas", "border", "boundary", "territory", "region", "district", "state", "province", "zone", "municipality", "urban", "rural", "suburb", "capital", "metropolitan", "geology", "geomorphology", "cartography", "climate zone"],
    "SPACE_ASTRONOMY": ["mars", "moon", "isro", "nasa", "astronomy", "saturn", "star", "planet", "galaxy", "universe", "cosmos", "telescope", "satellite", "spacecraft", "spaceship", "rocket", "launch", "orbit", "asteroid", "comet", "meteor", "eclipse", "solar", "lunar", "black hole", "nebula", "cosmonaut", "astronaut", "space station", "hubble", "apollo", "chandrayaan", "gaganyaan", "mission", "probe", "extraterrestrial", "alien", "exoplanet", "gravity", "spacex", "blue origin", "rover", "lander", "payload"],
    "ENVIRONMENT_CLIMATE": ["climate", "environment", "rain", "imd", "monsoon", "deforestation", "ozone", "global warming", "greenhouse", "pollution", "air quality", "aqi", "weather", "temperature", "humidity", "precipitation", "drought", "flood", "cyclone", "storm", "hurricane", "typhoon", "tornado", "tsunami", "earthquake", "biodiversity", "ecosystem", "wildlife", "conservation", "recycle", "renewable", "solar energy", "wind energy", "carbon", "emission", "plastic", "waste", "sustainability", "sustainable", "forest", "tree", "plantation", "soil", "erosion", "water conservation", "river cleaning", "ganga", "yamuna", "air pollution", "noise pollution", "climate change", "sea level", "ozone layer", "melting", "glacier", "heatwave", "coldwave", "smog", "environmental"],
    "SOCIETY_CULTURE": ["culture", "society", "festival", "marriage", "custom", "caste", "tradition", "ritual", "ceremony", "community", "religion", "religious", "faith", "belief", "language", "dialect", "folklore", "heritage", "art", "music", "dance", "literature", "poetry", "novel", "story", "myth", "legend", "costume", "attire", "fashion", "food", "cuisine", "family", "kinship", "clan", "tribe", "ethnic", "minority", "majority", "gender", "women", "men", "child", "children", "youth", "elderly", "senior citizen", "social", "ngo", "volunteer", "philanthropy", "charity", "welfare", "social work", "social service", "social justice", "inequality", "discrimination", "reservation", "affirmative action", "dowry", "domestic violence", "child marriage", "child labour", "human rights"],
    "LAW_CRIME": ["law", "court", "crime", "supreme court", "police", "legal", "cybercrime", "judge", "justice", "trial", "verdict", "sentence", "arrest", "bail", "warrant", "fir", "complaint", "petition", "appeal", "prosecution", "defense", "attorney", "lawyer", "advocate", "notary", "contract", "agreement", "evidence", "witness", "testimony", "forensic", "investigation", "enforcement", "prison", "jail", "cell", "convict", "accused", "victim", "offense", "offence", "felony", "misdemeanor", "homicide", "murder", "theft", "robbery", "burglary", "assault", "rape", "fraud", "scam", "corruption", "bribery", "extortion", "kidnap", "abduction", "cyber law", "cyber security", "cyber attack", "cyberbullying", "human trafficking", "narcotics", "drug trafficking", "smuggling", "terrorism", "terrorist", "anti-terror"],
    "SPORTS": ["cricket", "football", "olympics", "sports", "athlete", "coach", "player", "team", "tournament", "match", "game", "score", "goal", "medal", "champion", "league", "cup", "umpire", "referee", "stadium", "track", "field", "race", "marathon", "swimming", "boxing", "wrestling", "badminton", "tennis", "table tennis", "hockey", "basketball", "volleyball", "kabaddi", "golf", "cycling", "skiing", "skating", "archery", "shooting", "weightlifting", "gymnastics", "fencing", "rowing", "sailing", "surfing", "diving", "athletics", "relay", "bat", "ball", "goalkeeper", "striker", "defender", "midfielder", "forward", "coach", "manager", "sportsman", "sportswoman"],
    "ENTERTAINMENT": ["movie", "film", "bollywood", "song", "actor", "entertainment", "netflix", "oscars", "cinema", "theatre", "theater", "drama", "comedy", "tragedy", "musical", "album", "music", "band", "concert", "festival", "celebrity", "star", "director", "producer", "screenplay", "script", "dialogue", "scene", "shooting", "release", "box office", "award", "nomination", "hollywood", "tollywood", "kollywood", "mollywood", "tv", "television", "serial", "show", "episode", "web series", "reality show", "anchor", "host", "judge", "contestant", "performance", "dance", "singing", "voice", "animation", "cartoon", "character", "fiction", "novel", "story", "review", "trailer", "poster", "soundtrack", "background score", "remix", "remake", "sequel", "prequel", "blockbuster", "flop", "hit", "superhit"],
    "GENERAL_FACTUAL": []
}

def assign_context_topic(text):
    text_l = (text or "").lower()
    for label, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_l:
                return label
    return "GENERAL_FACTUAL"
import random

all_claims = []




def crawl_site(site, max_articles=50):
    claims = []
    try:
        resp = requests.get(site, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Twitter-like
        if "nitter.net" in site:
            tweets = soup.find_all('div', class_='tweet-content')
            for t in tweets[:max_articles]:
                claim = t.get_text(strip=True)
                if claim and len(claim) > 40:
                    claims.append({"claim": claim, "evidence_list": []})
            return claims
        # Science/space
        if "nasa.gov" in site or "science.org" in site or "nature.com" in site or "sciencenews.org" in site or "scientificamerican.com" in site:
            articles = soup.find_all('article')
            for art in articles[:max_articles]:
                h = art.find('h2') or art.find('h3') or art.find('h1')
                claim = h.get_text(strip=True) if h else None
                summary = art.find('p')
                evidence = [summary.get_text(strip=True)] if summary else []
                if claim and len(claim) > 40:
                    claims.append({"claim": claim, "evidence_list": evidence})
            return claims
        # News/sports/entertainment
        headlines = soup.find_all(['h2', 'h3', 'h1'])
        for h in headlines[:max_articles]:
            claim = h.get_text(strip=True)
            if claim and len(claim) > 40:
                sib = h.find_next('p')
                evidence = [sib.get_text(strip=True)] if sib else []
                claims.append({"claim": claim, "evidence_list": evidence})
        # Fact-checkers
        links = [a['href'] for a in soup.find_all('a', href=True) if any(x in a['href'] for x in ["/fact-check/", "/factchecks/", "/news/", "/fact-checks", "/article/"])]
        links = list(set(links))[:max_articles]
        for link in links:
            if not link.startswith('http'):
                link = site.rstrip('/') + '/' + link.lstrip('/')
            try:
                art = requests.get(link, headers=HEADERS, timeout=20)
                art_soup = BeautifulSoup(art.text, "html.parser")
                claim = art_soup.find('h1')
                claim = claim.get_text(strip=True) if claim else None
                evidence_list = [p.get_text(strip=True) for p in art_soup.find_all('p') if len(p.get_text(strip=True)) > 50]
                if claim and evidence_list:
                    claims.append({"claim": claim, "evidence_list": evidence_list[:5]})
                time.sleep(0.2)
            except Exception as e:
                print(f"Failed to parse article: {link}", e)
    except Exception as e:
        print(f"Failed to crawl site: {site}", e)
    return claims

# --- Main robust crawl loop ---
MAX_ATTEMPTS = 10
MIN_PER_TOPIC = 5
random.shuffle(ALL_SOURCES)
topic_counts = defaultdict(int)
claims_by_topic = defaultdict(list)
attempt = 0
while attempt < MAX_ATTEMPTS:
    print(f"Crawl attempt {attempt+1}/{MAX_ATTEMPTS}")
    for site in ALL_SOURCES:
        new_claims = crawl_site(site, max_articles=50)
        for item in new_claims:
            topic = assign_context_topic(item["claim"])
            if topic_counts[topic] < MIN_PER_TOPIC:
                claims_by_topic[topic].append(item)
                topic_counts[topic] += 1
    # Check if all topics are filled
    if all(topic_counts[t] >= MIN_PER_TOPIC for t in CONTEXT_TOPICS):
        print("All topics filled.")
        break
    attempt += 1
    print(f"Topic counts so far: {dict(topic_counts)}")

# --- Finalize dataset ---
balanced_claims = []
for topic in CONTEXT_TOPICS:
    items = claims_by_topic.get(topic, [])
    if len(items) >= MIN_PER_TOPIC:
        balanced_claims.extend(items[:MIN_PER_TOPIC])
    else:
        balanced_claims.extend(items)
        print(f"Warning: Only {len(items)} samples for topic '{topic}'")

print(f"Final dataset: {len(balanced_claims)} claims across {len(CONTEXT_TOPICS)} topics.")

with open("rerank_sample.json", "w", encoding="utf-8") as f:
    json.dump(balanced_claims, f, ensure_ascii=False, indent=2)

print(f"Crawled, deduplicated, balanced, and saved {len(balanced_claims)} claims to rerank_sample.json.")


# --- Deduplicate claims ---
def normalize_claim(text):
    return re.sub(r"\W+", "", text.lower())

unique_claims = {}
for item in all_claims:
    norm = normalize_claim(item["claim"])
    if norm not in unique_claims:
        unique_claims[norm] = item

deduped_claims = list(unique_claims.values())
print(f"Deduplicated to {len(deduped_claims)} unique claims.")


# --- Assign context topic using the 14-topic schema ---
CONTEXT_TOPICS = [
    "SCIENCE", "HEALTH", "TECHNOLOGY", "HISTORY", "POLITICS_GOVERNMENT", "ECONOMICS_BUSINESS",
    "GEOGRAPHY", "SPACE_ASTRONOMY", "ENVIRONMENT_CLIMATE", "SOCIETY_CULTURE", "LAW_CRIME",
    "SPORTS", "ENTERTAINMENT", "GENERAL_FACTUAL"
]
from context_data.generate_context_data import KEYWORD_MAP

def assign_context_topic(text):
    text_l = (text or "").lower()
    for label, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_l:
                return label
    return "GENERAL_FACTUAL"

def crawl_until_topic_balance(min_per_topic=5, max_total=1000):
    all_claims = []
    seen_claims = set()
    topic_counts = defaultdict(int)
    topic_claims = defaultdict(list)
    crawl_round = 0
    while True:
        crawl_round += 1
        print(f"\n--- Crawl round {crawl_round} ---")
        # Use the original crawl logic to get more claims
        round_claims = []
        for site in FACT_CHECK_SITES:
            print(f"Crawling: {site}")
            try:
                resp = requests.get(site, headers=HEADERS, timeout=20)
                soup = BeautifulSoup(resp.text, "html.parser")
                if "nitter.net" in site:
                    tweets = soup.find_all('div', class_='tweet-content')
                    for t in tweets[:50]:
                        claim = t.get_text(strip=True)
                        if claim and len(claim) > 40:
                            round_claims.append({"claim": claim, "evidence_list": []})
                    continue
                if "nasa.gov" in site or "science.org" in site:
                    articles = soup.find_all('article')
                    for art in articles[:50]:
                        h = art.find('h2') or art.find('h3') or art.find('h1')
                        claim = h.get_text(strip=True) if h else None
                        summary = art.find('p')
                        evidence = [summary.get_text(strip=True)] if summary else []
                        if claim and len(claim) > 40:
                            round_claims.append({"claim": claim, "evidence_list": evidence})
                    continue
                if any(x in site for x in ["bbc.com", "cnn.com", "reuters.com", "nytimes.com"]):
                    headlines = soup.find_all(['h2', 'h3', 'h1'])
                    for h in headlines[:60]:
                        claim = h.get_text(strip=True)
                        if claim and len(claim) > 40:
                            sib = h.find_next('p')
                            evidence = [sib.get_text(strip=True)] if sib else []
                            round_claims.append({"claim": claim, "evidence_list": evidence})
                    continue
                links = [a['href'] for a in soup.find_all('a', href=True) if any(x in a['href'] for x in ["/fact-check/", "/factchecks/", "/news/", "/fact-checks", "/article/"])]
                links = list(set(links))[:80]
                for link in links:
                    if not link.startswith('http'):
                        link = site.rstrip('/') + '/' + link.lstrip('/')
                    try:
                        art = requests.get(link, headers=HEADERS, timeout=20)
                        art_soup = BeautifulSoup(art.text, "html.parser")
                        claim = art_soup.find('h1')
                        claim = claim.get_text(strip=True) if claim else None
                        evidence_list = [p.get_text(strip=True) for p in art_soup.find_all('p') if len(p.get_text(strip=True)) > 50]
                        if claim and evidence_list:
                            round_claims.append({"claim": claim, "evidence_list": evidence_list[:5]})
                        time.sleep(0.2)
                    except Exception as e:
                        continue
            except Exception as e:
                continue
        # Deduplicate and assign topics
        for item in round_claims:
            norm = re.sub(r"\W+", "", item["claim"].lower())
            if norm in seen_claims:
                continue
            seen_claims.add(norm)
            topic = assign_context_topic(item["claim"])
            if topic_counts[topic] < min_per_topic:
                topic_claims[topic].append(item)
                topic_counts[topic] += 1
            all_claims.append(item)
            if sum(topic_counts[t] for t in CONTEXT_TOPICS) >= min_per_topic * len(CONTEXT_TOPICS):
                break
        # Log progress
        print("Topic counts so far:")
        for t in CONTEXT_TOPICS:
            print(f"  {t}: {topic_counts[t]}")
        # Check if all topics have enough
        if all(topic_counts[t] >= min_per_topic for t in CONTEXT_TOPICS):
            break
        if len(all_claims) > max_total:
            print("Max total claims reached, stopping crawl.")
            break
    # Flatten and shuffle
    balanced_claims = []
    for t in CONTEXT_TOPICS:
        balanced_claims.extend(topic_claims[t][:min_per_topic])
    random.shuffle(balanced_claims)
    print(f"Final dataset: {len(balanced_claims)} claims across {len(CONTEXT_TOPICS)} topics.")
    with open("rerank_sample.json", "w", encoding="utf-8") as f:
        json.dump(balanced_claims, f, ensure_ascii=False, indent=2)
    print(f"Crawled, deduplicated, balanced, and saved {len(balanced_claims)} claims to rerank_sample.json.")

# Run the new robust crawl
crawl_until_topic_balance(min_per_topic=5, max_total=2000)
