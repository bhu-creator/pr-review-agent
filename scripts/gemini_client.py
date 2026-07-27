"""
gemini_client.py — All Gemini AI interactions in one place.
To switch to a different LLM (OpenAI, Claude, etc.), only this file changes.
"""

import google.generativeai as genai

from review_prompt import DOTNET_REVIEW_PROMPT


class GeminiReviewer:
    """Sends code to Gemini and returns a .NET-focused review."""

    MODEL_NAME = "gemini-1.5-flash"   # Free tier

    def __init__(self, api_key: str, max_file_chars: int = 28_000) -> None:
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        genai.configure(api_key=api_key)
        self._model          = genai.GenerativeModel(self.MODEL_NAME)
        self._max_file_chars = max_file_chars

    def review_file(self, file_path: str, file_content: str) -> str:
        """Review a single file and return a markdown-formatted review."""
        content = self._truncate_if_needed(file_content)
        prompt  = DOTNET_REVIEW_PROMPT.format(
            file_path=file_path,
            file_content=content,
        )
        try:
            response = self._model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            return f"## ⚠️ Review failed for `{file_path}`\nError: {exc}"

    # ── Private ───────────────────────────────────────────────────────────────

    def _truncate_if_needed(self, content: str) -> str:
        if len(content) > self._max_file_chars:
            return content[:self._max_file_chars] + "\n\n... [truncated — file too large]"
        return content
