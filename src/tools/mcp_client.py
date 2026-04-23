import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config import settings
from src.logger.custom_logger import logger
from src.exceptions.custom_exceptions import MCPToolException

class GitHubMCPClient:
    def __init__(self):
        if not settings.GITHUB_PERSONAL_ACCESS_TOKEN:
            raise MCPToolException("GITHUB_PERSONAL_ACCESS_TOKEN not found")
        
        self._connections = {
            "github":{
                "transport":"streamable_http",
                "url":settings.GITHUB_MCP_URL,
                "headers": {
                    "Authorization": f"Bearer {settings.GITHUB_PERSONAL_ACCESS_TOKEN}"
                },
            }
        }
    
    async def _load_tools(self) -> List:
        try:
            client = MultiServerMCPClient(self._connections)
            tools = await client.get_tools()
            logger.bind(agent="mcp").info(f"Loaded {len(tools)} GitHub MCP tools:"
                                          f"{[t.name for t in tools]}")
            
            return tools 
    
        except Exception as e:
            raise MCPToolException(f"Failed to load GitHub MCP tools :{e}") from e 
    
    def load_tools_sync(self) -> List:
        return asyncio.run(self._load_tools())

    async def get_tools(self) -> List:
        return await self._load_tools()

# if __name__ == "__main__":
#     client = GitHubMCPClient()
#     mcp_tools = client.load_tools_sync()
#     logger.info(f"mcp_tools:{mcp_tools}")


# ---------------------------------------------------------------------------
# Context7 MCP client
# ---------------------------------------------------------------------------
# Exposes Context7's canonical-documentation tools to the developer and
# code-review agents. The developer invokes these tools directly through a
# tool-calling agent; the reviewer pulls a pre-fetched doc digest via
# ``fetch_docs_for_stack_sync``. All errors are swallowed and logged so the
# pipeline keeps running when Context7 is unreachable.

_ctx7_log = logger.bind(agent='context7')

_ctx7_client: Optional[MultiServerMCPClient] = None
_ctx7_tools_cache: Optional[List[BaseTool]] = None
_ctx7_doc_cache: Dict[tuple, str] = {}


def _build_context7_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
        'transport': 'stdio',
        'command': settings.CONTEXT7_MCP_COMMAND,
        'args': list(settings.CONTEXT7_MCP_ARGS),
    }
    if settings.CONTEXT7_API_KEY:
        cfg['env'] = {'CONTEXT7_API_KEY': settings.CONTEXT7_API_KEY}
    return cfg


def _get_context7_client() -> MultiServerMCPClient:
    global _ctx7_client
    if _ctx7_client is None:
        _ctx7_client = MultiServerMCPClient(
            {'context7': _build_context7_config()}
        )
    return _ctx7_client


async def get_context7_tools() -> List[BaseTool]:
    """Return cached Context7 tools; empty list if the MCP server is unreachable."""
    global _ctx7_tools_cache
    if _ctx7_tools_cache is not None:
        return _ctx7_tools_cache
    if not settings.USE_CONTEXT7:
        _ctx7_tools_cache = []
        return _ctx7_tools_cache
    try:
        client = _get_context7_client()
        tools = await client.get_tools()
        _ctx7_tools_cache = list(tools or [])
        _ctx7_log.info(
            f'Loaded {len(_ctx7_tools_cache)} Context7 tools: '
            f'{[t.name for t in _ctx7_tools_cache]}'
        )
    except Exception as e:
        _ctx7_log.warning(f'Context7 get_tools failed (continuing without it): {e}')
        _ctx7_tools_cache = []
    return _ctx7_tools_cache


def _find_tool(tools: List[BaseTool], *needles: str) -> Optional[BaseTool]:
    """Find a tool whose lowercased name contains every ``needle`` substring."""
    for t in tools:
        name = (t.name or '').lower()
        if all(n in name for n in needles):
            return t
    return None


async def _ainvoke_tool(tool: BaseTool, payload: Dict[str, Any]) -> str:
    try:
        result = await tool.ainvoke(payload)
    except Exception as e:
        _ctx7_log.warning(f'Tool {tool.name} failed: {e}')
        return ''
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts = []
        for item in result:
            if isinstance(item, dict) and 'text' in item:
                parts.append(item['text'])
            else:
                parts.append(str(item))
        return '\n'.join(parts)
    return str(result)


async def _fetch_one_library(
    tools: List[BaseTool], library: str, topic: str
) -> str:
    resolver = _find_tool(tools, 'resolve')
    docs_tool = _find_tool(tools, 'docs')
    if resolver is None or docs_tool is None:
        _ctx7_log.warning('Context7 resolver or docs tool not present')
        return ''

    resolved = await _ainvoke_tool(
        resolver,
        {'libraryName': library, 'query': topic or f'{library} current API usage'},
    )
    if not resolved:
        return ''

    lib_id = ''
    for token in resolved.replace(',', ' ').split():
        token = token.strip('`",\'')
        if token.startswith('/') and token.count('/') >= 2:
            lib_id = token
            break
    if not lib_id:
        _ctx7_log.warning(f"No library ID parsed for '{library}'")
        return ''

    return await _ainvoke_tool(
        docs_tool,
        {
            'libraryId': lib_id,
            'query': topic or f'{library} getting started and core APIs',
        },
    )


async def fetch_docs_for_stack(
    stack: List[str], topic: Optional[str] = None
) -> str:
    """Fetch authoritative docs for each library in the stack.

    Returns a single markdown string with one ``## {library}`` section per
    entry, or ``''`` if Context7 is disabled / unreachable.
    """
    if not stack or not settings.USE_CONTEXT7:
        return ''

    tools = await get_context7_tools()
    if not tools:
        return ''

    sections: List[str] = []
    for lib in stack:
        key = (lib.lower().strip(), topic or '')
        if key in _ctx7_doc_cache:
            cached = _ctx7_doc_cache[key]
            if cached:
                sections.append(f'## {lib}\n{cached}')
            continue
        doc = await _fetch_one_library(tools, lib, topic or '')
        _ctx7_doc_cache[key] = doc
        if doc:
            sections.append(f'## {lib}\n{doc}')

    return '\n\n'.join(sections)


def fetch_docs_for_stack_sync(
    stack: List[str], topic: Optional[str] = None
) -> str:
    try:
        return asyncio.run(fetch_docs_for_stack(stack, topic))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(fetch_docs_for_stack(stack, topic))
        finally:
            loop.close()
    except Exception as e:
        _ctx7_log.warning(f'fetch_docs_for_stack_sync failed: {e}')
        return ''


def reset_context7_cache() -> None:
    """Test helper: clear all module-level Context7 state."""
    global _ctx7_client, _ctx7_tools_cache
    _ctx7_client = None
    _ctx7_tools_cache = None
    _ctx7_doc_cache.clear()