import os
import re
import time
import math
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup
from collections import defaultdict

# ============================================================
# CONFIG
# ============================================================

OUTPUT_FILE = "context_labeled_data_hierarchical.csv"
REQUEST_DELAY = 0.8
MAX_RETRIES = 3
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

FINAL_CONTEXT_CLASSES = [
    "science",
    "health",
    "technology",
    "history",
    "politics_government",
    "economics_business",
    "geography",
    "space_astronomy",
    "environment_climate",
    "society_culture",
    "law_crime",
    "sports",
    "entertainment",
    "general_factual",
]

# ============================================================
# HIERARCHICAL TAXONOMY
# Each final class contains:
# - general_terms: broader terms for news/live-claim robustness
# - primary / secondary / tertiary sublabels
# Each sublabel contains:
# - pages
# - keywords
# ============================================================

TAXONOMY = {
    "science": {
        "general_terms": [
            "science", "scientific", "research", "evidence", "experiment",
            "observation", "theory", "study", "analysis", "data", "method",
            "measured", "tested", "discovery", "finding"
        ],
        "primary": {
            "physics": {
                "pages": ["Physics", "Classical_mechanics", "Quantum_mechanics", "Thermodynamics"],
                "keywords": ["physics", "force", "energy", "motion", "matter", "particle", "quantum", "mechanics"]
            },
            "chemistry": {
                "pages": ["Chemistry", "Chemical_reaction", "Organic_chemistry", "Inorganic_chemistry"],
                "keywords": ["chemistry", "chemical", "molecule", "atom", "reaction", "compound", "element"]
            },
            "biology": {
                "pages": ["Biology", "Cell_biology", "Genetics", "Evolution"],
                "keywords": ["biology", "cell", "genetics", "organism", "species", "evolution", "dna"]
            },
            "scientific_method": {
                "pages": ["Scientific_method", "Hypothesis", "Observation", "Experiment"],
                "keywords": ["hypothesis", "observation", "experiment", "scientific method", "testing", "replication"]
            },
            "mathematics": {
                "pages": ["Mathematics", "Algebra", "Statistics", "Calculus"],
                "keywords": ["mathematics", "equation", "statistics", "algebra", "calculus", "probability"]
            },
        },
        "secondary": {
            "earth_science": {
                "pages": ["Earth_science", "Geology", "Meteorology", "Oceanography"],
                "keywords": ["geology", "meteorology", "earth science", "oceanography", "crust", "atmosphere"]
            },
            "research_methods": {
                "pages": ["Research", "Empirical_evidence", "Peer_review", "Measurement"],
                "keywords": ["research", "peer review", "measurement", "evidence", "empirical", "methodology"]
            },
            "applied_science": {
                "pages": ["Applied_science", "Materials_science", "Biochemistry", "Geophysics"],
                "keywords": ["applied science", "materials", "biochemistry", "geophysics", "application"]
            },
        },
        "tertiary": {
            "scientific_tools": {
                "pages": ["Microscope", "Telescope", "Laboratory", "Spectroscopy"],
                "keywords": ["microscope", "telescope", "laboratory", "spectroscopy", "instrument"]
            },
            "scientific_reporting": {
                "pages": ["Scientific_journal", "Academic_publishing", "Replication_crisis"],
                "keywords": ["journal", "publication", "paper", "published", "replication"]
            },
            "general_science_language": {
                "pages": ["Science", "Research", "Observation"],
                "keywords": ["study", "finding", "scientists", "observed", "tested", "analysis"]
            },
        },
    },

    "health": {
        "general_terms": [
            "health", "medical", "doctor", "patient", "treatment", "disease",
            "hospital", "clinical", "public health", "symptoms", "care",
            "diagnosis", "medicine", "recovery", "infection"
        ],
        "primary": {
            "medicine": {
                "pages": ["Medicine", "Medical_diagnosis", "Therapy", "Pharmacology"],
                "keywords": ["medicine", "diagnosis", "therapy", "treatment", "drug", "pharmacology"]
            },
            "public_health": {
                "pages": ["Public_health", "Epidemiology", "Vaccination", "Health_policy"],
                "keywords": ["public health", "epidemiology", "vaccination", "health policy", "population health"]
            },
            "disease": {
                "pages": ["Disease", "Infectious_disease", "Cancer", "Diabetes"],
                "keywords": ["disease", "infection", "cancer", "diabetes", "illness", "pathogen"]
            },
            "mental_health": {
                "pages": ["Mental_health", "Depression_(mood)", "Anxiety_disorder", "Psychiatry"],
                "keywords": ["mental health", "depression", "anxiety", "psychiatry", "psychological"]
            },
        },
        "secondary": {
            "nutrition": {
                "pages": ["Nutrition", "Diet_(nutrition)", "Malnutrition", "Vitamin"],
                "keywords": ["nutrition", "diet", "vitamin", "malnutrition", "nutrient"]
            },
            "healthcare_systems": {
                "pages": ["Health_care", "Hospital", "Primary_care", "Universal_health_care"],
                "keywords": ["health care", "hospital", "primary care", "insurance", "medical system"]
            },
            "human_body": {
                "pages": ["Physiology", "Anatomy", "Immune_system", "Cardiovascular_system"],
                "keywords": ["physiology", "anatomy", "immune system", "body", "organ", "circulatory"]
            },
        },
        "tertiary": {
            "clinical_terms": {
                "pages": ["Symptom", "Prognosis", "Screening_(medicine)", "Clinical_trial"],
                "keywords": ["symptom", "clinical trial", "screening", "prognosis"]
            },
            "health_reporting": {
                "pages": ["Disease_outbreak", "Pandemic", "World_Health_Organization"],
                "keywords": ["outbreak", "pandemic", "health agency", "reported cases"]
            },
            "general_health_language": {
                "pages": ["Health", "Medicine", "Public_health"],
                "keywords": ["patients", "medical experts", "health officials", "health risk"]
            },
        },
    },

    "technology": {
        "general_terms": [
            "technology", "software", "digital", "computer", "internet",
            "platform", "system", "device", "application", "algorithm",
            "data", "online", "AI", "technical", "automation"
        ],
        "primary": {
            "computer_science": {
                "pages": ["Computer_science", "Algorithm", "Data_structure", "Computation"],
                "keywords": ["computer science", "algorithm", "computation", "data structure"]
            },
            "software": {
                "pages": ["Software", "Software_engineering", "Operating_system", "Computer_program"],
                "keywords": ["software", "program", "operating system", "application", "code"]
            },
            "artificial_intelligence": {
                "pages": ["Artificial_intelligence", "Machine_learning", "Neural_network_(machine_learning)", "Natural_language_processing"],
                "keywords": ["artificial intelligence", "machine learning", "model", "neural network", "AI", "NLP"]
            },
            "engineering_technology": {
                "pages": ["Technology", "Engineering", "Electrical_engineering", "Mechanical_engineering"],
                "keywords": ["technology", "engineering", "device", "technical", "design", "machinery"]
            },
        },
        "secondary": {
            "internet_and_networks": {
                "pages": ["Internet", "World_Wide_Web", "Computer_network", "Cloud_computing"],
                "keywords": ["internet", "web", "network", "cloud", "server", "online service"]
            },
            "electronics": {
                "pages": ["Electronics", "Semiconductor", "Integrated_circuit", "Microprocessor"],
                "keywords": ["electronics", "semiconductor", "chip", "processor", "circuit"]
            },
            "robotics_automation": {
                "pages": ["Robotics", "Automation", "Control_theory", "Autonomous_robot"],
                "keywords": ["robotics", "automation", "robot", "autonomous", "control system"]
            },
        },
        "tertiary": {
            "consumer_tech": {
                "pages": ["Smartphone", "Personal_computer", "Laptop", "Mobile_app"],
                "keywords": ["smartphone", "app", "laptop", "consumer device", "mobile"]
            },
            "tech_business_language": {
                "pages": ["Information_technology", "Digital_transformation", "Platform_economy"],
                "keywords": ["tech company", "digital platform", "service outage", "rollout", "update"]
            },
            "general_tech_language": {
                "pages": ["Technology", "Software", "Internet"],
                "keywords": ["users", "developers", "system", "feature", "launch", "tool"]
            },
        },
    },

    "history": {
        "general_terms": [
            "history", "historical", "past", "century", "ancient", "medieval",
            "modern", "empire", "war", "era", "period", "dynasty", "civilization"
        ],
        "primary": {
            "world_history": {
                "pages": ["World_history", "Ancient_history", "Modern_history", "Middle_Ages"],
                "keywords": ["world history", "ancient", "modern", "middle ages", "historical period"]
            },
            "indian_history": {
                "pages": ["History_of_India", "Maurya_Empire", "Mughal_Empire", "British_Raj"],
                "keywords": ["history of india", "empire", "raj", "dynasty", "subcontinent"]
            },
            "wars_revolutions": {
                "pages": ["World_War_I", "World_War_II", "French_Revolution", "Industrial_Revolution"],
                "keywords": ["war", "revolution", "conflict", "military campaign", "industrial revolution"]
            },
            "historiography": {
                "pages": ["Historiography", "Historian", "Archaeology", "Historical_method"],
                "keywords": ["historian", "archaeology", "historical method", "record", "source"]
            },
        },
        "secondary": {
            "civilizations": {
                "pages": ["Civilization", "Ancient_Egypt", "Mesopotamia", "Indus_Valley_Civilisation"],
                "keywords": ["civilization", "ancient society", "settlement", "urban center"]
            },
            "historical_figures": {
                "pages": ["Alexander_the_Great", "Ashoka", "Napoleon", "Mahatma_Gandhi"],
                "keywords": ["ruler", "leader", "historical figure", "emperor"]
            },
            "colonialism": {
                "pages": ["Colonialism", "Imperialism", "Decolonization"],
                "keywords": ["colonial", "imperial", "colony", "decolonization"]
            },
        },
        "tertiary": {
            "historical_language": {
                "pages": ["History", "Historical_document", "Timeline_of_world_history"],
                "keywords": ["historically", "records show", "during the period", "at the time"]
            },
            "museums_heritage": {
                "pages": ["Museum", "Cultural_heritage", "Artifact_(archaeology)"],
                "keywords": ["artifact", "heritage", "museum", "preserved"]
            },
            "general_past_events": {
                "pages": ["History", "World_history"],
                "keywords": ["in the past", "previous century", "historical event"]
            },
        },
    },

    "politics_government": {
        "general_terms": [
            "politics", "government", "policy", "election", "parliament",
            "minister", "president", "state", "governance", "administration",
            "legislation", "public office", "cabinet"
        ],
        "primary": {
            "government": {
                "pages": ["Government", "State_(polity)", "Public_administration", "Cabinet_(government)"],
                "keywords": ["government", "state", "administration", "public administration", "cabinet"]
            },
            "democracy_elections": {
                "pages": ["Democracy", "Election", "Voting", "Electoral_system"],
                "keywords": ["democracy", "election", "vote", "voter", "electoral", "ballot"]
            },
            "public_policy": {
                "pages": ["Public_policy", "Policy", "Regulation", "Governance"],
                "keywords": ["public policy", "regulation", "governance", "policy decision"]
            },
            "constitution_political_systems": {
                "pages": ["Constitution", "Political_system", "Parliament", "Federalism"],
                "keywords": ["constitution", "parliament", "federal", "political system", "constitutional"]
            },
        },
        "secondary": {
            "international_relations": {
                "pages": ["International_relations", "Diplomacy", "United_Nations", "Treaty"],
                "keywords": ["international relations", "diplomacy", "treaty", "foreign policy", "UN"]
            },
            "political_theory": {
                "pages": ["Political_science", "Liberalism", "Conservatism", "Socialism"],
                "keywords": ["political theory", "ideology", "liberalism", "conservatism", "socialism"]
            },
            "bureaucracy_and_state": {
                "pages": ["Bureaucracy", "Civil_service", "Rule_of_law"],
                "keywords": ["bureaucracy", "civil service", "rule of law", "state institutions"]
            },
        },
        "tertiary": {
            "general_political_language": {
                "pages": ["Politics", "Government", "Election"],
                "keywords": ["officials", "lawmakers", "announced policy", "government said", "voters"]
            },
            "campaign_terms": {
                "pages": ["Political_campaign", "Manifesto", "Opinion_poll"],
                "keywords": ["campaign", "manifesto", "poll", "candidate"]
            },
            "civic_terms": {
                "pages": ["Citizenship", "Civic_engagement"],
                "keywords": ["citizens", "civic", "public affairs"]
            },
        },
    },

    "economics_business": {
        "general_terms": [
            "economy", "economic", "business", "finance", "market", "trade",
            "bank", "investment", "inflation", "revenue", "industry",
            "growth", "consumer", "supply", "demand"
        ],
        "primary": {
            "economics": {
                "pages": ["Economics", "Macroeconomics", "Microeconomics", "Economic_growth"],
                "keywords": ["economics", "macroeconomics", "microeconomics", "growth", "economic output"]
            },
            "finance": {
                "pages": ["Finance", "Investment", "Financial_market", "Stock_market"],
                "keywords": ["finance", "investment", "market", "stock", "capital", "financial"]
            },
            "banking": {
                "pages": ["Bank", "Central_bank", "Commercial_bank", "Monetary_policy"],
                "keywords": ["bank", "central bank", "interest rate", "monetary policy", "lending"]
            },
            "business": {
                "pages": ["Business", "Corporation", "Entrepreneurship", "Management"],
                "keywords": ["business", "company", "corporation", "management", "enterprise"]
            },
        },
        "secondary": {
            "trade_and_industry": {
                "pages": ["Trade", "International_trade", "Manufacturing", "Industry_(economics)"],
                "keywords": ["trade", "exports", "imports", "manufacturing", "industry"]
            },
            "inflation_prices": {
                "pages": ["Inflation", "Consumer_price_index", "Price", "Cost_of_living"],
                "keywords": ["inflation", "price", "cost of living", "consumer prices"]
            },
            "labor_and_employment": {
                "pages": ["Labour_economics", "Employment", "Unemployment", "Wage"],
                "keywords": ["employment", "unemployment", "wage", "labor market", "jobs"]
            },
        },
        "tertiary": {
            "business_news_language": {
                "pages": ["Revenue", "Profit_(accounting)", "Merger", "Start-up_company"],
                "keywords": ["revenue", "profit", "loss", "quarterly results", "startup", "merger"]
            },
            "consumer_market_terms": {
                "pages": ["Consumer", "Retail", "Supply_and_demand"],
                "keywords": ["consumer demand", "retail", "supply", "demand"]
            },
            "general_economic_language": {
                "pages": ["Economy", "Business"],
                "keywords": ["economists", "markets reacted", "business activity"]
            },
        },
    },

    "geography": {
        "general_terms": [
            "geography", "region", "country", "location", "terrain", "climate",
            "river", "mountain", "coast", "population", "land", "map", "area"
        ],
        "primary": {
            "physical_geography": {
                "pages": ["Physical_geography", "Landform", "Mountain", "River"],
                "keywords": ["physical geography", "landform", "mountain", "river", "terrain"]
            },
            "human_geography": {
                "pages": ["Human_geography", "Population_geography", "Urban_geography", "Migration"],
                "keywords": ["human geography", "population", "urban", "migration", "settlement"]
            },
            "earth_regions": {
                "pages": ["Continent", "Asia", "Europe", "Africa"],
                "keywords": ["continent", "region", "country", "area", "border"]
            },
            "cartography": {
                "pages": ["Map", "Cartography", "Geographic_information_system"],
                "keywords": ["map", "cartography", "geographic information", "location data"]
            },
        },
        "secondary": {
            "climate_and_weather_space": {
                "pages": ["Climate", "Biome", "Desert", "Rainforest"],
                "keywords": ["climate zone", "biome", "desert", "rainforest"]
            },
            "oceans_and_coasts": {
                "pages": ["Ocean", "Coast", "Sea", "Island"],
                "keywords": ["ocean", "coast", "sea", "island"]
            },
            "geology_linked": {
                "pages": ["Geology", "Plate_tectonics", "Volcano", "Earthquake"],
                "keywords": ["tectonic", "volcano", "earthquake", "geology"]
            },
        },
        "tertiary": {
            "place_reporting_language": {
                "pages": ["Geography", "Country", "City"],
                "keywords": ["located in", "region", "area", "district", "province"]
            },
            "spatial_terms": {
                "pages": ["Latitude", "Longitude", "Topography"],
                "keywords": ["latitude", "longitude", "elevation", "topography"]
            },
            "general_location_terms": {
                "pages": ["Location", "Map"],
                "keywords": ["geographic area", "nearby", "across the region"]
            },
        },
    },

    "space_astronomy": {
        "general_terms": [
            "space", "astronomy", "planet", "star", "moon", "orbit",
            "galaxy", "telescope", "cosmic", "universe", "mission", "satellite"
        ],
        "primary": {
            "astronomy": {
                "pages": ["Astronomy", "Astrophysics", "Observational_astronomy", "Cosmology"],
                "keywords": ["astronomy", "astrophysics", "cosmology", "observation", "universe"]
            },
            "solar_system": {
                "pages": ["Solar_System", "Planet", "Moon", "Sun"],
                "keywords": ["solar system", "planet", "moon", "sun", "orbit"]
            },
            "stars_and_galaxies": {
                "pages": ["Star", "Galaxy", "Milky_Way", "Black_hole"],
                "keywords": ["star", "galaxy", "black hole", "milky way", "stellar"]
            },
            "space_exploration": {
                "pages": ["Space_exploration", "NASA", "Spacecraft", "Satellite"],
                "keywords": ["space mission", "nasa", "spacecraft", "satellite", "launch"]
            },
        },
        "secondary": {
            "rockets_and_launches": {
                "pages": ["Rocket", "Launch_vehicle", "Space_launch", "SpaceX"],
                "keywords": ["rocket", "launch vehicle", "space launch"]
            },
            "observatories": {
                "pages": ["Telescope", "Hubble_Space_Telescope", "James_Webb_Space_Telescope"],
                "keywords": ["telescope", "observatory", "deep space image"]
            },
            "planetary_science": {
                "pages": ["Planetary_science", "Mars", "Jupiter", "Exoplanet"],
                "keywords": ["planetary", "mars", "jupiter", "exoplanet"]
            },
        },
        "tertiary": {
            "space_news_language": {
                "pages": ["NASA", "European_Space_Agency", "Indian_Space_Research_Organisation"],
                "keywords": ["space agency", "mission update", "orbiting", "observed in space"]
            },
            "general_cosmic_terms": {
                "pages": ["Outer_space", "Universe"],
                "keywords": ["cosmic", "space-based", "celestial"]
            },
            "satellite_terms": {
                "pages": ["Satellite", "Remote_sensing"],
                "keywords": ["satellite imagery", "orbital", "remote sensing"]
            },
        },
    },

    "environment_climate": {
        "general_terms": [
            "environment", "climate", "pollution", "emissions", "ecosystem",
            "biodiversity", "sustainability", "warming", "conservation",
            "renewable", "carbon", "greenhouse gas"
        ],
        "primary": {
            "climate_change": {
                "pages": ["Climate_change", "Global_warming", "Greenhouse_gas", "Carbon_dioxide"],
                "keywords": ["climate change", "global warming", "greenhouse gas", "carbon emissions"]
            },
            "ecology": {
                "pages": ["Ecology", "Ecosystem", "Food_web", "Habitat"],
                "keywords": ["ecology", "ecosystem", "habitat", "species interaction"]
            },
            "pollution": {
                "pages": ["Pollution", "Air_pollution", "Water_pollution", "Plastic_pollution"],
                "keywords": ["pollution", "air pollution", "water pollution", "waste", "contamination"]
            },
            "conservation": {
                "pages": ["Conservation_biology", "Protected_area", "Endangered_species", "Biodiversity"],
                "keywords": ["conservation", "endangered", "biodiversity", "protected area"]
            },
        },
        "secondary": {
            "energy_transition": {
                "pages": ["Renewable_energy", "Solar_power", "Wind_power", "Energy_transition"],
                "keywords": ["renewable energy", "solar", "wind", "clean energy"]
            },
            "natural_resources": {
                "pages": ["Natural_resource", "Deforestation", "Water_resources", "Soil"],
                "keywords": ["natural resources", "deforestation", "water resources", "soil"]
            },
            "extreme_weather_linked": {
                "pages": ["Drought", "Flood", "Heat_wave", "Wildfire"],
                "keywords": ["drought", "flood", "heat wave", "wildfire", "extreme weather"]
            },
        },
        "tertiary": {
            "environmental_policy_language": {
                "pages": ["Environmental_policy", "Paris_Agreement", "Sustainable_development"],
                "keywords": ["environmental policy", "climate targets", "sustainable development"]
            },
            "general_environment_language": {
                "pages": ["Environment", "Climate_change"],
                "keywords": ["environmental impact", "climate risk", "emissions report"]
            },
            "green_terms": {
                "pages": ["Recycling", "Circular_economy"],
                "keywords": ["recycling", "green initiative", "waste reduction"]
            },
        },
    },

    "society_culture": {
        "general_terms": [
            "society", "culture", "community", "education", "religion",
            "language", "family", "identity", "social", "custom", "tradition"
        ],
        "primary": {
            "sociology": {
                "pages": ["Sociology", "Social_structure", "Social_norm", "Social_group"],
                "keywords": ["sociology", "social structure", "social norm", "group behavior"]
            },
            "culture": {
                "pages": ["Culture", "Cultural_anthropology", "Tradition", "Cultural_heritage"],
                "keywords": ["culture", "tradition", "custom", "heritage", "cultural"]
            },
            "religion": {
                "pages": ["Religion", "Religious_studies", "Ritual", "Belief"],
                "keywords": ["religion", "ritual", "belief", "faith", "religious"]
            },
            "education": {
                "pages": ["Education", "School", "Higher_education", "Literacy"],
                "keywords": ["education", "school", "literacy", "students", "teaching"]
            },
        },
        "secondary": {
            "language_and_identity": {
                "pages": ["Language", "Identity_(social_science)", "Ethnicity", "Multiculturalism"],
                "keywords": ["language", "identity", "ethnicity", "multicultural"]
            },
            "family_and_community": {
                "pages": ["Family", "Marriage", "Community", "Kinship"],
                "keywords": ["family", "community", "marriage", "kinship"]
            },
            "anthropology": {
                "pages": ["Anthropology", "Human_behavior", "Cross-cultural_studies"],
                "keywords": ["anthropology", "human behavior", "cross-cultural"]
            },
        },
        "tertiary": {
            "social_news_language": {
                "pages": ["Society", "Culture", "Education"],
                "keywords": ["community leaders", "social issue", "cultural event", "public response"]
            },
            "public_behavior_terms": {
                "pages": ["Social_change", "Public_opinion"],
                "keywords": ["public opinion", "social change", "community reaction"]
            },
            "general_human_terms": {
                "pages": ["Society", "Family"],
                "keywords": ["people", "communities", "social groups"]
            },
        },
    },

    "law_crime": {
        "general_terms": [
            "law", "legal", "crime", "court", "police", "judge", "justice",
            "arrest", "trial", "evidence", "criminal", "rights", "case"
        ],
        "primary": {
            "law": {
                "pages": ["Law", "Legal_system", "Rule_of_law", "Jurisprudence"],
                "keywords": ["law", "legal system", "jurisprudence", "rule of law"]
            },
            "criminal_law": {
                "pages": ["Criminal_law", "Crime", "Felony", "Misdemeanor"],
                "keywords": ["criminal law", "crime", "offense", "criminal charge"]
            },
            "justice_courts": {
                "pages": ["Justice", "Court", "Judge", "Trial"],
                "keywords": ["justice", "court", "judge", "trial", "hearing"]
            },
            "rights": {
                "pages": ["Human_rights", "Civil_rights", "Constitutional_law", "Due_process"],
                "keywords": ["rights", "human rights", "civil rights", "due process"]
            },
        },
        "secondary": {
            "policing": {
                "pages": ["Police", "Law_enforcement", "Arrest", "Investigation"],
                "keywords": ["police", "arrest", "investigation", "law enforcement"]
            },
            "evidence_and_procedure": {
                "pages": ["Evidence_(law)", "Witness", "Search_and_seizure", "Forensics"],
                "keywords": ["evidence", "witness", "search", "forensics", "procedure"]
            },
            "penalties": {
                "pages": ["Punishment", "Prison", "Sentence_(law)", "Capital_punishment"],
                "keywords": ["punishment", "prison", "sentence", "penalty"]
            },
        },
        "tertiary": {
            "crime_news_language": {
                "pages": ["Crime", "Police", "Court"],
                "keywords": ["suspect", "charged", "detained", "case filed", "court order"]
            },
            "legal_reporting_terms": {
                "pages": ["Lawsuit", "Subpoena", "Injunction"],
                "keywords": ["lawsuit", "injunction", "legal notice", "petition"]
            },
            "general_legal_language": {
                "pages": ["Law", "Justice"],
                "keywords": ["legal action", "under the law", "authorities said"]
            },
        },
    },

    "sports": {
        "general_terms": [
            "sport", "team", "player", "match", "tournament", "league",
            "coach", "score", "season", "championship", "win", "competition"
        ],
        "primary": {
            "general_sport": {
                "pages": ["Sport", "Athletics_(sport)", "Sportsmanship", "Competition"],
                "keywords": ["sport", "athlete", "competition", "sportsmanship"]
            },
            "cricket": {
                "pages": ["Cricket", "Test_cricket", "One_Day_International", "Indian_Premier_League"],
                "keywords": ["cricket", "bat", "bowling", "wicket", "innings", "IPL"]
            },
            "football": {
                "pages": ["Association_football", "FIFA_World_Cup", "Premier_League", "UEFA_Champions_League"],
                "keywords": ["football", "soccer", "goal", "league", "club", "FIFA"]
            },
            "olympic_sports": {
                "pages": ["Olympic_Games", "Athletics_at_the_Summer_Olympics", "Swimming_(sport)", "Gymnastics"],
                "keywords": ["olympics", "medal", "athletics", "swimming", "gymnastics"]
            },
        },
        "secondary": {
            "basketball_tennis": {
                "pages": ["Basketball", "NBA", "Tennis", "Grand_Slam_(tennis)"],
                "keywords": ["basketball", "nba", "tennis", "grand slam"]
            },
            "team_sports_terms": {
                "pages": ["Coach_(sport)", "Team_sport", "League", "Tournament"],
                "keywords": ["coach", "team", "league", "tournament", "season"]
            },
            "performance_and_records": {
                "pages": ["World_record", "Ranking", "Playoffs"],
                "keywords": ["record", "ranking", "playoffs", "performance"]
            },
        },
        "tertiary": {
            "sports_news_language": {
                "pages": ["Sport", "Cricket", "Association_football"],
                "keywords": ["won the match", "defeated", "scored", "captain", "fixture"]
            },
            "event_terms": {
                "pages": ["Championship", "Cup", "Final_(competition)"],
                "keywords": ["championship", "final", "qualifier", "semi-final"]
            },
            "general_game_terms": {
                "pages": ["Game", "Competition"],
                "keywords": ["match result", "took the lead", "season opener"]
            },
        },
    },

    "entertainment": {
        "general_terms": [
            "entertainment", "film", "music", "television", "actor", "artist",
            "show", "movie", "cinema", "audience", "performance", "series"
        ],
        "primary": {
            "film": {
                "pages": ["Film", "Cinema", "Film_director", "Screenplay"],
                "keywords": ["film", "movie", "cinema", "director", "screenplay"]
            },
            "music": {
                "pages": ["Music", "Musician", "Album", "Song"],
                "keywords": ["music", "song", "album", "musician", "concert"]
            },
            "television": {
                "pages": ["Television", "Television_show", "Series_premiere", "Broadcasting"],
                "keywords": ["television", "series", "show", "broadcast", "episode"]
            },
            "performing_arts": {
                "pages": ["Performing_arts", "Theatre", "Dance", "Comedy"],
                "keywords": ["theatre", "performance", "dance", "stage", "comedy"]
            },
        },
        "secondary": {
            "animation_and_games": {
                "pages": ["Animation", "Anime", "Video_game", "Game_developer"],
                "keywords": ["animation", "anime", "video game", "game developer"]
            },
            "celebrity_media": {
                "pages": ["Celebrity", "Popular_culture", "Mass_media"],
                "keywords": ["celebrity", "popular culture", "media coverage"]
            },
            "radio_and_audio": {
                "pages": ["Radio", "Podcast", "Sound_recording_and_reproduction"],
                "keywords": ["radio", "podcast", "audio production"]
            },
        },
        "tertiary": {
            "entertainment_news_language": {
                "pages": ["Entertainment", "Film", "Music"],
                "keywords": ["released", "trailer", "box office", "cast", "fans", "streaming"]
            },
            "awards_terms": {
                "pages": ["Academy_Awards", "Grammy_Awards", "Emmy_Awards"],
                "keywords": ["awards", "nominated", "winner", "ceremony"]
            },
            "general_media_terms": {
                "pages": ["Entertainment", "Television"],
                "keywords": ["audience response", "premiere", "new season"]
            },
        },
    },

    "general_factual": {
        "general_terms": [
            "fact", "information", "evidence", "data", "reality", "truth",
            "report", "statement", "claim", "confirmed", "observed",
            "recorded", "documented", "known", "identified"
        ],
        "primary": {
            "knowledge": {
                "pages": ["Knowledge", "Information", "Fact", "Truth"],
                "keywords": ["knowledge", "information", "fact", "truth", "known"]
            },
            "evidence_reasoning": {
                "pages": ["Evidence", "Reason", "Critical_thinking", "Logic"],
                "keywords": ["evidence", "reason", "logic", "critical thinking", "verification"]
            },
            "data_and_records": {
                "pages": ["Data", "Record", "Observation", "Documentation"],
                "keywords": ["data", "record", "observation", "documented", "recorded"]
            },
        },
        "secondary": {
            "reference_material": {
                "pages": ["Encyclopedia", "Reference_work", "Archive", "Database"],
                "keywords": ["reference", "archive", "database", "encyclopedia"]
            },
            "communication_of_facts": {
                "pages": ["Report", "Journalism", "Source_(journalism)", "Verification_and_validation"],
                "keywords": ["report", "source", "verification", "confirmed", "stated"]
            },
            "measurement_and_description": {
                "pages": ["Measurement", "Classification", "Description"],
                "keywords": ["measured", "classified", "described", "identified"]
            },
        },
        "tertiary": {
            "general_claim_language": {
                "pages": ["Fact", "Information", "Evidence"],
                "keywords": ["according to reports", "it is known", "evidence suggests", "records indicate"]
            },
            "live_factcheck_terms": {
                "pages": ["Verification_and_validation", "Journalism", "Data"],
                "keywords": ["claim", "fact-check", "verified", "unverified", "evidence shows"]
            },
            "broad_reference_language": {
                "pages": ["Knowledge", "Reference_work"],
                "keywords": ["official data", "documented evidence", "available information"]
            },
        },
    },
}

# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def split_sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [normalize_whitespace(p) for p in parts if normalize_whitespace(p)]

def is_good_sentence(sent: str, min_words=8, max_words=45):
    if not sent:
        return False
    wc = len(sent.split())
    if wc < min_words or wc > max_words:
        return False
    if sent.endswith("?"):
        return False
    if re.search(r"\b(edit|citation needed|ISBN|doi|retrieved)\b", sent, re.I):
        return False
    return True

def make_contextual_chunks(text: str, min_sent=2, max_sent=4):
    sents = [s for s in split_sentences(text) if is_good_sentence(s)]
    chunks = []
    if len(sents) < min_sent:
        return chunks

    # sliding windows of 2..4 sentences for contextual passages
    for window in range(min_sent, max_sent + 1):
        for i in range(0, len(sents) - window + 1):
            chunk = " ".join(sents[i:i + window]).strip()
            if 35 <= len(chunk.split()) <= 140:
                chunks.append(chunk)

    # dedupe preserve order
    seen = set()
    uniq = []
    for c in chunks:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq

def keyword_matches(text: str, keywords):
    text_l = text.lower()
    matched = []
    for kw in keywords:
        if kw.lower() in text_l:
            matched.append(kw)
    return matched

def compute_score(text: str, general_terms, sublabel_keywords, relevance_level):
    text_l = text.lower()

    matched_general = keyword_matches(text_l, general_terms)
    matched_specific = keyword_matches(text_l, sublabel_keywords)

    score = 0.0
    score += len(matched_general) * 1.0
    score += len(matched_specific) * 2.5

    # Prefer contextual passages
    word_count = len(text.split())
    if 45 <= word_count <= 110:
        score += 2.0
    elif 35 <= word_count <= 140:
        score += 1.0

    # Relevance prior
    if relevance_level == "primary":
        score += 3.0
    elif relevance_level == "secondary":
        score += 2.0
    elif relevance_level == "tertiary":
        score += 1.0

    # factual/claimish language bonus
    factual_terms = [
        "according", "reported", "observed", "measured", "identified",
        "announced", "stated", "found", "evidence", "study", "official"
    ]
    score += sum(0.3 for t in factual_terms if t in text_l)

    return score, matched_general, matched_specific

# ============================================================
# WIKIPEDIA FETCHING
# ============================================================

def fetch_page_html(page_title):
    url = f"https://en.wikipedia.org/wiki/{page_title}"
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.text
            time.sleep(1.2 * (attempt + 1))
        except Exception:
            time.sleep(1.2 * (attempt + 1))
    return None

def extract_blocks_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", {"id": "mw-content-text"})
    if not content:
        return []

    blocks = []

    # Paragraphs
    for p in content.find_all("p"):
        txt = normalize_whitespace(p.get_text(" ", strip=True))
        if len(txt.split()) >= 20:
            blocks.append(txt)

    # List items
    for ul in content.find_all(["ul", "ol"]):
        items = []
        for li in ul.find_all("li", recursive=False):
            txt = normalize_whitespace(li.get_text(" ", strip=True))
            if 8 <= len(txt.split()) <= 40:
                items.append(txt)
        if len(items) >= 2:
            merged = " ".join(items[:6])
            if len(merged.split()) >= 30:
                blocks.append(merged)

    # Section-wise blocks
    headers = content.find_all(["h2", "h3"])
    for hdr in headers:
        section_texts = []
        sib = hdr.find_next_sibling()
        steps = 0
        while sib and sib.name not in ["h2", "h3"] and steps < 8:
            if sib.name == "p":
                txt = normalize_whitespace(sib.get_text(" ", strip=True))
                if len(txt.split()) >= 15:
                    section_texts.append(txt)
            steps += 1
            sib = sib.find_next_sibling()
        if section_texts:
            merged = " ".join(section_texts[:3])
            if len(merged.split()) >= 30:
                blocks.append(merged)

    # dedupe
    seen = set()
    uniq = []
    for b in blocks:
        key = b.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(b)
    return uniq

# ============================================================
# COLLECTION LOGIC
# ============================================================

def collect_records_for_page(context_class, level_name, sublabel_name, page_title, general_terms, sublabel_keywords):
    html = fetch_page_html(page_title)
    if not html:
        return []

    blocks = extract_blocks_from_html(html)
    page_records = []

    for block in blocks:
        chunks = make_contextual_chunks(block, min_sent=2, max_sent=4)
        if not chunks and 35 <= len(block.split()) <= 140:
            chunks = [block]

        for chunk in chunks:
            score, matched_general, matched_specific = compute_score(
                chunk, general_terms, sublabel_keywords, level_name
            )

            # strong enough threshold
            if score < 4.5:
                continue

            primary_label = sublabel_name if level_name == "primary" else ""
            secondary_label = sublabel_name if level_name == "secondary" else ""
            tertiary_label = sublabel_name if level_name == "tertiary" else ""

            page_records.append({
                "text": chunk,
                "context_class": context_class,
                "relevance_level": level_name,
                "primary_label": primary_label,
                "secondary_label": secondary_label,
                "tertiary_label": tertiary_label,
                "source_page": page_title,
                "matched_general_terms": ", ".join(sorted(set(matched_general))),
                "matched_specific_terms": ", ".join(sorted(set(matched_specific))),
                "score": round(score, 3),
                "source": "wikipedia"
            })

    return page_records

def dedupe_records(records):
    seen = set()
    out = []
    for r in records:
        key = (r["text"].lower(), r["context_class"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out

def balanced_sample(records, max_per_sublabel=None):
    if max_per_sublabel is None:
        return records

    bucket = defaultdict(list)
    for r in records:
        sub = r["primary_label"] or r["secondary_label"] or r["tertiary_label"]
        bucket[(r["context_class"], r["relevance_level"], sub)].append(r)

    final = []
    for _, items in bucket.items():
        items.sort(key=lambda x: x["score"], reverse=True)
        final.extend(items[:max_per_sublabel])
    return final

def collect_hierarchical_dataset(max_per_sublabel=120, save_every_class=True):
    all_records = []

    for context_class in FINAL_CONTEXT_CLASSES:
        print(f"\n[INFO] Collecting class: {context_class}")
        cfg = TAXONOMY[context_class]
        general_terms = cfg["general_terms"]
        class_records = []

        for level_name in ["primary", "secondary", "tertiary"]:
            level_data = cfg.get(level_name, {})
            for sublabel_name, subcfg in level_data.items():
                print(f"[INFO]  -> {level_name.upper()} / {sublabel_name}")
                pages = subcfg["pages"]
                keywords = subcfg["keywords"]

                sublabel_records = []
                for page in pages:
                    print(f"[INFO]      scraping {page}")
                    recs = collect_records_for_page(
                        context_class=context_class,
                        level_name=level_name,
                        sublabel_name=sublabel_name,
                        page_title=page,
                        general_terms=general_terms,
                        sublabel_keywords=keywords
                    )
                    sublabel_records.extend(recs)
                    time.sleep(REQUEST_DELAY)

                sublabel_records = dedupe_records(sublabel_records)
                sublabel_records.sort(key=lambda x: x["score"], reverse=True)

                if max_per_sublabel is not None:
                    sublabel_records = sublabel_records[:max_per_sublabel]

                print(f"[INFO]      kept {len(sublabel_records)} records")
                class_records.extend(sublabel_records)

        class_records = dedupe_records(class_records)
        class_records.sort(key=lambda x: x["score"], reverse=True)
        print(f"[INFO] Total for {context_class}: {len(class_records)}")
        all_records.extend(class_records)

        if save_every_class:
            pd.DataFrame(all_records).to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
            print(f"[INFO] Intermediate save: {OUTPUT_FILE}")

    all_records = dedupe_records(all_records)
    df = pd.DataFrame(all_records)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"\n[SUCCESS] Saved {len(df)} rows to {OUTPUT_FILE}")
    return df

# ============================================================
# OPTIONAL ANALYSIS
# ============================================================

def show_summary(df):
    print("\n===== SUMMARY BY CLASS =====")
    print(df["context_class"].value_counts())

    print("\n===== SUMMARY BY LEVEL =====")
    print(df["relevance_level"].value_counts())

    print("\n===== TOP SUBLABEL COUNTS =====")
    sub = []
    for _, row in df.iterrows():
        label = row["primary_label"] or row["secondary_label"] or row["tertiary_label"]
        sub.append(label)
    sub_df = pd.Series(sub)
    print(sub_df.value_counts().head(30))

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    df = collect_hierarchical_dataset(max_per_sublabel=120, save_every_class=True)
    show_summary(df)