"""Holds the singleton compiled graph and its checkpointer context.

The SqliteSaver returned by ``make_checkpointer`` is a context manager, so we
enter it once at startup and close it at shutdown.
"""
from typing import Optional

from src.logger.custom_logger import logger
from src.pipelines.graph import build_graph, make_checkpointer

_CP_CTX = None
_CHECKPOINTER = None
_GRAPH = None


def startup() -> None:
    global _CP_CTX, _CHECKPOINTER, _GRAPH
    if _GRAPH is not None:
        return
    _CP_CTX = make_checkpointer()
    _CHECKPOINTER = _CP_CTX.__enter__()
    _GRAPH = build_graph(_CHECKPOINTER)
    logger.bind(agent='api').info('Graph compiled and ready')


def shutdown() -> None:
    global _CP_CTX, _CHECKPOINTER, _GRAPH
    if _CP_CTX is not None:
        try:
            _CP_CTX.__exit__(None, None, None)
        except Exception as e:
            logger.bind(agent='api').warning(f'Checkpointer shutdown error: {e}')
    _CP_CTX = None
    _CHECKPOINTER = None
    _GRAPH = None


def get_graph():
    if _GRAPH is None:
        startup()
    return _GRAPH
