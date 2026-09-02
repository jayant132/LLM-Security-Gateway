"""Thin LLM client. Uses OpenAI if OPENAI_API_KEY is set, else a deterministic mock
so the whole project runs free with zero external dependencies/costs."""
import os

def generate(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"[mock-llm response] You said: {prompt[:200]}"
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content
