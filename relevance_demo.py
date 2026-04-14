from evidence.relevance import RelevanceScorer

examples = [
    {
        "claim": "The printing press was invented by Johannes Gutenberg",
        "positive": "Goldsmith and inventor Johannes Gutenberg was the first European to introduce the printing press with movable type.",
        "negatives": [
            "A printing press is a mechanical device for applying pressure to an inked surface resting upon a print medium.",
            "The invention and global spread of the printing press was one of the most influential events in the second millennium."
        ]
    },
    {
        "claim": "Octopuses have three hearts",
        "positive": "Octopuses have three hearts and blue blood.",
        "negatives": [
            "An octopus is a soft-bodied, eight-limbed mollusc of the order Octopoda.",
            "Octopuses are among the most intelligent and behaviourally diverse invertebrates."
        ]
    },
    {
        "claim": "Sharks are older than trees",
        "positive": "Shark-like fish existed hundreds of millions of years before the first trees appeared on Earth.",
        "negatives": [
            "Sharks are a group of cartilaginous fishes characterized by five to seven gill slits on each side.",
            "Modern sharks are classified within the division Selachii."
        ]
    },
    {
        "claim": "The United Nations was founded after World War II",
        "positive": "The United Nations was established in 1945 after the end of the Second World War.",
        "negatives": [
            "The United Nations is an intergovernmental organization focused on peace and security.",
            "The UN Charter sets out the purposes and principles of the organization."
        ]
    },
    {
        "claim": "Humans can breathe in space without equipment",
        "positive": "Humans cannot survive in the vacuum of space without pressurized life-support equipment.",
        "negatives": [
            "Humans are the most widespread species of primate.",
            "Humans have large brains compared to body size."
        ]
    }
]

scorer = RelevanceScorer()

for ex in examples:
    print(f"\nClaim: {ex['claim']}")
    print(f"  Positive: {ex['positive']}")
    pos_score = scorer.score(ex['claim'], ex['positive'])
    print(f"    Relevance score: {pos_score}")
    for neg in ex['negatives']:
        print(f"  Negative: {neg}")
        neg_score = scorer.score(ex['claim'], neg)
        print(f"    Relevance score: {neg_score}")
