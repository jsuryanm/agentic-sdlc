from pathlib import Path 

from langchain.agents import create_agent

from src.agents.base_agent import BaseAgent
from src.core.config import settings
from src.models.schemas import DeploymentArtifacts
from src.pipelines.state import SDLCState
from src.tools.llm_factory import LLMFactory
from src.tools.mcp_client import GitHubMCPClient
from src.prompts.devops_prompt import DEVOPS_PROMPT

class DeploymentPlan(DeploymentArtifacts):
    """Internal — just the artifacts, PR URL filled in after MCP call."""
    pass 

class DevOpsAgent(BaseAgent):
    """Generates Dockerfile + CI yaml, writes them into the project, then uses
    GitHub MCP to commit the whole project on a feature branch and open a PR."""

    def __init__(self):
        super().__init__()
        self._chain = (DEVOPS_PROMPT 
                       | LLMFactory.get().with_structured_output(DeploymentArtifacts))

    def _process(self,state: SDLCState) -> dict:
        arch = state["architecture"]
        reqs = state["requirements"]
        project_dir = Path(state["codebase"]["project_dir"])

        plan: DeploymentPlan = self._chain.invoke({
            "project_name":reqs["project_name"],
            "entry_point":arch["entry_point"],
            "stack":arch["stack"]
        })

        # saves dockerfile 
        (project_dir / "Dockerfile").write_text(plan.dockerfile,encoding="utf-8")
        
        ci_dir = project_dir / ".github" / "workflows"
        ci_dir.mkdir(parents=True,exist_ok=True)
        (ci_dir/"ci.yml").write_text(plan.ci_yaml,encoding="utf-8")

        self.logger.info(f"Wrote Dockerfile and CI to {project_dir}")

        pr_url = self._push_via_mcp(project_dir, plan.branch_name, reqs["project_name"])

        return {
            "deployment":{
                **plan.model_dump(),
                "pr_url":pr_url,
                "project_url":str(project_dir)},
            
            "status":"deployment_ready" 
        }
    
    def _push_via_mcp(self,
                      project_dir: Path,
                      branch: str,
                      project_name: str) -> str | None:
        """Use GitHub MCP tools via a create_agent call to push the project."""
        try:
            tools = GitHubMCPClient().load_tools_sync()
            agent = create_agent(LLMFactory.get(),tools)

            files_listing = self._collect_files(project_dir)
            prompt = (
                f"Commit these files to repo {settings.GITHUB_REPO_OWNER}/"
                f"{settings.GITHUB_REPO_NAME} on a new branch '{branch}' "
                f"(base: main). Then open a pull request titled "
                f"'Agentic SDLC: {project_name}' with a short description.\n\n"
                f"Files:\n{files_listing}"
            )

            result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})

            last = result["messages"][-1].content if result.get("messages") else ""
            if isinstance(last, str) and "pull/" in last:
                # crude extraction; fine for demo
                import re
                m = re.search(r"https://github\.com/\S+/pull/\d+", last)
                if m: return m.group(0)
            return None
        except Exception as e:
            self.logger.warning(f"MCP push failed (non-fatal for demo): {e}")
            return None
    
    @staticmethod
    def _collect_files(project_dir: Path) -> str:
        lines = []

        for p in sorted(project_dir.rglob("*")):
            if p.is_file() and ".git" not in p.parts:
                # ignore git folder
                rel = p.relative_to(project_dir) # relative path
                content = p.read_text(encoding="utf-8", errors="ignore")
                lines.append(f"--- {rel} ---\n{content[:4000]}")
        return "\n\n".join(lines)