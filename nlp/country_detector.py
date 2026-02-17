import spacy
import pycountry

class CountryDetector:

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def detect(self, text):
        doc = self.nlp(text)

        for ent in doc.ents:
            if ent.label_ == "GPE":
                try:
                    country = pycountry.countries.lookup(ent.text)
                    return country.alpha_3
                except:
                    continue

        return None
