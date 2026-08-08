"""
Task engine for JARVIS (Phase 1).

Holds a dependency graph of Tasks and exposes readiness computation so the
orchestrator can run independent tasks in parallel and never start a task
before its dependencies complete. Modeled on the Multi-Agent Systems
Architect's hierarchical pattern with explicit state.
"""
from __future__ import annotations

from typing import Dict, List

from ..models.schemas import Task, TaskStatus, TaskView


class TaskGraph:
    def __init__(self, goal: str) -> None:
        self.goal = goal
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> Task:
        self.tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> Task:
        return self.tasks[task_id]

    def ready_to_run(self) -> List[Task]:
        """Tasks whose dependencies are all complete (or have none)."""
        out = []
        for task in self.tasks.values():
            if task.status != TaskStatus.QUEUED:
                continue
            if all(
                self.tasks[d].status == TaskStatus.COMPLETE
                for d in task.depends_on
                if d in self.tasks
            ):
                out.append(task)
        return out

    def all_complete(self) -> bool:
        return bool(self.tasks) and all(
            t.status in (TaskStatus.COMPLETE, TaskStatus.FAILED)
            for t in self.tasks.values()
        )

    def views(self) -> List[TaskView]:
        return [
            TaskView(
                id=t.task_id,
                agent_id=t.agent_id,
                goal=t.goal,
                status=t.status,
                depends_on=t.depends_on,
            )
            for t in self.tasks.values()
        ]
