from __future__ import annotations


PLAN_TEMPLATES = {
    "simple_lookup": [
        "retrieve relevant evidence",
        "draft concise grounded answer",
        "verify citation support",
    ],
    "comparison": [
        "retrieve evidence for each target",
        "compare aligned facts",
        "draft structured comparison answer",
        "verify grounding",
    ],
    "multi_hop": [
        "decompose question into sub-parts",
        "retrieve multi-source evidence",
        "optionally call helper tools",
        "synthesize reasoning chain",
        "verify grounding before final answer",
    ],
    "summary": [
        "retrieve major sections",
        "compress key points",
        "verify key claims are grounded",
    ],
    "insufficient_evidence_risk": [
        "retrieve the closest available evidence",
        "check whether the request exceeds document scope",
        "abstain if grounding is weak",
    ],
}


def make_plan(query_type: str) -> list[str]:
    return PLAN_TEMPLATES.get(query_type, PLAN_TEMPLATES["simple_lookup"]).copy()
