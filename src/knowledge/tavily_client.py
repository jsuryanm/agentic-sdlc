import asyncio
from typing import Any, Dict, List

from tavily import AsyncTavilyClient as _AsyncTavilyClient

from src.core.config import settings
from src.exceptions.custom_exceptions import KnowledgeException
from src.logger.custom_logger import logger


class TavilyClient:
    def __init__(self) -> None:
        self.log = logger.bind(agent='tavily')
        self._client: _AsyncTavilyClient | None = None

    def _get_client(self) -> _AsyncTavilyClient:
        if self._client is not None:
            return self._client
        if not settings.TAVILY_API_KEY:
            raise KnowledgeException(
                'TAVILY_API_KEY not set - configure it in .env or disable RAG'
            )
        self._client = _AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
        return self._client

    async def search(
        self, query: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        result = await client.search(
            query=query,
            max_results=max_results,
            search_depth='advanced',
            include_raw_content=True,
        )
        if isinstance(result, dict):
            return result.get('results', [])
        return result if isinstance(result, list) else []

    def search_sync(
        self, query: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        return asyncio.run(self.search(query, max_results))
