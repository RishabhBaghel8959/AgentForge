from app.llm.ollama_client import OllamaClient

client = OllamaClient()

response = client.generate("Say Hello in one sentence.")

print(response)