import json

import httpx

SYSTEM_PROMPT = (
    "You are a private personal assistant running locally on the user's PC. "
    "If tool data is provided, answer only from it. Be concise."
)


class AIEngine:

    def __init__(self, model="gemma3:1b", url="http://localhost:11434/api/chat"):
        self.api_url = url
        self.model = model
        self.history = []  # recent conversation turns (without tool data)

    def _post(self, messages, **extra):
        response = httpx.post(
            self.api_url,
            json={"model": self.model, "messages": messages, "stream": False, **extra},
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def route(self, message, tools):
        """Ask the model which tool to run. tools: {name: description}. Returns a name or None."""
        listing = "\n".join(f"- {name}: {desc}" for name, desc in tools.items())
        prompt = (
            "Pick the single best tool for the user's request, or \"none\" for ordinary chat.\n"
            f"Tools:\n{listing}\n"
            f"Request: {message}\n"
            'Reply with JSON only: {"tool": "<name or none>"}'
        )
        try:
            raw = self._post([{"role": "user", "content": prompt}],
                             format="json", options={"temperature": 0})
            name = json.loads(raw).get("tool")
        except (httpx.HTTPError, ValueError, KeyError, AttributeError):
            return None
        if name in tools:
            return name
        return "" if name == "none" else None  # "" = ordinary chat, None = router failed

    def chat(self, message, tool_data=None):
        user_content = message
        if tool_data:
            user_content = f"Tool data:\n{tool_data}\n\nUser question: {message}"
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history[-10:]
        messages.append({"role": "user", "content": user_content})

        try:
            answer = self._post(messages)
        except httpx.ConnectError:
            return "Error: Ollama server is not running."
        except httpx.TimeoutException:
            return "Error: AI response timed out."
        except httpx.HTTPStatusError as error:
            return f"Ollama API error: {error}"
        except Exception as error:
            return f"Unexpected error: {error}"

        self.history += [{"role": "user", "content": message},
                         {"role": "assistant", "content": answer}]
        return answer
