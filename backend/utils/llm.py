from openai import OpenAI
from backend.config import OPENROUTER_API_KEY, GEMINI_MODEL

# OpenRouter client — drop-in replacement for Gemini
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


def call_llm(prompt: str, temperature: float = 0.1) -> str:
    """
    Send a prompt to the LLM via OpenRouter.
    Returns the response text.
    temperature=0.1 keeps responses consistent (low randomness)
    """
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()