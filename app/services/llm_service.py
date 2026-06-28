import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI # pyright: ignore[reportMissingImports]
from langchain_groq import ChatGroq # pyright: ignore[reportMissingImports]


class MockLLM:
    def with_structured_output(self, model: Any):
        return StructuredMockLLM(model)

    def invoke(self, prompt: str):
        return type("Response", (), {"content": "mock response", "text": "mock response"})()


class StructuredMockLLM:
    def __init__(self, model: Any):
        self.model = model

    def invoke(self, prompt: str):
        return self._build_dummy_output()

    def _build_dummy_output(self):
        try:
            return self.model.model_validate(self._dummy_data_for_model(self.model))
        except Exception:
            return type("Response", (), {"content": "mock structured response"})()

    def _dummy_data_for_model(self, model: Any):
        if not hasattr(model, "model_fields"):
            return {}

        data = {}
        for field_name, field_info in model.model_fields.items():
            annotation = field_info.annotation
            if annotation is str:
                data[field_name] = ""
            elif annotation is int:
                data[field_name] = 0
            elif annotation is float:
                data[field_name] = 0.0
            elif annotation is bool:
                data[field_name] = False
            elif annotation is list:
                data[field_name] = []
            elif hasattr(annotation, "model_fields"):
                data[field_name] = self._dummy_data_for_model(annotation)
            else:
                data[field_name] = None

        return data


def _create_gemini_llm():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            temperature=0,
            api_key=api_key,
        )

    return None


def _create_groq_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=api_key,
        )

    return None


def get_llm():
    llm = _create_gemini_llm()
    if llm is not None:
        return llm
    
    groq_llm = _create_groq_llm()
    if groq_llm is not None:
        return groq_llm

    print("WARNING: No Gemini API key found. Using mock LLM instead.")
    return MockLLM()