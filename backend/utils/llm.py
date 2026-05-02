from openai import OpenAI
from typing import Optional

# Provider base URLs — all use OpenAI-compatible API
PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "openai":     "https://api.openai.com/v1",
}

# Free model defaults per provider
DEFAULT_MODELS = {
    "openrouter": "google/gemini-2.0-flash-exp:free",
    "groq":       "llama-3.3-70b-versatile",
    "openai":     "gpt-4o-mini",
    "anthropic":  "claude-haiku-4-5",
}


def call_llm(
    prompt:      str,
    provider:    str,
    api_key:     str,
    model:       Optional[str] = None,
    temperature: float = 0.1,
    max_tokens:  int   = 1024
) -> str:
    """
    Send a prompt to any supported LLM provider.

    Args:
        prompt:      The prompt to send
        provider:    One of: openrouter, groq, openai, anthropic
        api_key:     The user's decrypted API key for this provider
        model:       Model name — defaults to free model for provider
        temperature: Randomness (0.0-1.0) — low = consistent
        max_tokens:  Max response length

    Returns:
        Response text as string
    """
    model = model or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["openrouter"])

    # ── Anthropic (separate SDK) ─────────────────────────────────
    if provider == "anthropic":
        import anthropic
        client   = anthropic.Anthropic(api_key=api_key)
        message  = client.messages.create(
            model      = model,
            max_tokens = max_tokens,
            messages   = [{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()

    # ── OpenAI-compatible providers ──────────────────────────────
    base_url = PROVIDER_URLS.get(provider)
    if not base_url:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            f"Must be one of: {list(PROVIDER_URLS.keys()) + ['anthropic']}"
        )

    client   = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model       = model,
        messages    = [{"role": "user", "content": prompt}],
        temperature = temperature,
        max_tokens  = max_tokens,
    )
    return response.choices[0].message.content.strip()