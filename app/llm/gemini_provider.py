import os

from google import genai
from google.genai import types

from app.core.settings import GEMINI_MODEL
from .base import BaseLLM


class GeminiProvider(BaseLLM):
    def __init__(self, model=None):
        self.model = model or GEMINI_MODEL
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=api_key)

    def chat(self, messages):
        system_instruction = ""
        contents = []
        for message in messages:
            role = message.get("role", "user")
            content = str(message.get("content", ""))
            if role == "system":
                system_instruction += content + "\n"
            elif role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=content)],
                ))
            else:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)],
                ))

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction.strip(),
                max_output_tokens=700,
            ),
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text
