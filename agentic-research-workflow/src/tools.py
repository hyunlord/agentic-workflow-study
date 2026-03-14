from __future__ import annotations

import ast
import calendar
import operator
from collections import Counter
from datetime import date, datetime
from typing import Any

from dateutil import parser as date_parser_lib

from src.config import DEFAULT_REFERENCE_DATE
from src.schemas import ToolOutput, ToolRequest
from src.utils import content_tokens, extract_dates, normalize_text


ALLOWED_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
ALLOWED_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class SafeEvaluator(ast.NodeVisitor):
    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp) -> float:
        operator_fn = ALLOWED_BINARY_OPERATORS.get(type(node.op))
        if operator_fn is None:
            raise ValueError("Unsupported operation in calculator expression.")
        return operator_fn(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        operator_fn = ALLOWED_UNARY_OPERATORS.get(type(node.op))
        if operator_fn is None:
            raise ValueError("Unsupported unary operation in calculator expression.")
        return operator_fn(self.visit(node.operand))

    def visit_Constant(self, node: ast.Constant) -> float:
        if not isinstance(node.value, int | float):
            raise ValueError("Calculator accepts numeric constants only.")
        return float(node.value)

    def generic_visit(self, node: ast.AST) -> float:
        raise ValueError(f"Unsupported calculator syntax: {type(node).__name__}")


def calculator(expression: str) -> dict[str, Any]:
    try:
        parsed = ast.parse(expression, mode="eval")
        result = SafeEvaluator().visit(parsed)
    except Exception as error:  # pragma: no cover - simple error normalization
        return {"ok": False, "error": str(error)}
    return {"ok": True, "result": int(result) if result.is_integer() else round(result, 3)}


def date_parser(text: str, reference_date: str = DEFAULT_REFERENCE_DATE) -> dict[str, Any]:
    normalized = normalize_text(text).lower()
    anchor = datetime.fromisoformat(reference_date).date()

    if normalized == "last quarter":
        quarter = (anchor.month - 1) // 3
        year = anchor.year if quarter > 0 else anchor.year - 1
        quarter = quarter if quarter > 0 else 4
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start = date(year, start_month, 1)
        end = date(year, end_month, calendar.monthrange(year, end_month)[1])
        return {"ok": True, "normalized": {"start": start.isoformat(), "end": end.isoformat()}}

    try:
        parsed = date_parser_lib.parse(text, fuzzy=True, default=datetime(anchor.year, 1, 1))
    except (ValueError, OverflowError):
        return {"ok": False, "error": f"Could not parse date from: {text}"}
    return {"ok": True, "normalized": parsed.date().isoformat()}


def keyword_extractor(text: str, limit: int = 5) -> dict[str, Any]:
    keywords = Counter(content_tokens(text))
    return {"ok": True, "keywords": [token for token, _ in keywords.most_common(limit)]}


def plan_tool_requests(
    query: str,
    query_type: str,
    retrieved_docs: list[dict[str, Any]],
) -> list[ToolRequest]:
    requests: list[ToolRequest] = []
    normalized = normalize_text(query).lower()
    evidence_text = " ".join(doc["text"] for doc in retrieved_docs)
    date_candidates = extract_dates(query) or extract_dates(evidence_text)

    if "how many days" in normalized or "days" in normalized or "며칠" in normalized:
        if len(date_candidates) >= 2:
            requests.append(ToolRequest("date_parser", {"text": date_candidates[0]}))
            requests.append(ToolRequest("date_parser", {"text": date_candidates[1]}))
            requests.append(ToolRequest("calculator", {"expression": "DATE_DIFF_DAYS"}))

    if query_type == "summary":
        requests.append(ToolRequest("keyword_extractor", {"text": evidence_text or query, "limit": 5}))

    return requests


def execute_tool_requests(tool_requests: list[ToolRequest]) -> list[ToolOutput]:
    outputs: list[ToolOutput] = []
    parsed_dates: list[str] = []

    for request in tool_requests:
        if request.tool_name == "calculator" and request.args.get("expression") == "DATE_DIFF_DAYS":
            if len(parsed_dates) < 2:
                outputs.append(ToolOutput("calculator", {"ok": False, "error": "DATE_DIFF_DAYS missing parsed dates"}))
                continue
            start = datetime.fromisoformat(parsed_dates[0]).date()
            end = datetime.fromisoformat(parsed_dates[1]).date()
            outputs.append(ToolOutput("calculator", {"ok": True, "result": abs((end - start).days)}))
            continue

        if request.tool_name == "calculator":
            outputs.append(ToolOutput("calculator", calculator(str(request.args.get("expression", "")))))
            continue

        if request.tool_name == "date_parser":
            parsed_output = date_parser(
                str(request.args.get("text", "")),
                str(request.args.get("reference_date", DEFAULT_REFERENCE_DATE)),
            )
            if parsed_output.get("ok") and isinstance(parsed_output.get("normalized"), str):
                parsed_dates.append(parsed_output["normalized"])
            outputs.append(ToolOutput("date_parser", parsed_output))
            continue

        if request.tool_name == "keyword_extractor":
            outputs.append(
                ToolOutput(
                    "keyword_extractor",
                    keyword_extractor(
                        str(request.args.get("text", "")),
                        int(request.args.get("limit", 5)),
                    ),
                )
            )
            continue

        outputs.append(ToolOutput(request.tool_name, {"ok": False, "error": "Unknown tool"}))

    return outputs
