import json
from collections import defaultdict

# Path to crawl4ai output (JSON)
CRAWL4AI_INPUT = "crawl4ai_output.json"  # Change this to your actual crawl4ai output file
RERANK_OUTPUT = "rerank_sample.json"

# Your 14 context topics
CONTEXT_TOPICS = [
    "SCIENCE", "HEALTH", "TECHNOLOGY", "HISTORY", "POLITICS_GOVERNMENT", "ECONOMICS_BUSINESS",
    "GEOGRAPHY", "SPACE_ASTRONOMY", "ENVIRONMENT_CLIMATE", "SOCIETY_CULTURE", "LAW_CRIME",
    "SPORTS", "ENTERTAINMENT", "GENERAL_FACTUAL"
]

# Helper: assign topic from crawl4ai label or keywords (fallback to GENERAL_FACTUAL)
def assign_topic(item):
    # Try direct label
    label = item.get("topic") or item.get("label")
    if label and label.upper() in CONTEXT_TOPICS:
        return label.upper()
    # Fallback: keyword search in title/content
    text = (item.get("title") or "") + " " + (item.get("content") or "")
    text = text.lower()
    for topic in CONTEXT_TOPICS:
        if topic.lower() in text:
            return topic
    return "GENERAL_FACTUAL"

def main():
    with open(CRAWL4AI_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Group by topic, deduplicate by claim
    claims_by_topic = defaultdict(dict)
    for item in data:
        claim = item.get("title") or item.get("claim") or item.get("headline")
        if not claim or len(claim) < 20:
            continue
        topic = assign_topic(item)
        # Use content/summary as evidence
        evidence = item.get("content") or item.get("summary") or item.get("text") or ""
        evidence_list = [evidence] if evidence else []
        # Deduplicate by claim text
        norm_claim = claim.strip().lower()
        if norm_claim not in claims_by_topic[topic]:
            claims_by_topic[topic][norm_claim] = {
                "claim": claim.strip(),
                "evidence_list": evidence_list
            }

    # Balance: at least 5 per topic if possible
    balanced = []
    for topic in CONTEXT_TOPICS:
        topic_claims = list(claims_by_topic[topic].values())
        if len(topic_claims) >= 5:
            balanced.extend(topic_claims[:5])
        else:
            balanced.extend(topic_claims)
            print(f"Warning: Only {len(topic_claims)} samples for topic '{topic}'")

    print(f"Total samples: {len(balanced)}")
    with open(RERANK_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(balanced, f, ensure_ascii=False, indent=2)
    print(f"Saved to {RERANK_OUTPUT}")

if __name__ == "__main__":
    main()
