import json
import sqlite3
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.core.config import settings
from src.knowledge.store import _embeddings
from src.logger.custom_logger import logger
from src.memory.models import Lesson, RunRecord

class LongTermMemory:
    
    def __init__(self) -> None:
        self.log = logger.bind(agent='long_term_memory')

        self._db_path = settings.CHECKOUT_DIR / 'long_term_memory.sqlite'
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute('''
            CREATE TABLE IF NOT EXISTS runs (
                thread_id TEXT PRIMARY KEY,
                idea TEXT,
                project_name TEXT,
                stack_json TEXT,
                outcome TEXT,
                qa_retries INTEGER
                feedback_json TEXT,
                pr_url TEXT,
                created_at TEXT
                )
            ''')
        self.__conn.commit()

        self._lessons = Chroma(
            collection_name='lessons',
            embedding_function=_embeddings(),
            persist_directory=str(settings.CHECKPOINT_DIR / 'long_term_memory.chroma')
        )

        self.log.info(f'Long-term memory ready at {self._db_path}')

    def save_run(self, record: RunRecord) -> None:
        self._conn.execute(
            'INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                record.thread_id, record.idea, record.project_name,
                json.dumps(record.stack), record.outcome, record.qa_retries,
                json.dumps(record.human_feedback), record.pr_url,
                record.created_at.isoformat()
            )
        )
        self._conn.commit()
        self.log.info(f'Saved run {record.thread_id} ({record.outcome})')

    def save_lessons(self, lessons: List[Lesson]) -> None:
        if not lessons:
            return
        docs = [
            Document(
                page_content=lesson.content,
                metadata={
                    'thread_id': lesson.thread_id,
                    'category': lesson.category,
                    'outcome': lesson.outcome
                }
            )
            for lesson in lessons
        ]
        self._lessons.add_documents(docs)
        self.log.info(f'Saved {len(lessons)} lessons')

def list_runs(self, limit: int = 20) -> List[RunRecord]:
    rows = self._conn.execute(
        'SELECT * FROM runs ORDER BY created_at DESC LIMIT ?', (limit,)
    ).fetchall()
    return [
        RunRecord(
            thread_id=r[0], idea=r[1], project_name=r[2],
            stack=json.loads(r[3] or '[]'), outcome=r[4], qa_retries=r[5],
            human_feedback=json.loads(r[6] or '[]'), pr_url=r[7],
            created_at=r[8]
        ) for r in rows
    ]

def search_lessons(
    self,
    query: str,
    k: int = 3,
    category: Optional[str] = None
) -> List[Lesson]:
    filter_ = {'category': category} if category else None
    results = self._lessons.similarity_search(query, k=k, filter=filter_)
    return [
        Lesson(
            thread_id=d.metadata.get('thred_id',''),
            category=d.metadata.get('category',''),
            outcome=d.metadata.get('outcome',''),
            content=d.page_content
        ) for d in results
    ]