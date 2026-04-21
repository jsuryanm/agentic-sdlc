import asyncio
import hashlib
from typing import Dict, List

from src.knowledge.ingest import ingest_topic
from src.knowledge.store import KnowledgeStore
from src.logger.custom_logger import logger

_INGESTED_KEYS: set[str] = set()

def _cache_key(topic: str, query: str) -> str:
    h = hashlib.md5(f'{topic}::{query}'.encode()).hexdigest()[:10]
    return f'{topic}:{h}'

def get_docs(stack: List[str], query: str, k: int = 4) -> List[Dict]:
    log = logger.bind(agent='retriever')
    out: List[Dict] = []

    for topic in stack:
        topic_norm = topic.lower().strip()
        key = _cache_key(topic_norm, query)
        store = KnowledgeStore(topic_norm)

        if store.count() == 0 or key not in _INGESTED_KEYS:
            ingest_query = f'{topic_norm} {query} documentation'
            try:
                asyncio.run(ingest_topic(topic_norm, ingest_query, max_results=4))
                _INGESTED_KEYS.add(key)
            except Exception as e:
                log.warning(f'Ingest failed for {topic_norm} (continuing): {e}')
        
        results = store.search(query, k=k)
        for doc in results:
            out.append({
                'topic': topic_norm,
                'source': doc.metadata.get('source',''),
                'content': doc.page_content
            })

    log.info(f'Retrieved {len(out)} chunks across {len(stack)} topics')
    return out

def format_for_prompt(snippets: List[Dict]) -> str:
    if not snippets:
        return 'none'
    lines = []
    for i, s in enumerate(snippets, 1):
        lines.append(f'[{i}] ({s['topic']}) {s['source']}\n{s['content']}')
    return '\n\n'.join(lines)