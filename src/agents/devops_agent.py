import asyncio
import json
import time
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.a2a import DEVOPS_CARD
from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.models.schemas import DeploymentArtifacts
from src.pipelines.context import ContextManager
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory
from src.prompts.devops_prompt import DEVOPS_PROMPT

class DevOpsAgent(BaseAgent):
    name = "devops_agent"
    card = DEVOPS_CARD
    projection_fn = ContextManager.for_devops

    def __init__(self):
        super().__init__()
        self._chain = (
            DEVOPS_PROMPT
            | LLMFactory.get().with_structured_output(DeploymentArtifacts)
        )

    def _process(self, state: SDLCState, projection: Dict[str, Any]) -> dict:
        arch = state["architecture"]
        reqs = state["requirements"]
        project_dir = Path(state["codebase"]["project_dir"])
        
        repo_name = reqs.get("project_name", "generated-project").lower().replace(" ", "-").strip()

        plan = self._chain.invoke({
            "project_name": repo_name,
            "entry_point": arch["entry_point"],
            "stack": arch["stack"],
        })

        # Write artifacts to local disk
        (project_dir / "Dockerfile").write_text(plan.dockerfile, encoding="utf-8")
        ci_dir = project_dir / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "ci.yml").write_text(plan.ci_yaml, encoding="utf-8")

        # Per-run branch so reruns don't collide with a prior run's branch
        # (which would make every file-create hit "already exists" and the
        # resulting PR have zero commits).
        thread_id = state.get("thread_id") or ""
        suffix = (thread_id[:8] or "run").lower()
        branch_name = f"init-codebase-{suffix}"
        pr_url = self._run_async(self._push_via_mcp(project_dir, branch_name, repo_name, reqs["project_name"]))

        return {
            "deployment": {
                **plan.model_dump(), 
                "branch_name": branch_name,
                "pr_url": pr_url, 
                "project_dir": str(project_dir),
                "repo_name": repo_name
            },
            "status": "deployment_ready",
        }

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try: return loop.run_until_complete(coro)
        finally: loop.close()

    async def _push_via_mcp(self, project_dir: Path, branch: str, repo_name: str, display_name: str) -> Optional[str]:
        try:
            client = MultiServerMCPClient({
                "github": {
                    "transport": "streamable_http",
                    "url": settings.GITHUB_MCP_URL,
                    "headers": {"Authorization": f"Bearer {settings.GITHUB_PERSONAL_ACCESS_TOKEN}"},
                }
            })
            tools = await client.get_tools()
            tool_map = {t.name: t for t in tools}
            owner = settings.GITHUB_REPO_OWNER

            # Tools
            create_repo_tool = tool_map.get("create_repository")
            commit_tool = tool_map.get("create_or_update_file")
            branch_tool = tool_map.get("create_branch")
            pr_tool = tool_map.get("create_pull_request")
            get_contents_tool = tool_map.get("get_file_contents")

            # 1. CREATE REPO (Ignore if exists)
            try:
                self.logger.info(f"Step 1: Ensure repository {repo_name} exists...")
                await create_repo_tool.ainvoke({"name": repo_name})
                await asyncio.sleep(2)
            except Exception as e:
                if "422" in str(e): self.logger.info("Repo already exists.")

            # 2. CHECK MAIN & BOOTSTRAP WITH PLACEHOLDER
            try:
                await get_contents_tool.ainvoke({"owner": owner, "repo": repo_name, "path": "README.md", "ref": "main"})
                self.logger.info("Step 2: 'main' is already initialized.")
            except Exception:
                self.logger.info("Step 2: Seeding 'main' with placeholder README...")
                await commit_tool.ainvoke({
                    "owner": owner, "repo": repo_name,
                    "path": "README.md",
                    "content": f"# {display_name}\n\nInitial repository setup.",
                    "branch": "main",
                    "message": "chore: bootstrap repository"
                })
                await asyncio.sleep(2)

            # 3. CREATE FEATURE BRANCH (Ignore if exists)
            try:
                self.logger.info(f"Step 3: Creating branch {branch}...")
                await branch_tool.ainvoke({"owner": owner, "repo": repo_name, "branch": branch, "base": "main"})
            except Exception as e:
                self.logger.info(f"Branch {branch} already exists or error: {e}")

            # 4. UPSERT FILES (Handle SHAs correctly)
            files = self._collect_all_files(project_dir)
            for f in files:
                path = f["path"]
                # ALWAYS check for SHA on the target branch before pushing
                sha = await self._resolve_sha(get_contents_tool, owner, repo_name, path, [branch])
                
                try:
                    await commit_tool.ainvoke({
                        "owner": owner, "repo": repo_name,
                        "path": path,
                        "content": f["content"] or "\n",
                        "branch": branch,
                        "message": f"update: {path}",
                        **({"sha": sha} if sha else {})
                    })
                    self.logger.info(f"Pushed: {path}")
                except Exception as e:
                    self.logger.error(f"Failed {path}: {e}")

            # 5. CREATE PR
            try:
                pr_result = await pr_tool.ainvoke({
                    "owner": owner, "repo": repo_name, 
                    "title": f"SDLC: Initial Codebase for {display_name}",
                    "body": "This PR contains the generated FastAPI logic and CI/CD configurations.",
                    "head": branch, "base": "main"
                })
                return self._extract_url(pr_result)
            except Exception as e:
                if "A pull request already exists" in str(e):
                    # Attempt to find the existing PR URL in the error or repo
                    return f"https://github.com/{owner}/{repo_name}/pulls"
                self.logger.error(f"PR Error: {e}")

            return None

        except Exception as e:
            self.logger.error(f"Global MCP Error: {e}")
            return None

    # --- HELPERS (SAME AS PREVIOUS) ---
    def _collect_all_files(self, project_dir: Path) -> List[Dict[str, str]]:
        files = []
        exclude = {".git", "__pycache__", "venv", ".venv", ".DS_Store", ".pytest_cache"}
        for p in project_dir.rglob("*"):
            if p.is_file() and not any(x in p.parts for x in exclude):
                try:
                    files.append({
                        "path": p.relative_to(project_dir).as_posix(),
                        "content": p.read_text(encoding="utf-8", errors="replace")
                    })
                except Exception: continue
        return files

    async def _resolve_sha(self, tool, owner, repo, path, refs):
        if not tool: return None
        for ref in refs:
            try:
                res = await tool.ainvoke({"owner": owner, "repo": repo, "path": path, "ref": ref})
                sha = self._extract_sha(res, path)
                if sha: return sha
            except: continue
        return None

    def _extract_sha(self, res: Any, path: str) -> Optional[str]:
        """Dig `sha` out of whatever shape GitHub's MCP server returns.

        GitHub REST wraps single-file content as `{"sha": ..., "path": ..., ...}`,
        but MCP adapters often wrap the whole thing again as either a JSON
        string, or a list of ``{"type": "text", "text": "<json>"}`` content
        blocks. We handle all three plus directory-listing (list of entries).
        """
        if not res:
            return None

        # MCP content-block list: [{"type": "text", "text": "<json>"}, ...]
        if isinstance(res, list) and res and all(
            isinstance(x, dict) and 'text' in x for x in res
        ):
            merged = '\n'.join(x.get('text', '') for x in res)
            try:
                return self._extract_sha(json.loads(merged), path)
            except Exception:
                match = re.search(r'"sha"\s*:\s*"([0-9a-f]{7,40})"', merged)
                return match.group(1) if match else None

        if isinstance(res, str):
            try:
                return self._extract_sha(json.loads(res), path)
            except Exception:
                match = re.search(r'"sha"\s*:\s*"([0-9a-f]{7,40})"', res)
                return match.group(1) if match else None

        if isinstance(res, dict):
            if res.get('sha'):
                return res['sha']
            for k in ('content', 'data', 'item', 'result', 'file'):
                inner = res.get(k)
                if isinstance(inner, (dict, list, str)):
                    sha = self._extract_sha(inner, path)
                    if sha:
                        return sha

        if isinstance(res, list):
            for item in res:
                if isinstance(item, dict):
                    if item.get('path') == path and item.get('sha'):
                        return item['sha']
                    sha = self._extract_sha(item, path)
                    if sha:
                        return sha

        return getattr(res, 'sha', None)

    def _extract_url(self, result: Any) -> Optional[str]:
        if not result: return None
        if isinstance(result, str) and "github.com" in result: return result
        if isinstance(result, dict):
            url = result.get("html_url") or result.get("url")
            if not url:
                for key in ["item", "data", "pull_request"]:
                    inner = result.get(key, {})
                    if isinstance(inner, dict):
                        url = inner.get("html_url") or inner.get("url")
                        if url: break
            if isinstance(url, str): return url
        match = re.search(r'https://github\.com/[^"\s\']+/pull/\d+', str(result))
        return match.group(0) if match else None