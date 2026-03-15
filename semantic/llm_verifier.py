import json
import os
import re
from typing import Optional

import requests


class LLMVerifier:
    def __init__(self):
        self.enabled = os.getenv("ENABLE_LLM_VERIFIER", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.api_key = os.getenv("LLM_VERIFIER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.api_base = (os.getenv("LLM_VERIFIER_API_BASE") or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("LLM_VERIFIER_MODEL", "gpt-4o-mini")
        self.timeout = float(os.getenv("LLM_VERIFIER_TIMEOUT_SECONDS", "45"))
        self.max_context_chars = int(os.getenv("LLM_VERIFIER_MAX_CONTEXT_CHARS", "1200"))
        self.policy = os.getenv("LLM_VERIFIER_POLICY", "neutral_only").strip().lower()
        self.max_items = max(1, int(os.getenv("LLM_VERIFIER_MAX_ITEMS", "3")))
        self.provider_name = os.getenv("LLM_VERIFIER_PROVIDER", "openai_compatible")

    @property
    def available(self):
        return self.enabled and bool(self.api_key)

    def should_verify(self, evidence_index: int, current_stance: Optional[str] = None):
        if not self.available:
            return False
        if evidence_index >= self.max_items:
            return False
        if self.policy == "all":
            return True
        return (current_stance or "").upper() == "NEUTRAL"

    def verify(self, claim: str, sentence_text: str, context_text: Optional[str] = None):
        if not self.available:
            raise RuntimeError("LLM verifier is not configured")

        evidence = (context_text or sentence_text or "").strip()
        if len(evidence) > self.max_context_chars:
            evidence = evidence[: self.max_context_chars].rsplit(" ", 1)[0]

        system_prompt = (
            "You are a strict fact-verification judge. "
            "Use only the provided evidence. "
            "If the evidence directly supports the claim, return SUPPORT. "
            "If the evidence directly contradicts the claim, return REFUTE. "
            "If the evidence is indirect, about reported opinions, or insufficient, return NEUTRAL. "
            "Do not rely on outside knowledge. Return JSON only."
        )
        user_prompt = (
            f"Claim: {claim}\n\n"
            f"Evidence: {evidence}\n\n"
            "Return exactly one JSON object with keys: stance, confidence, rationale. "
            "stance must be one of SUPPORT, REFUTE, NEUTRAL. confidence must be a number between 0 and 1."
        )

        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.api_base}/chat/completions"
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        parsed = self._parse_json(content)
        stance = str(parsed.get("stance", "NEUTRAL")).upper().strip()
        if stance not in {"SUPPORT", "REFUTE", "NEUTRAL"}:
            stance = "NEUTRAL"
        try:
            confidence = float(parsed.get("confidence", 0.5))
        except Exception:
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        rationale = str(parsed.get("rationale", "")).strip()
        return {
            "stance": stance,
            "confidence": round(confidence, 3),
            "source": f"llm_verifier:{self.provider_name}:{self.model}",
            "rationale": rationale[:240],
        }

    @staticmethod
    def _parse_json(content: str):
        text = (content or "").strip()
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("LLM verifier returned non-JSON content")
