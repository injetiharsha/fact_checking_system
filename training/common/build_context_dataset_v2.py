import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from claim_detection.context_taxonomy import CONTEXT_TAXONOMY
from training.common.utils import ensure_dir, stratified_split_records


LABEL_SLOTS = {
    "science": {
        "subjects": ["Researchers", "A study", "Scientists", "A lab report"],
        "verbs": ["found", "reported", "measured", "showed"],
        "objects": ["experimental results", "observations", "field samples", "measured effects"],
        "evidence": ["new data", "repeat testing", "peer-reviewed findings", "controlled analysis"],
    },
    "health": {
        "subjects": ["Doctors", "A hospital report", "Public-health researchers", "Clinicians"],
        "verbs": ["said", "reported", "warned", "found"],
        "objects": ["patient outcomes", "treatment results", "symptom patterns", "population health trends"],
        "evidence": ["clinical data", "hospital records", "medical guidance", "trial results"],
    },
    "technology": {
        "subjects": ["Engineers", "A platform company", "Developers", "A product team"],
        "verbs": ["said", "reported", "showed", "claimed"],
        "objects": ["software systems", "device behavior", "user-generated data", "network activity"],
        "evidence": ["system logs", "model outputs", "technical documentation", "product testing"],
    },
    "history": {
        "subjects": ["Historians", "An archive", "A historical review", "A museum record"],
        "verbs": ["showed", "reported", "documented", "argued"],
        "objects": ["past events", "archival material", "historical timelines", "documented records"],
        "evidence": ["archival sources", "translated records", "historical accounts", "dated evidence"],
    },
    "politics_government": {
        "subjects": ["Lawmakers", "A ministry", "Government officials", "A parliamentary committee"],
        "verbs": ["said", "announced", "debated", "proposed"],
        "objects": ["public measures", "official decisions", "policy changes", "administrative actions"],
        "evidence": ["official notices", "committee records", "government briefings", "policy documents"],
    },
    "economics_business": {
        "subjects": ["An earnings report", "Company executives", "Market analysts", "A business filing"],
        "verbs": ["said", "reported", "showed", "forecast"],
        "objects": ["revenue trends", "market performance", "company guidance", "economic indicators"],
        "evidence": ["financial statements", "market data", "quarterly filings", "business disclosures"],
    },
    "geography": {
        "subjects": ["A reference source", "Geographers", "A map review", "An atlas entry"],
        "verbs": ["shows", "states", "indicates", "reports"],
        "objects": ["place features", "geographic boundaries", "physical landmarks", "regional traits"],
        "evidence": ["maps", "survey records", "reference tables", "geographic descriptions"],
    },
    "space_astronomy": {
        "subjects": ["Astronomers", "A space agency", "Observatory data", "A mission update"],
        "verbs": ["reported", "showed", "confirmed", "measured"],
        "objects": ["celestial observations", "orbital behavior", "space mission data", "planetary features"],
        "evidence": ["telescope data", "mission records", "spectral analysis", "observation logs"],
    },
    "environment_climate": {
        "subjects": ["Climate researchers", "An environmental report", "Scientists", "Field monitoring teams"],
        "verbs": ["reported", "showed", "warned", "measured"],
        "objects": ["ecosystem changes", "weather extremes", "pollution effects", "emissions trends"],
        "evidence": ["monitoring data", "impact assessments", "field measurements", "climate records"],
    },
    "society_culture": {
        "subjects": ["A census report", "Educators", "Community leaders", "Social researchers"],
        "verbs": ["reported", "said", "showed", "documented"],
        "objects": ["population trends", "cultural practices", "education outcomes", "social conditions"],
        "evidence": ["survey data", "community records", "education reports", "demographic tables"],
    },
    "law_crime": {
        "subjects": ["A court filing", "Regulators", "Police records", "A legal complaint"],
        "verbs": ["said", "alleged", "showed", "stated"],
        "objects": ["legal disputes", "enforcement actions", "criminal allegations", "compliance duties"],
        "evidence": ["court records", "legal orders", "complaint documents", "regulatory filings"],
    },
    "sports": {
        "subjects": ["A league update", "Coaches", "Sports reporters", "Team officials"],
        "verbs": ["said", "reported", "confirmed", "announced"],
        "objects": ["match outcomes", "player performance", "competition rules", "season standings"],
        "evidence": ["match statistics", "league records", "score reports", "competition schedules"],
    },
    "entertainment": {
        "subjects": ["A studio", "Entertainment reporters", "Platform executives", "A release update"],
        "verbs": ["said", "reported", "announced", "showed"],
        "objects": ["audience behavior", "release schedules", "game updates", "media performance"],
        "evidence": ["release notes", "audience metrics", "platform updates", "media coverage"],
    },
    "general_factual": {
        "subjects": ["A reference source", "An encyclopedia entry", "A textbook", "A fact sheet"],
        "verbs": ["states", "shows", "describes", "lists"],
        "objects": ["basic properties", "general facts", "standard definitions", "reference details"],
        "evidence": ["reference material", "basic descriptions", "standard definitions", "factual summaries"],
    },
}

SUBCATEGORY_KEYWORDS = {
    "science": {
        "physics": ["energy transfer", "force and motion", "wave behavior", "thermal properties"],
        "chemistry": ["chemical reactions", "compound structure", "acid-base balance", "molecular bonding"],
        "biology": ["cell behavior", "genetic traits", "organism growth", "species adaptation"],
        "earth_science": ["tectonic movement", "soil layers", "rock formation", "atmospheric cycles"],
        "environmental_science": ["ecosystem monitoring", "habitat stress", "resource use", "ecological sampling"],
        "materials_science": ["alloy strength", "material fatigue", "conductive properties", "surface composition"],
        "scientific_consensus": ["expert agreement", "reviewed evidence", "consensus findings", "established evidence"],
    },
    "health": {
        "medicine": ["prescription use", "dosage guidance", "symptom relief", "clinical treatment"],
        "public_health": ["community spread", "vaccination coverage", "health services", "population risk"],
        "nutrition": ["diet quality", "nutrient intake", "food balance", "dietary guidance"],
        "epidemiology": ["infection rates", "case trends", "risk factors", "disease spread"],
        "toxicology": ["poison exposure", "toxic effects", "chemical ingestion", "hazard warnings"],
        "disease_treatment": ["treatment response", "recovery time", "drug effectiveness", "care protocols"],
        "mental_health": ["anxiety symptoms", "mood changes", "behavioral health", "mental-health care"],
    },
    "technology": {
        "telecom": ["wireless coverage", "mobile towers", "signal quality", "network traffic"],
        "internet": ["broadband access", "online services", "server outages", "platform connectivity"],
        "software_ai": ["machine-learning systems", "vision models", "training data", "automated tools"],
        "hardware": ["device performance", "battery life", "chip design", "sensor accuracy"],
        "cybersecurity": ["security alerts", "data breaches", "malware activity", "account protection"],
        "social_media": ["content ranking", "recommendation systems", "user engagement", "platform moderation"],
    },
    "history": {
        "ancient_history": ["ancient kingdoms", "archaeological remains", "classical records", "ancient trade"],
        "modern_history": ["modern reforms", "industrial change", "twentieth-century events", "archived speeches"],
        "wars_conflicts": ["battle records", "military campaigns", "war casualties", "conflict timelines"],
        "historical_events": ["major events", "dated milestones", "public commemorations", "turning points"],
        "diplomacy_treaties": ["treaty terms", "peace agreements", "diplomatic meetings", "negotiated settlements"],
        "historical_figures": ["public leaders", "documented biographies", "recorded speeches", "historical influence"],
    },
    "politics_government": {
        "elections": ["vote counts", "ballot access", "campaign rules", "polling procedures"],
        "public_policy": ["policy rollout", "program funding", "public services", "administrative rules"],
        "foreign_affairs": ["diplomatic talks", "border issues", "international agreements", "foreign policy"],
        "legislation": ["bill language", "legislative votes", "committee changes", "statutory updates"],
        "governance": ["executive authority", "agency oversight", "cabinet decisions", "public administration"],
        "political_statements": ["campaign rhetoric", "party messaging", "official remarks", "public criticism"],
    },
    "economics_business": {
        "macroeconomics": ["GDP growth", "economic output", "recession risk", "national demand"],
        "finance": ["interest rates", "credit conditions", "bank lending", "bond yields"],
        "trade": ["export volumes", "import costs", "tariff changes", "trade balances"],
        "corporate_claims": ["quarterly revenue", "company guidance", "earnings calls", "active users"],
        "labor_inflation": ["wage growth", "job markets", "consumer prices", "inflation pressure"],
        "markets": ["stock performance", "market volatility", "investor sentiment", "index movement"],
    },
    "geography": {
        "countries": ["national borders", "country size", "territorial claims", "country rankings"],
        "continents": ["continental area", "regional placement", "landmass size", "continent comparisons"],
        "capitals_borders": ["capital cities", "border lines", "administrative capitals", "neighboring states"],
        "rivers_lakes": ["river systems", "lake depth", "water basins", "drainage routes"],
        "mountains": ["elevation records", "mountain ranges", "peak height", "summit location"],
        "climate_regions": ["desert belts", "monsoon regions", "polar zones", "tropical climates"],
    },
    "space_astronomy": {
        "planets": ["planetary atmospheres", "surface conditions", "orbital patterns", "planet composition"],
        "moons": ["moon orbits", "tidal effects", "satellite counts", "moon geology"],
        "stars": ["stellar temperature", "star formation", "luminosity", "stellar classification"],
        "space_missions": ["mission timelines", "launch vehicles", "lunar landings", "orbital probes"],
        "planetary_science": ["crater studies", "surface minerals", "planetary weather", "magnetic fields"],
        "cosmology": ["galaxy formation", "dark matter", "cosmic expansion", "early universe models"],
    },
    "environment_climate": {
        "climate_change": ["warming trends", "emissions pathways", "temperature records", "carbon outputs"],
        "biodiversity": ["species loss", "habitat decline", "conservation status", "ecosystem diversity"],
        "pollution": ["air quality", "water contamination", "plastic waste", "industrial emissions"],
        "disasters_weather": ["storm damage", "flood risk", "heat waves", "extreme rainfall"],
        "sustainability": ["renewable energy", "resource efficiency", "recycling systems", "low-carbon planning"],
        "ecological_impacts": ["forest loss", "soil erosion", "coastal damage", "ecosystem disruption"],
    },
    "society_culture": {
        "religion": ["religious practice", "faith communities", "worship traditions", "sacred observance"],
        "education": ["school enrollment", "classroom policy", "student outcomes", "curriculum changes"],
        "demographics": ["population growth", "migration patterns", "age distribution", "urbanization"],
        "social_issues": ["housing access", "income gaps", "public safety concerns", "community support"],
        "language_identity": ["language policy", "identity claims", "official language use", "cultural recognition"],
        "customs_traditions": ["festival practices", "traditional dress", "community rituals", "local customs"],
    },
    "law_crime": {
        "courts": ["court rulings", "appeal hearings", "judicial review", "trial decisions"],
        "regulation": ["industry rules", "agency enforcement", "regulatory notices", "compliance standards"],
        "constitutional_issues": ["constitutional rights", "federal authority", "judicial limits", "legal challenges"],
        "criminal_cases": ["criminal charges", "arrest reports", "investigation updates", "case evidence"],
        "rights_compliance": ["privacy rights", "data protection", "labor compliance", "civil-rights duties"],
    },
    "sports": {
        "teams": ["team form", "club strategy", "roster changes", "season performance"],
        "athletes": ["player fitness", "individual records", "transfer news", "athlete preparation"],
        "tournaments": ["bracket results", "tournament format", "qualifying rounds", "event scheduling"],
        "records": ["scoring records", "career milestones", "historic wins", "performance marks"],
        "rules": ["offside calls", "eligibility rules", "disciplinary action", "competition regulations"],
    },
    "entertainment": {
        "film": ["box office totals", "casting changes", "release plans", "festival screenings"],
        "television": ["season renewals", "episode ratings", "broadcast schedules", "series finales"],
        "music": ["album releases", "tour dates", "chart rankings", "stream counts"],
        "celebrity": ["public appearances", "celebrity statements", "award coverage", "fan reactions"],
        "gaming": ["player counts", "game patches", "studio updates", "launch performance"],
        "streaming_media": ["subscriber totals", "platform catalogs", "viewing trends", "streaming releases"],
    },
    "general_factual": {
        "encyclopedic": ["reference summaries", "basic descriptions", "general definitions", "introductory facts"],
        "entity_property": ["physical properties", "entity traits", "standard characteristics", "named features"],
        "general_news": ["widely reported facts", "general updates", "basic event descriptions", "public information"],
    },
}

LABEL_TEMPLATES = {
    "science": [
        "{subject} {verb} that {keyword} changed according to {evidence}.",
        "{evidence} linked {keyword} to {obj} in a science-focused claim.",
        "A claim about {keyword} relied on {evidence} and {obj}.",
    ],
    "health": [
        "{subject} {verb} that {keyword} affected {obj} based on {evidence}.",
        "A health claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} was used to discuss {keyword} and related {obj}.",
    ],
    "technology": [
        "{subject} {verb} that {keyword} improved {obj} using {evidence}.",
        "A technology claim about {keyword} referenced {evidence} and {obj}.",
        "{evidence} described how {keyword} shaped {obj}.",
    ],
    "history": [
        "{subject} {verb} that {keyword} explained {obj} through {evidence}.",
        "A historical claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} was used to interpret {keyword} and related {obj}.",
    ],
    "politics_government": [
        "{subject} {verb} that {keyword} changed {obj} according to {evidence}.",
        "A government claim about {keyword} pointed to {evidence} and {obj}.",
        "{evidence} was used in debate over {keyword} and {obj}.",
    ],
    "economics_business": [
        "{subject} {verb} that {keyword} influenced {obj} based on {evidence}.",
        "A business claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} was used to describe {keyword} and related {obj}.",
    ],
    "geography": [
        "{subject} {verb} that {keyword} described {obj} using {evidence}.",
        "A geography claim about {keyword} relied on {evidence} and {obj}.",
        "{evidence} was used to explain {keyword} and nearby {obj}.",
    ],
    "space_astronomy": [
        "{subject} {verb} that {keyword} shaped {obj} according to {evidence}.",
        "A space claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} was used to analyze {keyword} and related {obj}.",
    ],
    "environment_climate": [
        "{subject} {verb} that {keyword} affected {obj} based on {evidence}.",
        "An environment claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} connected {keyword} with {obj} in a climate-related claim.",
    ],
    "society_culture": [
        "{subject} {verb} that {keyword} influenced {obj} using {evidence}.",
        "A society claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} was used to discuss {keyword} and broader {obj}.",
    ],
    "law_crime": [
        "{subject} {verb} that {keyword} affected {obj} according to {evidence}.",
        "A legal claim about {keyword} relied on {evidence} and {obj}.",
        "{evidence} was cited in a dispute over {keyword} and {obj}.",
    ],
    "sports": [
        "{subject} {verb} that {keyword} changed {obj} based on {evidence}.",
        "A sports claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} was used to describe {keyword} and match-level {obj}.",
    ],
    "entertainment": [
        "{subject} {verb} that {keyword} influenced {obj} using {evidence}.",
        "An entertainment claim about {keyword} cited {evidence} and {obj}.",
        "{evidence} was used to discuss {keyword} and media-related {obj}.",
    ],
    "general_factual": [
        "{subject} {verb} that {keyword} described {obj} using {evidence}.",
        "A factual claim about {keyword} relied on {evidence} and {obj}.",
        "{evidence} summarized {keyword} and related {obj}.",
    ],
}

STATE_EXAMPLES = ["tamil_nadu", "maharashtra", "karnataka", "delhi", "california", "texas"]


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def infer_risk_flags(label: str, subcategory: str, keyword: str) -> list[str]:
    flags = []
    lowered = keyword.lower()
    if label == "health" and subcategory in {"toxicology", "disease_treatment", "medicine"}:
        flags.append("medical_safety")
    if label == "politics_government" and subcategory == "elections":
        flags.append("election_sensitive")
    if label in {"space_astronomy", "environment_climate", "technology", "health"} and any(
        term in lowered for term in ["lunar", "carbon", "infection", "security"]
    ):
        flags.append("misinformation_sensitive")
    return sorted(set(flags))


def generate_examples(label: str, subcategory: str, per_subcategory: int) -> list[dict]:
    slots = LABEL_SLOTS[label]
    keywords = SUBCATEGORY_KEYWORDS[label][subcategory]
    templates = LABEL_TEMPLATES[label]
    rows = []
    for idx in range(per_subcategory):
        subject = slots["subjects"][idx % len(slots["subjects"])]
        verb = slots["verbs"][idx % len(slots["verbs"])]
        obj = slots["objects"][idx % len(slots["objects"])]
        evidence = slots["evidence"][idx % len(slots["evidence"])]
        keyword = keywords[idx % len(keywords)]
        template = templates[idx % len(templates)]
        text = template.format(subject=subject, verb=verb, obj=obj, evidence=evidence, keyword=keyword)
        row = {
            "text": text,
            "label": label,
            "subcategory": subcategory,
            "risk_flags": infer_risk_flags(label, subcategory, keyword),
            "state_focus": None,
            "source": "v2_keyword_generated",
            "confidence_hint": 0.88,
            "keyword_signals": [label, subcategory, keyword],
        }
        if label == "politics_government" and subcategory == "public_policy" and idx == per_subcategory - 1:
            row["risk_flags"] = sorted(set(row["risk_flags"] + ["regional_local_claim"]))
            row["state_focus"] = STATE_EXAMPLES[idx % len(STATE_EXAMPLES)]
        rows.append(row)
    return rows


def build_records(base_records: list[dict], per_subcategory: int) -> list[dict]:
    seen = {normalize_text(row.get("text", "")) for row in base_records}
    merged = list(base_records)
    next_id = len(merged) + 1

    for label, meta in CONTEXT_TAXONOMY.items():
        for subcategory in meta["subcategories"]:
            for row in generate_examples(label, subcategory, per_subcategory):
                normalized = normalize_text(row["text"])
                if normalized in seen:
                    continue
                seen.add(normalized)
                merged.append({"id": f"context_v2_{next_id}", **row})
                next_id += 1
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v2 context dataset from v1 plus generic keyword-driven expansions.")
    parser.add_argument("--input-dir", default="data/context/v1")
    parser.add_argument("--output-dir", default="data/context/v2")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-subcategory", type=int, default=6)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = ensure_dir(args.output_dir)

    base_records = load_jsonl(input_dir / "dataset.jsonl")
    merged = build_records(base_records, per_subcategory=args.per_subcategory)

    random.seed(args.seed)
    random.shuffle(merged)
    train_rows, val_rows, test_rows = stratified_split_records(
        merged,
        label_key="label",
        validation_ratio=0.15,
        test_ratio=0.15,
    )

    for file_name, rows in (
        ("train.jsonl", train_rows),
        ("validation.jsonl", val_rows),
        ("test.jsonl", test_rows),
        ("dataset.jsonl", merged),
    ):
        output_path = output_dir / file_name
        with output_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, {len(test_rows)} test rows to {output_dir}"
    )


if __name__ == "__main__":
    main()
