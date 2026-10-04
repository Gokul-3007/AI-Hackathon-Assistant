import json
import os

import requests


class GroqClient:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    def chat(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1500, json_mode=False):
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing. Add it to your .env file or environment.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful hackathon mentor."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
        except requests.exceptions.Timeout as exc:
            raise RuntimeError("Groq is taking too long to respond. Try again later.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError("Cannot connect to Groq right now. Check your internet connection and try again.") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError("The Groq request could not be completed. Try again later.") from exc

        if response.status_code != 200:
            try:
                error_message = response.json().get("error", {}).get("message", "")
            except (ValueError, AttributeError):
                error_message = ""

            if response.status_code in {401, 403}:
                detail = "Check that GROQ_API_KEY is valid and has access to this model."
            elif response.status_code == 429:
                if any(term in error_message.casefold() for term in ("quota", "billing", "spend limit")):
                    detail = "Groq account quota is exhausted. Check billing or usage limits in the Groq console."
                else:
                    detail = "Groq rate limit reached. Wait briefly before retrying."
            elif response.status_code == 404:
                detail = f"The configured model '{self.model}' is unavailable. Set GROQ_MODEL to an active model."
            else:
                detail = error_message or f"Groq returned HTTP {response.status_code}."
            raise RuntimeError(detail)

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise RuntimeError("Groq returned an empty response.")
            return content
        except (KeyError, IndexError, TypeError):
            return json.dumps(data)
