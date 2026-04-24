import asyncio
import json
import base64
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

        # Generate plan (the prompt should naturally use 'uv' based on project context)
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
        try: 
            return loop.run_until_complete(coro)
        finally: 
            loop.close()

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

            create_repo_tool = tool_map.get("create_repository")
            commit_tool = tool_map.get("create_or_update_file")
            branch_tool = tool_map.get("create_branch")
            pr_tool = tool_map.get("create_pull_request")
            get_contents_tool = tool_map.get("get_file_contents")

            # 1. CREATE REPO
            try:
                self.logger.info(f"Step 1: Ensuring repository {repo_name} exists...")
                await create_repo_tool.ainvoke({"name": repo_name})
                await asyncio.sleep(2)
            except Exception as e:
                if "422" in str(e): self.logger.info("Repo already exists.")

            # 2. BOOTSTRAP MAIN
            try:
                await get_contents_tool.ainvoke({"owner": owner, "repo": repo_name, "path": "README.md", "ref": "main"})
            except Exception:
                self.logger.info("Step 2: Seeding 'main'...")
                await commit_tool.ainvoke({
                    "owner": owner, "repo": repo_name,
                    "path": "README.md",
                    "content": f"# {display_name}\n\nInitial repository setup.",
                    "branch": "main",
                    "message": "chore: bootstrap repository"
                })
                await asyncio.sleep(2)

            # 3. CREATE FEATURE BRANCH
            try:
                await branch_tool.ainvoke({"owner": owner, "repo": repo_name, "branch": branch, "base": "main"})
            except Exception:
                self.logger.info(f"Branch {branch} ready.")

            # 4. UPSERT FILES (With "Ignore if Identical" logic)
            files = self._collect_all_files(project_dir)
            for f in files:
                path = f["path"]
                local_content = f["content"] or "\n"
                
                # Check remote state
                remote_data = await self._fetch_remote_data(get_contents_tool, owner, repo_name, path, branch)
                
                if remote_data:
                    # Skip if content matches exactly
                    if remote_data.get("content") == local_content:
                        self.logger.info(f"Skipping {path}: No changes detected.")
                        continue
                    sha = remote_data.get("sha")
                else:
                    sha = None

                try:
                    await commit_tool.ainvoke({
                        "owner": owner, "repo": repo_name,
                        "path": path,
                        "content": local_content,
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
                    "body": "Generated logic and CI/CD configurations.",
                    "head": branch, "base": "main"
                })
                return self._extract_url(pr_result)
            except Exception as e:
                if "pull request already exists" in str(e).lower():
                    return f"https://github.com/{owner}/{repo_name}/pulls"
                return None

        except Exception as e:
            self.logger.error(f"Global MCP Error: {e}")
            return None

    # --- HELPERS ---

    async def _fetch_remote_data(self, tool, owner, repo, path, branch) -> Optional[dict]:
        """Fetches remote SHA and decodes content for comparison."""
        try:
            res = await tool.ainvoke({"owner": owner, "repo": repo, "path": path, "ref": branch})
            raw = self._get_raw_json(res)
            if not raw: return None

            content = raw.get("content", "")
            if raw.get("encoding") == "base64":
                try:
                    # Clean newlines from base64 string before decoding
                    content = base64.b64decode(content.replace("\n", "")).decode("utf-8")
                except: pass
            
            return {"sha": raw.get("sha"), "content": content}
        except:
            return None

    def _get_raw_json(self, res: Any) -> Optional[dict]:
        if isinstance(res, list) and res:
            merged = '\n'.join(x.get('text', '') for x in res if 'text' in x)
            try: return json.loads(merged)
            except: return None
        if isinstance(res, str):
            try: return json.loads(res)
            except: return None
        return res if isinstance(res, dict) else None

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
                except: continue
        return files

    def _extract_url(self, result: Any) -> Optional[str]:
        if not result: return None
        res_str = str(result)
        match = re.search(r'https://github\.com/[^"\s\']+/pull/\d+', res_str)
        if match: return match.group(0)
        
        raw = self._get_raw_json(result)
        if isinstance(raw, dict):
            return raw.get("html_url") or raw.get("url")
        return None