import asyncio
from typing import Any, Dict, List, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config import settings
from src.exceptions.custom_exceptions import KnowledgeException
from src.logger.custom_logger import logger

class TavilyClient:
    def __init__(self) -> None:
        self.log = logger.bind(agent='tavily')
        self.tools: Optional[Dict[str, Any]] = None

    async def _load(self) -> Dict[str, Any]:
        if self._tools is not None:
            return self._tools
        if not settings.TAVILY_API_KEY:
            raise KnowledgeException(
                'TAVILY_API_KEY not set - configure it in .env or diable RAG'
            )
        
        client = MultiServerMCPClient({
            'tavily': {
                'transport': 'streamable_http',
                'url': settings.TAVILY_MCP_URL,
                'headers': {'Authorization': f'Bearer {settings.TAVILY_API_KEY}'}
            }
        })
        tools = await client.get_tools()
        self._tools = {t.name: t for t in tools}
        self.log.info(f'TAVILY tools loaded: {list(self._tools.keys())}')
        return self._tools
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        tools = await self.load()

        search_tool = (
            tools.get('tavily-search')
            or tools.get('tavily_search')
            or tools.get('search')
        )

        if not search_tool:
            raise KnowledgeException(
                f'Tavily MCP missing search tool; available: {list(tools.keys())}'
            )
        
        result = await search_tool.ainvoke({
            'query': query,
            'max_results': max_results,
            'search_depth': 'advanced',
            'include_raw_content': True
        })

        if isinstance(result, dict):
            return result.get('results',[])
        return result if isinstance(result, list) else []
    
    def search_sync(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return asyncio.run(self.search(query, max_results))