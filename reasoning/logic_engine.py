import re
import spacy


class LogicEngine:
    """Structured reasoning over claim/evidence to produce an auxiliary stance."""

    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            self.nlp = None

    def _extract_numbers(self, text):
        out = []
        for val in re.findall(r"\d+(?:\.\d+)?", text or ""):
            try:
                out.append(float(val))
            except Exception:
                continue
        return out

    def _numeric_signal(self, claim, evidence_list):
        c_nums = self._extract_numbers(claim)
        if not c_nums:
            return 0.0

        c = c_nums[0]
        all_e = []
        for ev in evidence_list:
            all_e.extend(self._extract_numbers(ev.get("text", "")))
        if not all_e:
            return 0.0

        nearest = min(all_e, key=lambda x: abs(x - c))
        rel_err = abs(nearest - c) / max(abs(c), 1.0)
        return max(min(0.7 - rel_err, 0.7), -0.7)

    def _entity_signal(self, claim, evidence_list):
        if not self.nlp:
            return 0.0

        c_doc = self.nlp(claim)
        c_ents = {e.text.lower() for e in c_doc.ents}
        if not c_ents:
            return 0.0

        overlaps = []
        for ev in evidence_list:
            e_doc = self.nlp(ev.get("text", ""))
            e_ents = {e.text.lower() for e in e_doc.ents}
            if not e_ents:
                continue
            overlaps.append(len(c_ents & e_ents) / max(len(c_ents), 1))

        if not overlaps:
            return 0.0
        avg = sum(overlaps) / len(overlaps)
        return max(min(avg - 0.4, 0.4), -0.4)

    def _consensus_signal(self, evidence_list):
        support = 0.0
        refute = 0.0
        for ev in evidence_list:
            probs = ev.get("probabilities", {})
            if probs:
                support += float(probs.get("SUPPORT", 0.0))
                refute += float(probs.get("REFUTE", 0.0))
            else:
                stance = ev.get("stance")
                conf = float(ev.get("confidence", 0.0))
                if stance == "SUPPORT":
                    support += conf
                elif stance == "REFUTE":
                    refute += conf
        total = support + refute
        if total == 0:
            return 0.0
        return (support - refute) / total

    def analyze(self, claim, evidence_list):
        score = 0.0
        score += self._numeric_signal(claim, evidence_list)
        score += self._entity_signal(claim, evidence_list)
        score += self._consensus_signal(evidence_list)

        if score > 0.8:
            return "SUPPORT"
        if score < -0.8:
            return "REFUTE"
        return None
