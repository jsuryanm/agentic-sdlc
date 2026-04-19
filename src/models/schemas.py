from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

# Requirement 

class UserStory(BaseModel):
    title: str
    description: str
    acceptance_criteria: List[str]

class Requirements(BaseModel):
    project_name: str = Field(description='kebab-case project name')
    summary: str
    user_stories: List[UserStory]
    non_functional: List[str] = Field(default_factory=list)

# Architect

class FileSpec(BaseModel):
    path: str = Field(description='Relative path inside the project')
    purpose: str

class Architecture(BaseModel):
    stack: List[str] = Field(description='Tech stack choices')
    components: List[str]
    files: List[FileSpec] = Field(description='Files to be generated')
    entry_point: str = Field(description="Command to run the app, e.g. 'uvicorn app.main:app'")

# Developer

class GeneratedFile(BaseModel):
    path: str
    content: str

class Codebase(BaseModel):
    files: List[GeneratedFile]
    notes: str = ''

# QA

class TestStatus(str, Enum):
    PASS = 'pass'
    FAIL = 'fail'
    ERROR = 'error'

class TestReport(BaseModel):
    status: TestStatus
    passed: int = 0
    failed: int = 0
    errors: List[str] = Field(default_factory=list)
    raw_output: str = ''

# DevOps

class DeploymentArtifacts(BaseModel):
    dockerfile: str
    ci_yaml: str
    branch_name: str
    pr_url: Optional[str] = None