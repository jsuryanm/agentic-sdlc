import time
from abc import ABC, abstractmethod

from src.logger.custom_logger import logger
from src.pipelines.state import SDLCState

class BaseAgent(ABC):
    name: str = 'base_agent'

    def __init__(self):
        self.logger = logger.bind(agent=self.name)

    def run(self, state: SDLCState) -> dict:
        self.logger.info(f'▶ {self.name} starting')
        start = time.time()
        try:
            updates = self._process(state)
            elapsed = round(time.time() - start, 2)
            self.logger.info(f'{self.name} done in {elapsed}s')
            return updates
        except Exception as e:
            elapsed = round(time.time() - start, 2)
            msg = f'{self.name} failed after {elapsed}s: {e}'
            self.logger.exception(msg)
            return {'errors': [msg], 'status': f'{self.name}_failed'}
        
    @abstractmethod
    def _process(self, state: SDLCState) -> dict: ...