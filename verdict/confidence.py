# verdict/confidence.py

from collections import Counter


class ConfidenceCalculator:

    def __init__(self):
        pass

    def calculate(self, support_score, refute_score, score_gap_threshold=0.15, evidence_list=None):

        total = support_score + refute_score

        if total == 0:
            return 0

        raw = abs(support_score - refute_score) / total

        # Penalize close-score situations to avoid overconfident outputs.
        gap = abs(support_score - refute_score)
        if gap < score_gap_threshold:
            raw *= 0.75

        source_penalty = 1.0
        if evidence_list:
            domains = []
            for item in evidence_list:
                url = str((item or {}).get("url") or "").strip()
                if not url or url.startswith("internal://"):
                    continue
                try:
                    domain = url.split("//", 1)[1].split("/", 1)[0].lower()
                except Exception:
                    continue
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain:
                    domains.append(domain)

            if len(domains) > 1:
                total_items = len(domains)
                counts = Counter(domains)
                top_share = max(counts.values()) / total_items

                count_penalty = max(0.84, 1.0 - min(0.18, 0.03 * (total_items - 1)))
                concentration_penalty = 1.0 - min(0.10, max(0.0, top_share - (1.0 / total_items)) * 0.25)
                source_penalty = count_penalty * concentration_penalty

        raw *= source_penalty

        return round(raw, 3)
