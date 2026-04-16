"""LLM client with caching for cost efficiency."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

# Load .env file if present
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Cache directory for LLM responses
CACHE_DIR = Path(__file__).parent.parent.parent / ".llm_cache"


class LLMClient:
    """
    LLM client wrapper with response caching.

    Caches responses by input hash to avoid repeated API calls.
    Uses Claude Haiku for cost efficiency (~$0.25/1M input, $1.25/1M output).
    """

    def __init__(
        self,
        model: str = "claude-3-haiku-20240307",
        cache_enabled: bool = True,
    ):
        self.model = model
        self.cache_enabled = cache_enabled
        self._client = None

        # Ensure cache directory exists
        if cache_enabled:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable not set. "
                    "Set it with: export ANTHROPIC_API_KEY=your_key"
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _cache_key(self, prompt: str, system: str = "") -> str:
        """Generate cache key from prompt hash."""
        content = f"{self.model}:{system}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a given key."""
        return CACHE_DIR / f"{cache_key}.json"

    def _load_from_cache(self, cache_key: str) -> str | None:
        """Load cached response if available."""
        if not self.cache_enabled:
            return None

        cache_path = self._cache_path(cache_key)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                return data.get("response")
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    def _save_to_cache(self, cache_key: str, response: str, prompt: str) -> None:
        """Save response to cache."""
        if not self.cache_enabled:
            return

        cache_path = self._cache_path(cache_key)
        data = {
            "response": response,
            "model": self.model,
            "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt,
        }
        cache_path.write_text(json.dumps(data, indent=2))

    def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """
        Get completion from LLM with caching.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            max_tokens: Maximum tokens in response

        Returns:
            The LLM response text
        """
        # Check cache first
        cache_key = self._cache_key(prompt, system)
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached

        # Make API call
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        result = response.content[0].text

        # Cache the response
        self._save_to_cache(cache_key, result, prompt)

        return result

    def complete_json(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
    ) -> dict[str, Any] | None:
        """
        Get JSON completion from LLM.

        Instructs the model to respond with valid JSON and parses the result.
        Returns None if parsing fails.
        """
        json_system = (system + "\n\n" if system else "") + (
            "Respond with valid JSON only. No markdown, no explanation, just the JSON object."
        )

        response = self.complete(prompt, system=json_system, max_tokens=max_tokens)

        # Try to parse JSON from response
        try:
            # Handle potential markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                # Extract content between code blocks
                lines = text.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_block = not in_block
                        continue
                    if in_block:
                        json_lines.append(line)
                text = "\n".join(json_lines)

            return json.loads(text)
        except json.JSONDecodeError:
            return None


# Global client instance (lazy initialized)
_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Get the global LLM client instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def is_llm_available() -> bool:
    """Check if LLM is available (API key set and package installed)."""
    if not ANTHROPIC_AVAILABLE:
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
