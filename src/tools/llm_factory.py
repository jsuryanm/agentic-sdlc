from langchain_openai import ChatOpenAI
from src.core.config import settings
from src.exceptions.custom_exceptions import LLMToolException
from src.logger.custom_logger import logger

class LLMFactory:
    _cache = {}

    @classmethod
    def get(cls, model: str | None = None, temperature: float | None = None):
        model = model or settings.LLM_MODEL
        temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
        key = (model, temperature)

        if key in cls._cache:
            return cls._cache[key]
        
        if not settings.OPENAI_API_KEY:
            raise LLMToolException('OPENAI_API_KEY is missing')
        
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=settings.LLM_MAX_TOKENS,
                api_key=settings.OPENAI_API_KEY
            )
        except Exception as e:
            raise LLMToolException(f"Failed to init LLM '{model}': {e}") from e
        
        cls._cache[key] = llm
        logger.bind(agent='system').info(f'LLM ready: {model} (temp={temperature})')
        return llm