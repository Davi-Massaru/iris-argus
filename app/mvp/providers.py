"""Provider boundary: runtime depends on a LangChain chat model only."""
import os


def chat_model(provider, model):
    if provider == 'ollama':
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, base_url=os.environ.get('AGENTIC_OLLAMA_URL', 'http://ollama:11434'),
                          temperature=0, num_predict=1000, num_ctx=8192, reasoning=False,
                          client_kwargs={'timeout': 90.0})
    raise ValueError('PROVIDER_NOT_INSTALLED')
