"""
Real OpenAI API Client
=======================
Replaces the mock server with actual OpenAI GPT calls.
Set your API key in .env file:
    OPENAI_API_KEY=sk-xxxxxxxxxxxx
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

class OpenAIChatClient:
    
    BASE_URL = "https://api.openai.com/v1/chat/completions"
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }
    
    def chat(self, message: str, system_prompt: str = "You are a helpful assistant.") -> dict:
        """Send a message to GPT and return structured response."""
        start = time.time()
        
        payload = {
            "model": "gpt-3.5-turbo",   # cheap for testing
            "messages": [
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": message},
            ],
            "max_tokens": 200,
            "temperature": 0.7,
        }
        
        response = requests.post(self.BASE_URL, json=payload, headers=self.headers)
        latency_ms = round((time.time() - start) * 1000, 2)
        
        response.raise_for_status()
        data = response.json()
        
        return {
            "response":        data["choices"][0]["message"]["content"],
            "latency_ms":      latency_ms,
            "tokens_used":     data["usage"]["total_tokens"],
            "model":           data["model"],
            "finish_reason":   data["choices"][0]["finish_reason"],
        }


# ── Tests against real OpenAI ─────────────────────────────────

if __name__ == "__main__":
    client = OpenAIChatClient()
    
    test_messages = [
        "What is the capital of France?",
        "Explain machine learning in one sentence.",
        "Say hello in Spanish.",
    ]
    
    for msg in test_messages:
        result = client.chat(msg)
        print(f"\nQ: {msg}")
        print(f"A: {result['response']}")
        print(f"Latency: {result['latency_ms']}ms | Tokens: {result['tokens_used']}")