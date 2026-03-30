import json
import time


class PipelineTrace:

    def __init__(self, claim):

        self.data = {
            "claim": claim,
            "timestamp": time.time(),
            "search_results": [],
            "scraped_pages": [],
            "sentence_candidates": [],
            "selected_sentences": [],
            "evidence_scoring": [],
            "stance_predictions": [],
            "final_result": None
        }

    # store search results
    def add_search_result(self, title, url):

        self.data["search_results"].append({
            "title": title,
            "url": url
        })

        self.data["timings"] = []

    # store scraped page info (file saved separately)
    def add_scraped_page(self, url, file_path, word_count, preview):

        self.data["scraped_pages"].append({
            "url": url,
            "file": file_path,
            "word_count": word_count,
            "preview": preview
        })

    # store sentence candidates per page
    def add_sentence_candidates(self, url, sentences):

        self.data["sentence_candidates"].append({
            "url": url,
            "candidates": sentences[:5]
        })

    # store chosen evidence sentence
    def add_selected_sentence(self, url, sentence):

        self.data["selected_sentences"].append({
            "url": url,
            "sentence": sentence
        })

    # store scoring info
    def add_evidence_score(self, url, relevance, quality):

        self.data["evidence_scoring"].append({
            "url": url,
            "relevance": relevance,
            "quality": quality
        })

    # store stance prediction
    def add_stance(self, url, stance, confidence):

        self.data["stance_predictions"].append({
            "url": url,
            "stance": stance,
            "confidence": confidence
        })

    # final verdict
    def set_final_result(self, verdict, confidence):

        self.data["final_result"] = {
            "verdict": verdict,
            "confidence": confidence
        }

    # save trace file
    def save(self, filename="logs/pipeline_trace.json"):

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)