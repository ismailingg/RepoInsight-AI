from openai import OpenAI
from backend.config import OPENROUTER_API_KEY, GEMINI_MODEL

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


def call_llm(prompt: str, temperature: float = 0.1, max_tokens: int = 1024) -> str:
    """
    Send a prompt to the LLM via OpenRouter.
    max_tokens=1024 is enough for all our use cases:
      - Intent detection: 1 word
      - Re-ranking: ~10 lines of scores
      - Query expansion: 3 lines
      - Answer generation: a few paragraphs
    """
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()