# verdict/evidence_report.py

class EvidenceReport:

    def __init__(self):
        pass

    def summarize(self, evidence_list):

        supporting = []
        refuting = []

        for ev in evidence_list:
            if ev["stance"] == "SUPPORT":
                supporting.append(ev["source"])
            elif ev["stance"] == "REFUTE":
                refuting.append(ev["source"])

        return {
            "supporting_sources": supporting,
            "refuting_sources": refuting
        }
