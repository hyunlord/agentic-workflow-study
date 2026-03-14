from __future__ import annotations

from typing import Any

from src.utils import content_tokens, extract_dates, normalize_text, overlap_ratio, sentence_split


def _clean_sentence(sentence: str) -> str:
    cleaned = sentence.replace("Leadership FAQ", "").strip()
    if "A:" in cleaned:
        cleaned = cleaned.split("A:", 1)[1].strip()
    elif cleaned.startswith("Q:"):
        return ""
    return normalize_text(cleaned)


def _rank_sentences(query: str, retrieved_docs: list[dict[str, Any]]) -> list[tuple[float, str, dict[str, Any]]]:
    query_tokens = content_tokens(query)
    ranked: list[tuple[float, str, dict[str, Any]]] = []

    for doc in retrieved_docs:
        for raw_sentence in sentence_split(doc["text"]):
            sentence = _clean_sentence(raw_sentence)
            if not sentence:
                continue
            overlap = overlap_ratio(query_tokens, content_tokens(sentence))
            score = (overlap * 1.6) + (float(doc.get("score", 0.0)) * 0.35)
            ranked.append((score, sentence, doc))

    return sorted(ranked, key=lambda item: item[0], reverse=True)


def _tool_notes(tool_outputs: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    for output in tool_outputs:
        if output["tool_name"] == "calculator" and output["output"].get("ok"):
            notes.append(f"Computed value: {output['output']['result']}.")
        if output["tool_name"] == "keyword_extractor" and output["output"].get("ok"):
            notes.append(f"Key themes: {', '.join(output['output']['keywords'])}.")
    return notes


def build_baseline_answer(query: str, retrieved_docs: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = _rank_sentences(query, retrieved_docs)
    evidence = [sentence for _, sentence, _ in ranked[:2]]
    citations = [
        {
            "doc_id": doc["doc_id"],
            "chunk_id": doc["chunk_id"],
            "source": doc["source"],
            "score": doc["score"],
        }
        for doc in retrieved_docs[:3]
    ]
    answer = " ".join(evidence) if evidence else "No relevant evidence was retrieved."
    return {"draft_answer": answer, "citations": citations}


def synthesize_answer(
    query: str,
    query_type: str,
    retrieved_docs: list[dict[str, Any]],
    tool_outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_query = normalize_text(query).lower()
    ranked = _rank_sentences(query, retrieved_docs)
    evidence_sentences = [sentence for _, sentence, _ in ranked[:3]]
    citations = []
    seen_chunks: set[str] = set()
    for _, _, doc in ranked[:3]:
        if doc["chunk_id"] in seen_chunks:
            continue
        citations.append(
            {
                "doc_id": doc["doc_id"],
                "chunk_id": doc["chunk_id"],
                "source": doc["source"],
                "score": doc["score"],
            }
        )
        seen_chunks.add(doc["chunk_id"])

    if not evidence_sentences:
        draft = "I could not find grounded evidence for this question in the loaded documents."
        return {"draft_answer": draft, "citations": citations}

    calculator_result = next(
        (
            output["output"]["result"]
            for output in tool_outputs
            if output["tool_name"] == "calculator" and output["output"].get("ok")
        ),
        None,
    )
    date_mentions = extract_dates(" ".join(doc["text"] for doc in retrieved_docs))

    if ("how many days" in normalized_query or "days" in normalized_query) and calculator_result is not None:
        if len(date_mentions) >= 2:
            body = f"The pilot window spans {calculator_result} days, from {date_mentions[0]} to {date_mentions[1]}."
        else:
            body = f"The relevant duration is {calculator_result} days."
    elif query_type == "comparison":
        comparison_sentence = next(
            (sentence for sentence in evidence_sentences if "while" in sentence.lower() or "different" in sentence.lower()),
            evidence_sentences[0],
        )
        body = comparison_sentence
    elif query_type == "summary":
        distinct_sentences: list[str] = []
        seen_sources: set[str] = set()
        for _, sentence, doc in ranked:
            if doc["source"] in seen_sources:
                continue
            distinct_sentences.append(sentence)
            seen_sources.add(doc["source"])
            if len(distinct_sentences) == 3:
                break
        body = " ".join(distinct_sentences)
    elif "risk" in normalized_query:
        body = next((sentence for sentence in evidence_sentences if "risk" in sentence.lower()), evidence_sentences[0])
    elif "goal" in normalized_query:
        body = next((sentence for sentence in evidence_sentences if "goal" in sentence.lower()), evidence_sentences[0])
    elif "when" in normalized_query and date_mentions:
        body = next((sentence for sentence in evidence_sentences if extract_dates(sentence)), evidence_sentences[0])
    elif query_type == "multi_hop":
        body = " ".join(evidence_sentences[:2])
    else:
        body = evidence_sentences[0]

    notes = _tool_notes(tool_outputs)
    if notes:
        body = f"{body} {' '.join(notes)}"

    source_list = ", ".join(citation["source"] for citation in citations) or "no sources"
    draft = f"{body} Sources: {source_list}."
    return {"draft_answer": draft, "citations": citations}
