# verdict/aggregate.py

from verdict.final_report import FinalVerdictEngine


def aggregate_results(evidence_list):

    engine = FinalVerdictEngine()

    return engine.decide(evidence_list)
