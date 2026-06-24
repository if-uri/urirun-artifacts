# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
#
# The workflow domain: what a planned ticket and a flow ARE. These mirror the live Pydantic
# models in urirun (host/task_planner.py: PlannedTicket/TaskPlanningResult) and urirun-flow
# (Step/Flow), registered here so the chat→ticket→flow chain is validatable over artifact://
# without urirun-artifacts depending on those packages. Keep the fields in step with the source.

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import Artifact
from .enums import ExecutorMode
from ..registry import artifact


@artifact("planned-ticket", domain="workflow", title="Planned ticket",
          keywords=("ticket", "task", "planner", "chat", "automation"))
class PlannedTicket(Artifact):
    """One ticket the chat planner produced from a natural-language prompt — mirrors
    task_planner.PlannedTicket. The unit a chat request is decomposed into."""

    name: str = Field(description="Short ticket title")
    description: str = Field(default="", description="Longer description")
    priority: str = Field(default="normal", description="normal | high")
    sprint: str = Field(default="current", description="Sprint id")
    queue: str = Field(default="default", description="default | review | daily | inbox")
    labels: list[str] = Field(default_factory=list, description="Free-form labels")
    prompt: str = Field(description="The prompt handed to the executor")
    executor_kind: str = Field(default="uri-flow", description="Executor kind")
    executor_mode: ExecutorMode = Field(default=ExecutorMode.AUTOMATIC, description="automatic | interactive")
    executor_handler: str | None = Field(default="flow://host/chat-plan", description="Handler URI")
    max_attempts: int = Field(default=1, description="Retry budget")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Done-when checks")
    review_required: bool = Field(default=False, description="Needs human review before done")
    wait_for_input: bool = Field(default=False, description="Blocks on user input")
    clarification_prompt: str | None = Field(default=None, description="What to ask the user, if blocked")


@artifact("task-planning-result", domain="workflow", title="Task planning result",
          keywords=("planner", "result", "chat", "tickets"))
class TaskPlanningResult(Artifact):
    """The planner's full output for one prompt — mirrors task_planner.TaskPlanningResult."""

    ok: bool = Field(default=True, description="Planning succeeded")
    source: str = Field(default="heuristic", description="heuristic | llm")
    original_prompt: str = Field(description="The user's original request")
    needs_input: bool = Field(default=False, description="Planner needs clarification")
    requires_review: bool = Field(default=False, description="Any ticket needs review")
    tickets: list[PlannedTicket] = Field(default_factory=list, description="Planned tickets")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings")


@artifact("flow-step", domain="workflow", title="Flow step",
          keywords=("flow", "step", "uri", "dag"))
class FlowStep(Artifact):
    """One step of a flow — a URI to run plus its payload and dependencies (mirrors
    urirun_flow.Step). `kind` is derived from the URI tail when omitted."""

    id: str = Field(description="Step id, referenced by depends_on")
    uri: str = Field(description="The URI this step runs (scheme://...)")
    operation: str | None = Field(default=None, description="Optional explicit operation")
    kind: str | None = Field(default=None, description="query | command | assertion")
    payload: dict[str, Any] = Field(default_factory=dict, description="Step payload")
    depends_on: list[str] = Field(default_factory=list, description="Ids of prerequisite steps")


@artifact("flow", domain="workflow", title="Flow",
          keywords=("flow", "dag", "automation", "registry"))
class Flow(Artifact):
    """A flow: a DAG of steps with an allow-list and optional registry (mirrors
    urirun_flow.Flow)."""

    task: dict[str, Any] = Field(default_factory=dict, description="Task metadata")
    registry: str | None = Field(default=None, description="Registry path/URI the flow runs against")
    allow: list[str] = Field(default_factory=list, description="Allow-listed URI prefixes/schemes")
    steps: list[FlowStep] = Field(default_factory=list, description="Ordered steps (DAG)")


__all__ = ["PlannedTicket", "TaskPlanningResult", "FlowStep", "Flow"]
