"""
Ollama provider — talks to a locally running Ollama instance.

Design note: small models (3B) follow instructions imperfectly. This
provider is deliberately defensive — strict prompts, tolerant
parsing, and a fall back to deterministic rules when the model
returns something unusable.

That fallback is a safety property, not a convenience. A model that
fails must never produce a confident wrong answer about the user's
history.
"""

import json
import re

import httpx

from app.ai.base import AIProvider, MemoryAnswer, StructuredMemory
from app.ai.mock_provider import MockProvider
from app.core.config import settings

STRUCTURE_PROMPT = """You extract structured data from a person's \
description of their work.

Return ONLY a JSON object. No markdown, no explanation, no preamble.

Fields:
- "title": short summary, under 100 characters
- "memory_type": exactly one of: note, learning, mistake, solution, \
incident, code, meeting
- "confidence": "uncertain" if the person expressed doubt (I think, \
maybe, not sure, can't remember, might have). Otherwise "confirmed".
- "topics": lowercase technology/topic tags, e.g. ["argocd", "helm"]
- "language": "en", "te", "hi", or "mixed"

CRITICAL RULE: Do not add information the person did not state. Do \
not guess. Only describe what is written.

Example input:
I think I fixed the pod issue by changing the service account, but \
I'm not certain.

Example output:
{"title": "Possibly fixed pod issue via service account change", \
"memory_type": "solution", "confidence": "uncertain", \
"topics": ["kubernetes"], "language": "en"}

Now process this text:
"""

ANSWER_PROMPT = """You answer questions about a person's recorded \
work history.

ABSOLUTE RULES:
1. Use ONLY the memories provided below. Never add facts from your \
own knowledge.
2. If the memories do not answer the question, say: "I don't have a \
recorded memory of this."
3. If a memory is marked uncertain, say so — e.g. "you recalled that \
you may have...". Never state it as fact.
4. Reference dates when you use a memory.

RECORDED MEMORIES:
{memories}

QUESTION: {question}

Answer using only the memories above."""


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.url = settings.ollama_url.rstrip("/")
        self.model = settings.ollama_model
        self.embed_model = settings.ollama_embed_model
        # Used when the model is unreachable or returns unusable output.
        self._fallback = MockProvider()

    # ---------- availability -------------------------------------

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.url}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    # ---------- internal helpers ---------------------------------

    def _generate(self, prompt: str, *, json_mode: bool = False) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Low temperature: we want consistent extraction, not
            # creative variation.
            "options": {"temperature": 0.1},
        }
        if json_mode:
            # Constrains decoding to valid JSON — far more reliable
            # than asking the model nicely.
            payload["format"] = "json"

        r = httpx.post(f"{self.url}/api/generate", json=payload, timeout=120.0)
        r.raise_for_status()
        return r.json().get("response", "")

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """
        Parse JSON from a model response, tolerating the usual mess:
        markdown fences, preambles, trailing text.
        """
        text = text.strip()

        # Strip ```json fences if present.
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Last resort: find the first {...} block.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    # ---------- interface ----------------------------------------

    def structure_memory(self, text: str) -> StructuredMemory:
        if not self.is_available():
            return self._fallback.structure_memory(text)

        try:
            raw = self._generate(STRUCTURE_PROMPT + text, json_mode=True)
            data = self._extract_json(raw)
        except Exception:
            data = None

        if not data:
            # Model unusable — deterministic rules are safer than
            # trusting malformed output.
            return self._fallback.structure_memory(text)

        # Validate every field. The model's output is untrusted input.
        valid_types = {
            "note", "learning", "mistake", "solution",
            "incident", "code", "meeting",
        }
        memory_type = str(data.get("memory_type", "note")).lower()
        if memory_type not in valid_types:
            memory_type = "note"

        confidence = str(data.get("confidence", "confirmed")).lower()
        if confidence not in {"confirmed", "uncertain"}:
            confidence = "confirmed"

        # Safety net: if our own rules detect hedging but the model
        # said "confirmed", trust the rules. Preserving uncertainty
        # matters more than trusting the model.
        rule_based = self._fallback.structure_memory(text)
        if rule_based.confidence == "uncertain":
            confidence = "uncertain"

        topics = data.get("topics", [])
        if not isinstance(topics, list):
            topics = []
        topics = [str(t).strip().lower() for t in topics if str(t).strip()][:10]

        language = str(data.get("language", "en")).lower()
        if language not in {"en", "te", "hi", "mixed"}:
            language = "en"

        title = str(data.get("title") or "").strip()[:200]
        if not title:
            title = rule_based.title

        return StructuredMemory(
            title=title,
            # Always the user's own words, never the model's rewrite.
            content=text.strip(),
            memory_type=memory_type,
            confidence=confidence,
            topics=topics,
            language=language,
            uncertainty_markers=rule_based.uncertainty_markers,
        )

    def answer_from_memories(
        self, question: str, memories: list[dict]
    ) -> MemoryAnswer:
        # The no-memory case never reaches the model. There is
        # nothing for it to summarise, and asking would invite
        # invention.
        if not memories:
            return MemoryAnswer(
                answer=(
                    "I don't have a recorded memory of this, so I don't "
                    "want to guess."
                ),
                used_memory_ids=[],
                has_recorded_memory=False,
            )

        if not self.is_available():
            return self._fallback.answer_from_memories(question, memories)

        blocks = []
        for m in memories:
            flag = " (UNCERTAIN — the user was not sure)" if m.get(
                "confidence"
            ) == "uncertain" else ""
            blocks.append(
                f"[{m.get('occurred_on')}]{flag}\n"
                f"Title: {m.get('title')}\n"
                f"Details: {m.get('content')}"
            )

        prompt = ANSWER_PROMPT.format(
            memories="\n\n".join(blocks), question=question
        )

        try:
            answer = self._generate(prompt).strip()
        except Exception:
            return self._fallback.answer_from_memories(question, memories)

        if not answer:
            return self._fallback.answer_from_memories(question, memories)

        return MemoryAnswer(
            answer=answer,
            used_memory_ids=[str(m["id"]) for m in memories],
            has_recorded_memory=True,
        )

    def embed(self, text: str) -> list[float]:
        r = httpx.post(
            f"{self.url}/api/embeddings",
            json={"model": self.embed_model, "prompt": text},
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()["embedding"]