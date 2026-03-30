import os
import re

import requests


class OpenFDAAPI:

    BASE_URL = "https://api.fda.gov"

    DRUG_KEYWORDS = {
        "drug", "medicine", "medication", "tablet", "capsule", "vaccine",
        "covid", "bleach", "cure", "treatment", "side effect", "fda",
    }
    FOOD_KEYWORDS = {"food", "recall", "contamination", "ingredient", "nutrition"}
    DEVICE_KEYWORDS = {"device", "implant", "pacemaker", "diagnostic", "test kit"}

    def __init__(self):
        self.api_key = (os.getenv("OPENFDA_API_KEY") or "").strip()

    def fetch(self, claim):
        endpoint = self._select_endpoint(claim)
        if endpoint is None:
            return None

        try:
            if endpoint == "drug/label.json":
                return self._fetch_drug_label(claim)
            if endpoint == "food/enforcement.json":
                return self._fetch_food_enforcement(claim)
            if endpoint == "device/classification.json":
                return self._fetch_device_classification(claim)
        except Exception as e:
            print("openFDA API error:", e)
        return None

    def _select_endpoint(self, claim):
        claim_lower = (claim or "").lower()
        if any(keyword in claim_lower for keyword in self.DRUG_KEYWORDS):
            return "drug/label.json"
        if any(keyword in claim_lower for keyword in self.FOOD_KEYWORDS):
            return "food/enforcement.json"
        if any(keyword in claim_lower for keyword in self.DEVICE_KEYWORDS):
            return "device/classification.json"
        return None

    def _request(self, path, params):
        if self.api_key:
            params = dict(params)
            params["api_key"] = self.api_key
        response = requests.get(f"{self.BASE_URL}/{path}", params=params, timeout=10)
        if response.status_code != 200:
            return None
        return response.json() or {}

    def _fetch_drug_label(self, claim):
        term = self._extract_topic(claim)
        data = self._request(
            "drug/label.json",
            {"search": f'openfda.brand_name:"{term}"', "limit": 1},
        )
        if not data:
            return None
        results = data.get("results") or []
        if not results:
            data = self._request("drug/label.json", {"search": term, "limit": 1})
            results = (data or {}).get("results") or []
        if not results:
            return None

        row = results[0]
        openfda = row.get("openfda") or {}
        brand = ", ".join(openfda.get("brand_name") or []) or term
        purpose = self._first_text(row, "purpose", "indications_and_usage", "warnings")
        if not purpose:
            return None
        return {
            "source": "openFDA",
            "url": "https://open.fda.gov/apis/drug/label/",
            "text": f"openFDA drug label for {brand}: {purpose[:400]}",
            "weight": 0.92,
        }

    def _fetch_food_enforcement(self, claim):
        term = self._extract_topic(claim)
        data = self._request("food/enforcement.json", {"search": term, "limit": 1})
        results = (data or {}).get("results") or []
        if not results:
            return None
        row = results[0]
        reason = (row.get("reason_for_recall") or "").strip()
        product = (row.get("product_description") or term).strip()
        if not reason and not product:
            return None
        return {
            "source": "openFDA",
            "url": "https://open.fda.gov/apis/food/enforcement/",
            "text": f"openFDA food enforcement record for {product}: {reason[:400]}",
            "weight": 0.92,
        }

    def _fetch_device_classification(self, claim):
        term = self._extract_topic(claim)
        data = self._request("device/classification.json", {"search": term, "limit": 1})
        results = (data or {}).get("results") or []
        if not results:
            return None
        row = results[0]
        name = (row.get("device_name") or term).strip()
        definition = (row.get("definition") or row.get("medical_specialty_description") or "").strip()
        if not definition:
            return None
        return {
            "source": "openFDA",
            "url": "https://open.fda.gov/apis/device/classification/",
            "text": f"openFDA device classification for {name}: {definition[:400]}",
            "weight": 0.92,
        }

    def _extract_topic(self, claim):
        cleaned = re.sub(r"[^A-Za-z0-9\\s-]", " ", claim or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        tokens = [token for token in cleaned.split() if token.lower() not in {
            "is", "are", "was", "were", "can", "does", "do", "did", "the", "a", "an",
            "and", "or", "of", "for", "to", "with", "without", "after", "before",
            "cures", "cause", "causes", "treats", "treatment", "claim", "claims",
        }]
        if not tokens:
            return cleaned or "drug"
        return " ".join(tokens[:5])

    def _first_text(self, row, *fields):
        for field in fields:
            value = row.get(field)
            if isinstance(value, list) and value:
                text = " ".join(str(item) for item in value if item)
                if text:
                    return text
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
