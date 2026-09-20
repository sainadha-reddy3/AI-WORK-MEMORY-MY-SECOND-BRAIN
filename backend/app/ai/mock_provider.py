"""
Mock AI provider.

Deterministic, instant, and requires no model. Used for development
in environments without an LLM, and for tests — the hallucination
rules must be testable without depending on a model's mood.

The rules it implements are simplified but real: uncertainty
detection and refusal-when-no-memory behave exactly as the
production providers must.
"""

import hashlib
import re

from app.ai.base import AIProvider, MemoryAnswer, StructuredMemory

# Phrases that mean the user is unsure. Anything matching these
# keeps the memory marked "uncertain" forever.
UNCERTAINTY_PATTERNS = [
    r"\bi think\b",
    r"\bi believe\b",
    r"\bnot sure\b",
    r"\bnot certain\b",
    r"\bmaybe\b",
    r"\bprobably\b",
    r"\bpossibly\b",
    r"\bmight have\b",
    r"\bcan'?t remember\b",
    r"\bdon'?t remember\b",
    r"\bif i recall\b",
]

# Simple keyword → topic mapping. A real provider infers topics;
# this keeps the mock predictable.
TOPIC_KEYWORDS = {
    "kubernetes": ["kubernetes", "k8s", "pod", "kubectl", "namespace"],
    "k9s": ["k9s"],
    "argocd": ["argocd", "argo cd"],
    "helm": ["helm", "values.yaml", "chart"],
    "terraform": ["terraform", "tfstate", "terragrunt"],
    "gcp": ["gcp", "google cloud", "gke"],
    "iam": ["iam", "service account", "workload identity"],
    "docker": ["docker", "dockerfile", "container"],
    "gitops": ["gitops"],
    "networking": ["load balancer", "ingress", "dns", "networkpolicy"],
}

TYPE_KEYWORDS = {
    "mistake": ["mistake", "wrong", "failed", "didn't work", "did not work"],
    "solution": ["fixed", "solved", "resolved", "corrected", "working now"],
    "incident": ["issue", "error", "crash", "down", "failing", "broken"],
    "learning": ["learned", "understood", "read about", "studied"],
    "meeting": ["meeting", "call", "discussed with", "standup"],
}


class MockProvider(AIProvider):
    name = "mock"

    def is_available(self) -> bool:
        return True

    def structure_memory(self, text: str) -> StructuredMemory:
        lower = text.lower()

        # --- uncertainty detection -------------------------------
        markers = [
            m.group(0)
            for p in UNCERTAINTY_PATTERNS
            if (m := re.search(p, lower))
        ]
        confidence = "uncertain" if markers else "confirmed"

        # --- topics ----------------------------------------------
        topics = [
            topic
            for topic, words in TOPIC_KEYWORDS.items()
            if any(w in lower for w in words)
        ]

        # --- type -------------------------------------------------
        memory_type = "note"
        for mtype, words in TYPE_KEYWORDS.items():
            if any(w in lower for w in words):
                memory_type = mtype
                break

        # --- title ------------------------------------------------
        first_line = text.strip().split("\n")[0]
        title = first_line[:120].rstrip(".") or "Untitled memory"

        return StructuredMemory(
            title=title,
            content=text.strip(),
            memory_type=memory_type,
            confidence=confidence,
            topics=topics,
            language="en",
            uncertainty_markers=markers,
        )

    def answer_from_memories(
        self, question: str, memories: list[dict]
    ) -> MemoryAnswer:
        """
        The core anti-hallucination rule, in its simplest form:
        no memories means no claim about the user's history.
        """
        if not memories:
            return MemoryAnswer(
                answer=(
                    "I don't have a recorded memory of this, so I don't "
                    "want to guess."
                ),
                used_memory_ids=[],
                has_recorded_memory=False,
            )

        lines = []
        for m in memories:
            prefix = (
                "You recorded (unconfirmed): "
                if m.get("confidence") == "uncertain"
                else "You recorded: "
            )
            lines.append(f"{m.get('occurred_on')} — {prefix}{m.get('title')}")

        return MemoryAnswer(
            answer="\n".join(lines),
            used_memory_ids=[str(m["id"]) for m in memories],
            has_recorded_memory=True,
        )

    def embed(self, text: str) -> list[float]:
        """
        Deterministic pseudo-embedding derived from a hash.

        Not semantically meaningful — it exists so Phase 5 plumbing
        can be built and tested without a model. Real semantic search
        requires a real embedding model.
        """
        digest = hashlib.sha256(text.encode()).digest()
        return [(b - 128) / 128.0 for b in digest[:32]]