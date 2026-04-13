import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests


class LLMVerifier:
    _RATE_STATE_PATH = Path("logs/llm_verifier_rpm_state.json")
    _RATE_LOCK_DIR = Path("logs/llm_verifier_rpm_state.lock")
    _LOCK_STALE_SECONDS = 180.0

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
        self.max_requests_per_minute = max(1, int(os.getenv("LLM_VERIFIER_MAX_REQUESTS_PER_MINUTE", "20")))
        self._RATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

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

        self._acquire_global_rate_slot()

        evidence = (context_text or sentence_text or "").strip()
        if len(evidence) > self.max_context_chars:
            evidence = evidence[: self.max_context_chars].rsplit(" ", 1)[0]

        system_prompt = (
            "You are a strict fact-verification judge. "
            "Use only the provided evidence. "
            "If the evidence directly supports the claim, return SUPPORT. "
            "If the evidence directly contradicts the claim, return REFUTE. "
            "If the evidence is indirect, advisory, conditional, headline-like, about reported opinions, "
            "or insufficient, return NEUTRAL. "
            "Administrative or payment-status instructions such as deadlines, 'do this', 'check status', "
            "'file a complaint', or 'if you have not received money' are NEUTRAL unless the evidence "
            "explicitly verifies both the condition and the exact claimed consequence. "
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

    def _acquire_global_rate_slot(self):
        window_seconds = 60.0
        min_interval_seconds = window_seconds / float(self.max_requests_per_minute)
        while True:
            self._acquire_lock()
            try:
                now = time.time()
                state = self._load_rate_state()
                timestamps = list(state.get("timestamps", []))
                next_allowed_at = float(state.get("next_allowed_at", 0.0) or 0.0)
                timestamps = [ts for ts in timestamps if (now - ts) < window_seconds]
                next_slot_wait = max(0.0, next_allowed_at - now)
                window_wait = 0.0
                if len(timestamps) >= self.max_requests_per_minute:
                    oldest = min(timestamps)
                    window_wait = max(0.0, (oldest + window_seconds) - now)
                wait_seconds = max(next_slot_wait, window_wait)
                if wait_seconds <= 0.0:
                    timestamps.append(now)
                    state = {
                        "timestamps": timestamps,
                        "next_allowed_at": now + min_interval_seconds,
                    }
                    self._save_rate_state(state)
                    return
            finally:
                self._release_lock()
            time.sleep(max(0.05, wait_seconds + 0.05))

    def _load_rate_state(self):
        try:
            payload = json.loads(self._RATE_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"timestamps": [], "next_allowed_at": 0.0}
        if isinstance(payload, list):
            payload = {"timestamps": payload, "next_allowed_at": 0.0}
        if not isinstance(payload, dict):
            return {"timestamps": [], "next_allowed_at": 0.0}
        cleaned = []
        for item in payload.get("timestamps", []):
            try:
                cleaned.append(float(item))
            except Exception:
                continue
        try:
            next_allowed_at = float(payload.get("next_allowed_at", 0.0) or 0.0)
        except Exception:
            next_allowed_at = 0.0
        return {"timestamps": cleaned, "next_allowed_at": next_allowed_at}

    def _save_rate_state(self, state):
        temp_path = self._RATE_STATE_PATH.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(state, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temp_path, self._RATE_STATE_PATH)

    def _acquire_lock(self):
        while True:
            try:
                os.mkdir(self._RATE_LOCK_DIR)
                return
            except FileExistsError:
                try:
                    age = time.time() - self._RATE_LOCK_DIR.stat().st_mtime
                    if age > self._LOCK_STALE_SECONDS:
                        os.rmdir(self._RATE_LOCK_DIR)
                        continue
                except FileNotFoundError:
                    continue
                except OSError:
                    pass
                time.sleep(0.05)

    def _release_lock(self):
        try:
            os.rmdir(self._RATE_LOCK_DIR)
        except FileNotFoundError:
            return

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
