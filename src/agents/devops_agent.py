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

        # Generate deployment artifacts (Dockerfile, CI/CD YAML)
        plan = self._chain.invoke({
            "project_name": reqs["project_name"],
            "entry_point": arch["entry_point"],
            "stack": arch["stack"],
        })

        # 1. Sync generated files to local disk
        (project_dir / "Dockerfile").write_text(plan.dockerfile, encoding="utf-8")
        ci_dir = project_dir / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)
        (ci_dir / "ci.yml").write_text(plan.ci_yaml, encoding="utf-8")

        self.logger.info(f"Artifacts prepared in {project_dir}")

        # 2. Setup unique branch to ensure a blank slate every run
        unique_branch = f"deploy-{int(time.time())}"
        
        # 3. Execute MCP Push and PR creation
        pr_url = self._run_async(self._push_via_mcp(project_dir, unique_branch, reqs["project_name"]))

        return {
            "deployment": {
                **plan.model_dump(), 
                "branch_name": unique_branch,
                "pr_url": pr_url, 
                "project_dir": str(project_dir)
            },
            "status": "deployment_ready",
        }

    def _run_async(self, coro):
        """Helper to safely manage the async event loop in a sync context."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _push_via_mcp(self, project_dir: Path, branch: str, project_name: str) -> Optional[str]:
        try:
            client = MultiServerMCPClient({
                "github": {
                    "transport": "streamable_http",
                    "url": settings.GITHUB_MCP_URL,
                    "headers": {"Authorization": f"Bearer {settings.GITHUB_PERSONAL_ACCESS_TOKEN}"},
                }
            })
            tools = await client.get_tools()
            owner, repo = settings.GITHUB_REPO_OWNER, settings.GITHUB_REPO_NAME

            # --- STRICT TOOL MAPPING ---
            # Mapping names exactly to avoid 'update_pull_request' (which causes pullNumber errors)
            tool_map = {t.name: t for t in tools}
            
            commit_tool = tool_map.get("create_or_update_file")
            branch_tool = tool_map.get("create_branch")
            pr_tool = tool_map.get("create_pull_request")
            get_contents_tool = tool_map.get("get_file_contents")

            if not all([commit_tool, branch_tool, pr_tool]):
                self.logger.error("Missing critical GitHub tools in MCP toolset.")
                return None

            # 1. Create the new isolated branch
            await branch_tool.ainvoke({"owner": owner, "repo": repo, "branch": branch, "base": "main"})
            self.logger.info(f"Created isolated branch: {branch}")

            # 2. Collect and push ALL files (app logic + requirements + devops files)
            files_to_push = self._collect_all_files(project_dir)
            pushed_count = 0
            
            for f in files_to_push:
                path = f["path"]
                # Resolve SHA from deploy branch first (in case we already pushed
                # it this run) then fall back to main.
                sha = await self._resolve_sha(
                    get_contents_tool, owner, repo, path, [branch, "main"]
                )

                # GitHub Contents API rejects empty bodies on create/update.
                content = f["content"] if f["content"] else "\n"

                try:
                    await commit_tool.ainvoke({
                        "owner": owner, "repo": repo,
                        "path": path,
                        "content": content,
                        "branch": branch,
                        "message": f"SDLC Automator: Adding {path}",
                        **({"sha": sha} if sha else {})
                    })
                    pushed_count += 1
                    self.logger.info(f"Successfully pushed: {path}")
                except Exception as e:
                    self.logger.error(f"Failed to push {path}: {e}")

            # 3. Create the Pull Request and extract ONLY the URL
            if pushed_count > 0:
                try:
                    self.logger.info(f"Opening Pull Request for {branch}...")
                    pr_result = await pr_tool.ainvoke({
                        "owner": owner, "repo": repo, 
                        "title": f"SDLC Deployment: {project_name}",
                        "body": "Automated deployment PR with code and CI/CD artifacts.",
                        "head": branch, 
                        "base": "main"
                    })
                    
                    # Ensure we only return a clean string URL
                    clean_url = self._extract_url(pr_result)
                    if clean_url:
                        self.logger.info(f"PR CREATED: {clean_url}")
                        return clean_url
                        
                except Exception as pr_e:
                    self.logger.error(f"PR Creation Failed: {pr_e}")

            return None

        except Exception as e:
            self.logger.error(f"Global MCP Workflow Error: {e}")
            return None

    def _collect_all_files(self, project_dir: Path) -> List[Dict[str, str]]:
        """Scans directory and captures everything not explicitly ignored."""
        files = []
        exclude = {".git", "__pycache__", "venv", ".venv", ".DS_Store", ".pytest_cache"}
        for p in project_dir.rglob("*"):
            if p.is_file() and not any(x in p.parts for x in exclude):
                try:
                    files.append({
                        "path": p.relative_to(project_dir).as_posix(),
                        "content": p.read_text(encoding="utf-8", errors="replace")
                    })
                except Exception as e:
                    self.logger.warning(f"Skipping unreadable file {p}: {e}")
        return files

    async def _resolve_sha(self, tool, owner, repo, path, refs):
        """Fetches the SHA of a file if it exists in the specified git references.

        MCP tool responses vary — dict, pydantic-ish object, JSON string, or
        JSON array (for directory listings). Try each shape before giving up.
        """
        if not tool:
            return None
        for ref in refs:
            try:
                res = await tool.ainvoke(
                    {"owner": owner, "repo": repo, "path": path, "ref": ref}
                )
            except Exception:
                continue
            sha = self._extract_sha(res, path)
            if sha:
                return sha
        return None

    @staticmethod
    def _extract_sha(res: Any, path: str) -> Optional[str]:
        if res is None:
            return None
        if isinstance(res, str):
            try:
                res = json.loads(res)
            except Exception:
                return None
        if isinstance(res, dict):
            if res.get("sha"):
                return res["sha"]
            inner = res.get("content") or res.get("data") or res.get("item")
            if isinstance(inner, (dict, list)):
                return DevOpsAgent._extract_sha(inner, path)
            return None
        if isinstance(res, list):
            # Directory listing — match our exact path.
            for item in res:
                if isinstance(item, dict):
                    if item.get("path") == path and item.get("sha"):
                        return item["sha"]
            return None
        return getattr(res, "sha", None)

    def _extract_url(self, result: Any) -> Optional[str]:
        """Strictly extracts a GitHub PR URL string from various response formats."""
        if not result: return None
        
        # Check for direct string
        if isinstance(result, str) and "github.com" in result:
            return result

        # Check dictionary keys
        if isinstance(result, dict):
            url = result.get("html_url") or result.get("url")
            if not url:
                # Handle nested formats
                for key in ["item", "data", "pull_request"]:
                    inner = result.get(key, {})
                    if isinstance(inner, dict):
                        url = inner.get("html_url") or inner.get("url")
                        if url: break
            if isinstance(url, str): return url

        # Regex fallback
        match = re.search(r'https://github\.com/[^"\s\']+/pull/\d+', str(result))
        return match.group(0) if match else None