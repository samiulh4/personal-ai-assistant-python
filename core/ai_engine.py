
import httpx


class AIEngine:

    def __init__(self):
        self.api_url = "http://localhost:11434/api/chat"
        self.model = "gemma3:1b"

    def chat(self, message):

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "stream": False
        }

        try:
            response = httpx.post(
                self.api_url,
                json=payload,
                timeout=120.0
            )

            response.raise_for_status()

            result = response.json()

            return result["message"]["content"]

        except httpx.ConnectError:
            return "Error: Ollama server is not running."

        except httpx.TimeoutException:
            return "Error: AI response timed out."

        except httpx.HTTPStatusError as error:
            return f"Ollama API error: {error}"

        except Exception as error:
            return f"Unexpected error: {error}"
