import re


class ClaimDecomposer:
    def decompose(self, claim):
        text = " ".join((claim or "").strip().split())
        if not text:
            return []

        decomposed = []
        lowered = text.lower()

        both_match = re.match(r"^(?P<subject>.+?)\s+is\s+both\s+a[n]?\s+(?P<left>.+?)\s+and\s+a[n]?\s+(?P<right>.+?)$", lowered)
        if both_match:
            subject = both_match.group("subject").strip()
            left = both_match.group("left").strip()
            right = both_match.group("right").strip()
            decomposed.extend([
                f"{subject} is a {left}",
                f"{subject} is a {right}",
            ])

        only_match = re.match(
            r"^(?P<subject>.+?)\s+are\s+the\s+only\s+(?P<classname>.+?)\s+capable\s+of\s+(?P<capability>.+?)$",
            lowered,
        )
        if only_match:
            subject = only_match.group("subject").strip()
            classname = only_match.group("classname").strip()
            capability = only_match.group("capability").strip()
            decomposed.extend([
                f"{subject} are {classname}",
                f"{subject} are capable of {capability}",
                f"Only {classname} are capable of {capability}",
            ])

        largest_match = re.match(r"^(?P<subject>.+?)\s+is\s+the\s+(?P<rank>largest|biggest|smallest|oldest|youngest|farthest)\s+(?P<object>.+?)$", lowered)
        if largest_match:
            subject = largest_match.group("subject").strip()
            rank = largest_match.group("rank").strip()
            obj = largest_match.group("object").strip()
            decomposed.append(f"{subject} is the {rank} {obj}")
            if rank == "largest":
                decomposed.append(f"{subject} is the biggest {obj}")
            if rank == "biggest":
                decomposed.append(f"{subject} is the largest {obj}")

        dna_match = re.match(r"^(?P<subject>.+?)\s+share\s+about\s+(?P<value>.+?)\s+of\s+their\s+dna\s+with\s+(?P<object>.+?)$", lowered)
        if dna_match:
            subject = dna_match.group("subject").strip()
            value = dna_match.group("value").strip()
            obj = dna_match.group("object").strip()
            decomposed.extend([
                f"{subject} share {value} of their DNA with {obj}",
                f"{subject} share DNA with {obj}",
            ])

        return self._dedupe([item for item in decomposed if item and item != lowered])

    @staticmethod
    def _dedupe(items):
        out = []
        seen = set()
        for item in items:
            normalized = " ".join(item.split()).strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                out.append(" ".join(item.split()))
        return out
