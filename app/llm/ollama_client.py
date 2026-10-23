import requests

from app.models.workflow import GenerationResult


class OllamaClient:
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str) -> str:
        return self.generate_with_metadata(prompt).text

    def generate_with_metadata(self, prompt: str) -> GenerationResult:

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=(5, 120)
        )

        response.raise_for_status()

        body = response.json()
        text = body.get("response")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Ollama returned an empty response")
        return GenerationResult(
            text=text.strip(),
            model=body.get("model", self.model),
            prompt_tokens=body.get("prompt_eval_count"),
            completion_tokens=body.get("eval_count"),
        )
