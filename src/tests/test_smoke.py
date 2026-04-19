import sys, uuid
from langgraph.types import Command

from src.logger.custom_logger import logger
from src.pipelines.graph import build_graph, make_checkpointer
from src.pipelines.state import initial_state

def main():
    idea = sys.argv[1] if len(sys.argv) > 1 else \
        'A FastAPI TODO API with CRUD and in-memory storage'
    thread_id = str(uuid.uuid4())[:8]

    with make_checkpointer() as cp:
        graph = build_graph(cp)
        cfg = {'configurable': {'thread_id': thread_id}}
        result = graph.invoke(initial_state(idea, thread_id), config=cfg)

        while '__interrupt__' in result:
            phase = result['__interrupt__'][0].value.get('phase')
            logger.bind(agent='cli').info(f'[auto-approve] {phase}')
            result = graph.invoke(
                Command(resume={'verdict': 'approve', 'comment': ''})
                config=cfg
            )

        logger.bind(agent='cli').info(f'FINAL STATUS: {result.get('status')}')
        if result.get('deployment', {}).get('pr_url'):
            print(f'PR: {result['deployment']['pr_url']}')

if __name__ == '__main__':
    main()