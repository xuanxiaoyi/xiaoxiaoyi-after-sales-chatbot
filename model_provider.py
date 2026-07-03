import os

import requests
from ollama import Client


CHAT_MODEL_NAME = os.environ.get("OLLAMA_CHAT_MODEL", "qwen3:4b")
DEEPSEEK_MODEL_NAME = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/chat/completions",
)

ollama_client = Client()


def use_deepseek():
    provider = os.environ.get("LLM_PROVIDER", "auto").lower()
    return provider == "deepseek" or (
        provider == "auto" and bool(os.environ.get("DEEPSEEK_API_KEY"))
    )


def chat_completion(messages, temperature=0.2, max_tokens=180):
    if use_deepseek():
        try:
            return deepseek_chat(messages, temperature=temperature, max_tokens=max_tokens)
        except Exception:
            if os.environ.get("LLM_PROVIDER", "auto").lower() == "deepseek_strict":
                raise
            return ollama_chat(messages, temperature=temperature, max_tokens=max_tokens)
    return ollama_chat(messages, temperature=temperature, max_tokens=max_tokens)


def deepseek_chat(messages, temperature=0.2, max_tokens=180):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    response = requests.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def ollama_chat(messages, temperature=0.2, max_tokens=180):
    response = ollama_client.chat(
        model=CHAT_MODEL_NAME,
        messages=messages,
        think=False,
        options={
            "temperature": temperature,
            "num_ctx": 2048,
            "num_predict": max_tokens,
            "top_k": 30,
            "top_p": 0.9,
        },
        keep_alive="30m",
    )
    return response.message.content
