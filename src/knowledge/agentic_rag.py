from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.config import settings
from src.knowledge.retriever import format_for_prompt, get_docs
from src.logger.custom_logger import logger
from src.tools.llm_factory import LLMFactory


class QueryPlan(BaseModel):
    queries: List[str] = Field(
        description='2-3 focused search queries covering distinct aspects of the task'
    )
    reasoning: str = Field(description='Why these queries, briefly')


class SufficiencyVerdict(BaseModel):
    sufficient: bool = Field(
        description='True if retrieved docs cover the task well enough to proceed'
    )
    gap: str = Field(
        default='',
        description='If insufficient, a short description of what is missing'
    )
    follow_up_query: str = Field(
        default='',
        description='If insufficient, a single focused query to fill the gap'
    )


_PLANNER_SYSTEM = (
    "You are a research planner for a code-generation agent. Given a coding task "
    "and a tech stack, produce 2-3 FOCUSED search queries that will retrieve the "
    "most useful current documentation. Each query should target a DISTINCT aspect "
    "(e.g., one for framework basics, one for a specific feature, one for testing). "
    "Queries should be 3-6 words each, suitable for a documentation search engine. "
    "Do NOT use site: or quotes."
)

_EVALUATOR_SYSTEM = (
    "You are evaluating whether retrieved documentation covers a coding task well "
    "enough that a developer could implement the task without hallucinating APIs. "
    "Consider: does the doc show current syntax? Does it cover the specific features "
    "needed? If something critical is missing, set sufficient=false, describe the "
    "gap, and propose one follow-up query; otherwise set sufficient=true."
)


class AgenticRetriever:
    def __init__(self, max_iterations: int | None = None) -> None:
        self.max_iterations = max_iterations or settings.AGENTIC_RAG_MAX_ITERATIONS
        self.log = logger.bind(agent='agentic_rag')

    def retrieve(
        self,
        task_description: str,
        stack: List[str],
        k_per_query: int | None = None
    ) -> List[Dict]:
        k_per_query = k_per_query or settings.RAG_CHUNKS_PER_QUERY

        if not stack:
            self.log.info('Empty stack - skipping retrieval')
            return []

        try:
            plan = self._plan_queries(task_description, stack)
            queries = plan.queries
        except Exception as e:
            self.log.warning(f'Planner failed, falling back to single query: {e}')
            queries = [task_description]

        self.log.info(f'Planned {len(queries)} queries: {queries}')

        all_chunks: List[Dict] = []
        seen = set()
        for q in queries:
            chunks = self._safe_get_docs(stack, q, k=k_per_query)
            for c in chunks:
                key = (c.get('source', ''), c.get('content', '')[:80])
                if key not in seen:
                    seen.add(key)
                    all_chunks.append(c)

        for iteration in range(self.max_iterations):
            try:
                verdict = self._evaluate(task_description, all_chunks)
            except Exception as e:
                self.log.warning(f'Evaluator failed, returning what we have: {e}')
                return all_chunks

            if verdict.sufficient:
                self.log.info(
                    f'Sufficient after {iteration + 1} iteration(s); '
                    f'{len(all_chunks)} chunks'
                )
                return all_chunks

            if not verdict.follow_up_query:
                self.log.info('Evaluator flagged gap but no follow-up - stopping')
                return all_chunks

            self.log.info(
                f"Gap: {verdict.gap} -> follow-up: '{verdict.follow_up_query}'"
            )
            new_chunks = self._safe_get_docs(
                stack, verdict.follow_up_query, k=k_per_query
            )

            for c in new_chunks:
                key = (c.get('source', ''), c.get('content', '')[:80])
                if key not in seen:
                    seen.add(key)
                    all_chunks.append(c)

        self.log.info(f'Max iterations reached; returning {len(all_chunks)} chunks')
        return all_chunks

    def _plan_queries(self, task: str, stack: List[str]) -> QueryPlan:
        llm = LLMFactory.get(temperature=0.0).with_structured_output(QueryPlan)
        stack_str = ', '.join(stack)
        return llm.invoke([
            SystemMessage(content=_PLANNER_SYSTEM),
            HumanMessage(content=(
                f'Task: {task}\n'
                f'Stack: {stack_str}\n\n'
                f'Produce the query plan'
            ))
        ])

    def _evaluate(self, task: str, chunks: List[Dict]) -> SufficiencyVerdict:
        if not chunks:
            return SufficiencyVerdict(
                sufficient=False,
                gap='No documentation retrieved at all.',
                follow_up_query=f'{task} documentation'
            )

        digest_lines = []
        for c in chunks[:10]:
            topic = c.get('topic', '?')
            source = c.get('source', '')
            content = c.get('content', '')[:400]
            digest_lines.append(f'[{topic}] {source}\n{content}')
        digest = '\n---\n'.join(digest_lines)

        llm = LLMFactory.get(temperature=0.0).with_structured_output(SufficiencyVerdict)
        return llm.invoke([
            SystemMessage(content=_EVALUATOR_SYSTEM),
            HumanMessage(content=(
                f'Task: {task}\n\n'
                f'Retrieved docs: \n{digest}\n\n'
                f'Evaluate sufficiency'
            ))
        ])

    def _safe_get_docs(self, stack: List[str], query: str, k: int) -> List[Dict]:
        try:
            return get_docs(stack=stack, query=query, k=k)
        except Exception as e:
            self.log.warning(f"get_docs failed for '{query}': {e}")
            return []


def retrieve_for_developer(
    requirements_summary: str,
    architecture: dict
) -> str:
    stack = architecture.get('stack', [])
    entry_point = architecture.get('entry_point', '')
    task = f'{requirements_summary}. Entry point: {entry_point}.'

    if not settings.TAVILY_API_KEY:
        logger.bind(agent='retriever').info(
            'TAVILY_API_KEY not set - skipping RAG'
        )
        return 'none (RAG disabled)'

    try:
        if settings.USE_AGENTIC_RAG:
            chunks = AgenticRetriever().retrieve(task_description=task, stack=stack)
        else:
            chunks = get_docs(
                stack=stack, query=task, k=settings.RAG_CHUNKS_PER_QUERY
            )
    except Exception as e:
        logger.bind(agent='retriever').warning(
            f'RAG failed (continuing without docs): {e}'
        )
        return 'none (retrieval error)'

    return format_for_prompt(chunks)
