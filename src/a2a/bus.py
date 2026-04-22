import json
import sqlite3
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.logger.custom_logger import logger


class A2ABus:
    _instance: Optional['A2ABus'] = None

    def __new__(cls) -> 'A2ABus':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        self.db_path = settings.CHECKPOINT_DIR / 'a2a.sqlite'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT,
                from_agent TEXT,
                to_agent TEXT,
                task TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
        ''')
        self._conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_thread ON messages(thread_id)'
        )
        self.log = logger.bind(agent='a2a_bus')
        self.log.info(f'A2A bus ready at {self.db_path}')

    def publish(self, msg: Dict[str, Any], thread_id: str = '') -> None:
        meta = msg.get('metadata') or {}
        payload = json.dumps(msg, default=str)
        message_id = msg.get('message_id', '')
        self._conn.execute(
            'INSERT OR REPLACE INTO messages '
            '(message_id, thread_id, from_agent, to_agent, task, payload_json) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (message_id, thread_id, meta.get('from_agent', ''),
             meta.get('to_agent', ''), meta.get('task', ''), payload)
        )
        self._conn.commit()
        from_a = meta.get('from_agent')
        to_a = meta.get('to_agent')
        task = meta.get('task')
        parts_count = len(msg.get('parts') or [])
        self.log.info(
            f'[{message_id}] {from_a} -> {to_a} task={task} parts={parts_count}'
        )

    def history(self, thread_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            'SELECT payload_json FROM messages '
            'WHERE thread_id = ? ORDER BY created_at, message_id',
            (thread_id,)
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def latest_for(self, thread_id: str, to_agent: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            'SELECT payload_json FROM messages '
            'WHERE thread_id = ? AND to_agent = ? '
            'ORDER BY created_at DESC LIMIT 1',
            (thread_id, to_agent)
        ).fetchone()
        return json.loads(row[0]) if row else None
