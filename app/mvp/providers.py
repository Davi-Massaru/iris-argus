"""Provider boundary: runtime depends on a LangChain chat model only."""

import os


SUPPORTED_PROVIDERS = {"ollama", "openai"}


def configured_provider():
    provider = os.environ.get("AGENTIC_PROVIDER", "ollama").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError("AGENTIC_PROVIDER must be ollama or openai.")
    return provider


def default_model(provider=None):
    provider = provider or configured_provider()
    default = "qwen2.5:3b" if provider == "ollama" else "gpt-4o-mini"
    return os.environ.get("AGENTIC_MODEL", default)


def chat_model(provider, model):
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            base_url=os.environ.get("AGENTIC_OLLAMA_URL", "http://ollama:11434"),
            temperature=0,
            num_predict=1000,
            num_ctx=8192,
            reasoning=False,
            client_kwargs={"timeout": 90.0},
        )
    if provider == "openai":
        api_key = os.environ.get("AGENTIC_OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("AGENTIC_OPENAI_API_KEY is required when AGENTIC_PROVIDER=openai.")
        from langchain_openai import ChatOpenAI

        options = {"model": model, "api_key": api_key, "temperature": 0, "max_tokens": 1000}
        base_url = os.environ.get("AGENTIC_OPENAI_BASE_URL", "").strip()
        if base_url:
            options["base_url"] = base_url
        return ChatOpenAI(**options)
    raise ValueError("PROVIDER_NOT_INSTALLED")
