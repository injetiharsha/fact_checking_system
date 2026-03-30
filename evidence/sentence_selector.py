# evidence/sentence_selector.py

import re


class SentenceSelector:
    """
    Extracts the most relevant sentence from scraped evidence
    to improve stance detection accuracy.
    """

    def __init__(self, relevance_scorer):
        self.relevance_scorer = relevance_scorer

    def extract(self, claim, text):
        """
        Select the best sentence from a document based on semantic similarity
        and simple keyword boosts.

        Parameters
        ----------
        claim : str
            The claim being fact-checked.

        text : str
            Full scraped document text.

        Returns
        -------
        str or None
            Best sentence candidate for stance detection.
        """

        if not text:
            return None

        sentences = self._split_sentences(text)

        best_sentence = None
        best_score = 0

        claim_words = set(claim.lower().split())

        for sentence in sentences:

            sentence = sentence.strip()

            if not self._valid_sentence(sentence):
                continue

            score = self.relevance_scorer.score(claim, sentence)

            # Boost sentences containing claim keywords
            sentence_words = set(sentence.lower().split())
            overlap = len(claim_words & sentence_words)

            score += overlap * 0.05

            if score > best_score:
                best_score = score
                best_sentence = sentence

        return best_sentence

    def _split_sentences(self, text):
        """
        Basic sentence segmentation.
        """
        return re.split(r"[.!?]\s+", text)

    def _valid_sentence(self, sentence):
        """
        Filters out sentences that are too short or too long.
        """

        words = sentence.split()

        if len(words) < 6:
            return False

        if len(words) > 80:
            return False

        return True