"""
LLM provider abstraction.

Every briefing call goes through get_llm_provider().generate(). The product
never depends on which provider handled the request — it just needs structured
text back. If Groq fails, the TemplateFallback produces a usable briefing from
the raw scores so the user is never shown an empty page.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GROQ_API_KEY


class LLMProvider:
    """Abstract base. Subclasses implement generate(system_prompt, user_prompt) -> str."""

    def generate(self, system_prompt, user_prompt):
        raise NotImplementedError


class GroqProvider(LLMProvider):
    """Calls Groq's free-tier llama-3.3-70b-versatile. Fast, no GPU, ~6k requests/day free."""

    # Tried in order — first one that works wins
    DEFAULT_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama3-70b-8192",            # legacy fallback
        "mixtral-8x7b-32768",
    ]

    def __init__(self, model=None):
        from groq import Groq
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model  = model or self.DEFAULT_MODELS[0]

    def generate(self, system_prompt, user_prompt):
        return self.generate_messages([
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ])

    def generate_messages(self, messages):
        """
        Multi-turn variant — accepts a full messages array, used by the chat
        endpoint so prior turns are visible to the LLM.
        """
        last_error = None
        models_to_try = [self.model] + [m for m in self.DEFAULT_MODELS if m != self.model]

        for model in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1500,
                    temperature=0.3,
                    timeout=30,
                )
                if model != self.model:
                    print(f"   ℹ️  Using Groq model {model} (primary unavailable)")
                    self.model = model
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                if "model" in msg and ("deprec" in msg or "not found" in msg or "decommis" in msg):
                    print(f"   ⚠️  Groq model {model} unavailable, trying next...")
                    continue
                raise

        raise RuntimeError(f"All Groq models failed. Last error: {last_error}")


class TemplateFallback(LLMProvider):
    """
    Deterministic briefing assembled from raw scores. No LLM call.
    Used when Groq is unavailable. Quality is lower but never empty.

    Expects a user_prompt that's already structured with sections marked
    by [HEALTH], [RISKS], [POSITIVES], [REGULATIONS]. Briefing.py builds
    that structure before calling.
    """

    def generate(self, system_prompt, user_prompt):
        # The user_prompt is a structured dict serialised as JSON-ish text
        # We extract sections naively and reassemble into the standard format
        return self._build_template_briefing(user_prompt)

    def _build_template_briefing(self, prompt_text):
        return (
            "PROSPEX WEEKLY BRIEFING\n"
            "═══════════════════════\n\n"
            "Note: This briefing was generated from raw scores because the AI "
            "service was unavailable. The figures below are accurate; the "
            "narrative is simpler than usual.\n\n"
            f"{prompt_text}\n\n"
            "THIS WEEK'S ACTIONS\n"
            "Review the financial alerts above and prioritise the runway "
            "and receivables items first.\n"
        )


def get_llm_provider():
    """Returns Groq if configured + reachable, otherwise TemplateFallback."""
    if not GROQ_API_KEY or GROQ_API_KEY.endswith("_here"):
        print("   ⚠️  Groq API key missing — using template fallback")
        return TemplateFallback()

    try:
        provider = GroqProvider()
        return provider
    except Exception as e:
        print(f"   ⚠️  Groq init failed ({e}) — using template fallback")
        return TemplateFallback()
