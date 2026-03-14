from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from src.utils import normalize_text


Handler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class PlanStep:
    step_id: str
    objective: str
    rationale: str
    tool_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlanGenerator:
    STRATEGIES = ("react", "planner_executor", "decompose")

    def generate_plan(self, task: str, strategy: str = "planner_executor") -> list[dict[str, Any]]:
        normalized_task = normalize_text(task)
        strategy_name = strategy if strategy in self.STRATEGIES else "planner_executor"

        if strategy_name == "react":
            steps = [
                PlanStep("react_1", f"Observe the task: {normalized_task}", "Start by reading the request carefully."),
                PlanStep("react_2", "Think about what information is missing.", "Identify gaps before acting."),
                PlanStep("react_3", "Act with the best available tool or retrieval step.", "Collect evidence or perform a calculation.", "tool_or_retrieval"),
                PlanStep("react_4", "Observe the result and check whether it is enough.", "Use tool output to decide the next move."),
                PlanStep("react_5", "Respond with the grounded result.", "Finish only after the evidence supports the answer."),
            ]
            return [step.to_dict() for step in steps]

        if strategy_name == "decompose":
            clauses = self._decompose_task(normalized_task)
            steps = [
                PlanStep(
                    step_id=f"decompose_{index}",
                    objective=clause,
                    rationale="Solve one sub-problem at a time to reduce cognitive load.",
                    tool_hint="retrieval" if "find" in clause.lower() or "lookup" in clause.lower() else None,
                )
                for index, clause in enumerate(clauses, start=1)
            ]
            return [step.to_dict() for step in steps]

        steps = [
            PlanStep("plan_1", f"Clarify the objective: {normalized_task}", "Define what a successful answer should contain."),
            PlanStep("plan_2", "Gather evidence for each important part of the task.", "Planner-executor systems work best with explicit evidence collection.", "retrieval"),
            PlanStep("plan_3", "Execute any focused tools needed for calculations or lookups.", "Use tools only after the sub-tasks are clear.", "tool"),
            PlanStep("plan_4", "Synthesize the final response from evidence and tool outputs.", "Combine the executor outputs into a coherent answer."),
        ]
        return [step.to_dict() for step in steps]

    def compare_strategies(self, task: str) -> dict[str, list[dict[str, Any]]]:
        return {strategy: self.generate_plan(task, strategy=strategy) for strategy in self.STRATEGIES}

    def _decompose_task(self, task: str) -> list[str]:
        separators = (" and ", " then ", ",")
        parts = [task]
        for separator in separators:
            if separator in task.lower():
                parts = [normalize_text(part) for part in task.split(separator) if normalize_text(part)]
                break
        if len(parts) == 1:
            return [
                f"Identify the core request in: {task}",
                "Collect the evidence needed for the request.",
                "Produce a grounded final answer.",
            ]
        return [f"Handle sub-task: {part}" for part in parts]


class PlanExecutor:
    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}

    def register_handler(self, name: str, handler: Handler) -> None:
        self.handlers[name] = handler

    def execute(self, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
        execution_log: list[dict[str, Any]] = []
        for step in plan:
            tool_hint = step.get("tool_hint")
            handler = self.handlers.get(tool_hint or "", self._default_handler)
            result = handler(step)
            execution_log.append(
                {
                    "step_id": step["step_id"],
                    "objective": step["objective"],
                    "tool_hint": tool_hint,
                    "status": result.get("status", "completed"),
                    "output": result.get("output", ""),
                }
            )
        return execution_log

    @staticmethod
    def _default_handler(step: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "completed",
            "output": f"Executed step: {step['objective']}",
        }


__all__ = ["PlanGenerator", "PlanExecutor", "PlanStep"]
