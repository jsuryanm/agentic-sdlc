import asyncio 
from typing import List

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