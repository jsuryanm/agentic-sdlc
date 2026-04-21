from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.core.config import settings
from src.logger.custom_logger import logger

_EMBEDDINGS: Optional[HuggingFaceEmbeddings] = None

def _embeddings() -> HuggingFaceEmbeddings:
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = HuggingFaceEmbeddings(
            model_name='sentence-transformers/all-MiniLM-L6-v2',
            encode_kwargs={'normalize_embeddings': True}
        )
    return _EMBEDDINGS

class KnowledgeStore:
    def __init__(self, collection: str) -> None:
        self.collection = collection
        self.persist_dir = settings.CHECKPOINT_DIR / 'knowledge.chroma'
        self.persit_dir.mkdir(parents=True, exist_ok=True)
        self.log = logger.bind(agent='knowledge')
        self._db = Chroma(
            collection_name=f'docs_{collection}',
            embedding_function=_embeddings(),
            persist_directory=str(self.persist_dir)
        )

    def add(self, docs: List[Document]) -> None:
        if not docs:
            return 
        self._db.add_documents(docs)
        self.log.info(f'[{self.collection}] added {len(docs)} chunks')

    def search(self, query: str, k: int = 4) -> List[Document]:
        return self._db.similarity_search(query, k=k)
    
    def count(self) -> int:
        try:
            return self._db._collection.count()
        except Exception: 
            return 0