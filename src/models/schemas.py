from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# Requirements

class UserStory(BaseModel):
    """A single feature requirement."""
    title: str
    description: str
    acceptance_criteria: List[str]


class Requirements(BaseModel):
    """Full project spec."""
    project_name: str = Field(description='kebab-case project name')
    summary: str
    user_stories: List[UserStory]
    non_functional: List[str] = Field(default_factory=list)


# Architecture

class FileSpec(BaseModel):
    """One file to create, with its relative path and purpose."""
    path: str = Field(description='Relative path inside the project')
    purpose: str


class Architecture(BaseModel):
    """System design output."""
    stack: List[str] = Field(description='Tech stack choices')
    components: List[str]
    files: List[FileSpec] = Field(description='Files to be generated')
    entry_point: str = Field(description="Command to run the app, e.g. 'uvicorn app.main:app'")


# Developer

class GeneratedFile(BaseModel):
    """A single generated source file."""
    path: str
    content: str


class Codebase(BaseModel):
    """The entire generated project."""
    files: List[GeneratedFile]
    notes: str = ''


# Code review

class ReviewIssue(BaseModel):
    file: str
    line: Optional[int] = None
    severity: Literal['low', 'medium', 'high'] = 'medium'
    message: str


class CodeReview(BaseModel):
    """Structured review of a generated codebase."""
    passed: bool = Field(description='True when the codebase is acceptable as-is')
    issues: List[ReviewIssue] = Field(default_factory=list)
    required_fixes: List[str] = Field(
        default_factory=list,
        description='Concrete, actionable fixes the developer must apply on the next attempt.'
    )
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


# Documentation

class PhaseDocument(BaseModel):
    """One Markdown report for a single SDLC phase."""
    phase: Literal['requirements', 'architecture', 'developer', 'qa', 'devops']
    title: str
    content_markdown: str
    summary: str = ''
