from typing import Dict, List

CONTEXT_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "science": {
        "subcategories": [
            "physics",
            "chemistry",
            "biology",
            "earth_science",
            "environmental_science",
            "materials_science",
            "scientific_consensus",
        ]
    },
    "health": {
        "subcategories": [
            "medicine",
            "public_health",
            "nutrition",
            "epidemiology",
            "toxicology",
            "disease_treatment",
            "mental_health",
        ]
    },
    "technology": {
        "subcategories": [
            "telecom",
            "internet",
            "software_ai",
            "hardware",
            "cybersecurity",
            "social_media",
        ]
    },
    "history": {
        "subcategories": [
            "ancient_history",
            "modern_history",
            "wars_conflicts",
            "historical_events",
            "diplomacy_treaties",
            "historical_figures",
        ]
    },
    "politics_government": {
        "subcategories": [
            "elections",
            "public_policy",
            "foreign_affairs",
            "legislation",
            "governance",
            "political_statements",
        ]
    },
    "economics_business": {
        "subcategories": [
            "macroeconomics",
            "finance",
            "trade",
            "corporate_claims",
            "labor_inflation",
            "markets",
        ]
    },
    "geography": {
        "subcategories": [
            "countries",
            "continents",
            "capitals_borders",
            "rivers_lakes",
            "mountains",
            "climate_regions",
        ]
    },
    "space_astronomy": {
        "subcategories": [
            "planets",
            "moons",
            "stars",
            "space_missions",
            "planetary_science",
            "cosmology",
        ]
    },
    "environment_climate": {
        "subcategories": [
            "climate_change",
            "biodiversity",
            "pollution",
            "disasters_weather",
            "sustainability",
            "ecological_impacts",
        ]
    },
    "society_culture": {
        "subcategories": [
            "religion",
            "education",
            "demographics",
            "social_issues",
            "language_identity",
            "customs_traditions",
        ]
    },
    "law_crime": {
        "subcategories": [
            "courts",
            "regulation",
            "constitutional_issues",
            "criminal_cases",
            "rights_compliance",
        ]
    },
    "sports": {
        "subcategories": [
            "teams",
            "athletes",
            "tournaments",
            "records",
            "rules",
        ]
    },
    "entertainment": {
        "subcategories": [
            "film",
            "television",
            "music",
            "celebrity",
            "gaming",
            "streaming_media",
        ]
    },
    "general_factual": {
        "subcategories": [
            "encyclopedic",
            "entity_property",
            "general_news",
        ]
    },
}

RISK_FLAGS = [
    "misinformation_sensitive",
    "medical_safety",
    "election_sensitive",
    "regional_local_claim",
]

INDIA_STATE_ALIASES: Dict[str, List[str]] = {
    "andhra_pradesh": ["andhra pradesh", "ap", "amaravati", "visakhapatnam"],
    "arunachal_pradesh": ["arunachal pradesh", "itanagar"],
    "assam": ["assam", "guwahati", "dispur"],
    "bihar": ["bihar", "patna"],
    "chhattisgarh": ["chhattisgarh", "raipur"],
    "goa": ["goa", "panaji", "margao"],
    "gujarat": ["gujarat", "gandhinagar", "ahmedabad", "surat"],
    "haryana": ["haryana", "chandigarh", "gurugram", "faridabad"],
    "himachal_pradesh": ["himachal pradesh", "shimla"],
    "jharkhand": ["jharkhand", "ranchi"],
    "karnataka": ["karnataka", "bengaluru", "mysuru", "mangalore"],
    "kerala": ["kerala", "thiruvananthapuram", "kochi", "kozhikode"],
    "madhya_pradesh": ["madhya pradesh", "bhopal", "indore"],
    "maharashtra": ["maharashtra", "mumbai", "pune", "nagpur"],
    "manipur": ["manipur", "imphal"],
    "meghalaya": ["meghalaya", "shillong"],
    "mizoram": ["mizoram", "aizawl"],
    "nagaland": ["nagaland", "kohima"],
    "odisha": ["odisha", "orissa", "bhubaneswar", "cuttack"],
    "punjab": ["punjab", "chandigarh", "amritsar", "ludhiana"],
    "rajasthan": ["rajasthan", "jaipur", "jodhpur", "udaipur"],
    "sikkim": ["sikkim", "gangtok"],
    "tamil_nadu": ["tamil nadu", "chennai", "coimbatore", "madurai"],
    "telangana": ["telangana", "hyderabad", "warangal"],
    "tripura": ["tripura", "agartala"],
    "uttar_pradesh": ["uttar pradesh", "up", "lucknow", "kanpur", "varanasi"],
    "uttarakhand": ["uttarakhand", "dehradun"],
    "west_bengal": ["west bengal", "kolkata", "howrah", "siliguri"],
    "delhi": ["delhi", "new delhi", "nct of delhi"],
    "jammu_and_kashmir": ["jammu and kashmir", "srinagar", "jammu"],
    "ladakh": ["ladakh", "leh", "kargil"],
    "puducherry": ["puducherry", "pondicherry"],
    "chandigarh": ["chandigarh"],
    "andaman_and_nicobar": ["andaman", "nicobar", "port blair"],
    "dadra_and_nagar_haveli_and_daman_and_diu": ["daman", "diu", "dadra", "nagar haveli"],
    "lakshadweep": ["lakshadweep"],
}
