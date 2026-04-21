from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.knowledge.store import KnowledgeStore
from src.knowledge.tavily_client import TavilyClient
from src.logger.custom_logger import logger

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120,
    separators=['\n\n', '\n', '.', ' ', '']
)

async def ingest_topic(topic: str, query: str, max_results: int = 5) -> int:
    log = logger.bind(agent='ingest')
    store = KnowledgeStore(topic)
    client = TavilyClient()

    try:
        results = await client.search(query, max_results=max_results)
    except Exception as e:
        log.warning(f'[{topic}] Tavily search failed: {e}')
        return 0
    
    if not results:
        log.warning(f"[{topic}] Tavily returned nothing for '{query}'")
        return 0
    
    docs: List[Document] = []
    for r in results:
        content = r.get('raw_content') or r.get('content') or ''
        if not content.strip():
            continue
        for chunk in _SPLITTER.split_text(content):
            docs.append(Document(
                page_content=chunk,
                metadata={
                    'source': r.get('url', ''),
                    'title': r.get('title', ''),
                    'topic': topic
                }
            ))

    store.add(docs)
    log.info(f'[{topic}] ingested {len(docs)} chunks from {len(results)} pages')
    return len(docs)