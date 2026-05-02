from typing import List

# Default models per provider
DEFAULT_EMBEDDING_MODELS = {
    "google": "models/gemini-embedding-001",
    "openai": "text-embedding-3-small",
}


def embed_text(
    text:     str,
    provider: str,
    api_key:  str,
    model:    str = None
) -> List[float]:
    """
    Embed a single text using the specified provider.

    Args:
        text:     Text to embed
        provider: One of: google, openai
        api_key:  User's decrypted API key
        model:    Model name — defaults to provider default

    Returns:
        List of floats (the embedding vector)
    """
    model = model or DEFAULT_EMBEDDING_MODELS.get(provider)

    # ── Google ───────────────────────────────────────────────────
    if provider == "google":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model     = model,
            content   = text,
            task_type = "retrieval_document"
        )
        return result["embedding"]

    # ── OpenAI ───────────────────────────────────────────────────
    elif provider == "openai":
        from openai import OpenAI
        client   = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model = model,
            input = text
        )
        return response.data[0].embedding

    else:
        raise ValueError(
            f"Unknown embedding provider: '{provider}'. "
            f"Must be one of: google, openai"
        )


def embed_query(
    text:     str,
    provider: str,
    api_key:  str,
    model:    str = None
) -> List[float]:
    """
    Embed a search query (uses retrieval_query task type for Google).
    Same as embed_text but optimized for queries not documents.
    """
    model = model or DEFAULT_EMBEDDING_MODELS.get(provider)

    if provider == "google":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model     = model,
            content   = text,
            task_type = "retrieval_query"   # ← different from document embedding
        )
        return result["embedding"]

    elif provider == "openai":
        # OpenAI uses same endpoint for queries and documents
        return embed_text(text, provider, api_key, model)

    else:
        raise ValueError(f"Unknown embedding provider: '{provider}'")