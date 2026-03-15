from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TECH_DOCS_DIR = RAW_DIR / "tech_docs"

USER_AGENT = "agentic-research-workflow-tech-doc-fetcher/0.1"
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 0.2

SITE_SELECTORS = {
    "anthropic": ["main", "article", '[role="main"]'],
    "langgraph": ["main", "article", '[role="main"]'],
    "sentence_transformers": ['div[role="main"]', "main", ".wy-nav-content", ".document"],
}

REMOVE_SELECTORS = [
    "nav",
    "header",
    "footer",
    "aside",
    "script",
    "style",
    "noscript",
    "button",
    ".sidebar",
    ".toc",
    ".table-of-contents",
    ".breadcrumbs",
    ".wy-nav-side",
    ".wy-side-nav-search",
    ".rst-footer-buttons",
    ".sphinxsidebar",
    ".edit-this-page",
]


@dataclass(frozen=True)
class TargetPage:
    domain: str
    url: str


TARGETS: tuple[TargetPage, ...] = (
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/mcp-connector"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/tool-use/fine-grained-tool-streaming"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-tools"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/quickstart"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices"),
    TargetPage("anthropic", "https://platform.claude.com/docs/en/agent-sdk/overview"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/overview.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/quickstart.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/workflows-agents.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/application-structure.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/choosing-apis.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/graph-api.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/functional-api.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/use-graph-api.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/use-functional-api.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/persistence.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/add-memory.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/durable-execution.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/interrupts.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/streaming.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/use-time-travel.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/use-subgraphs.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/agentic-rag.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/sql-agent.md"),
    TargetPage("langgraph", "https://docs.langchain.com/oss/python/langgraph/test.md"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/installation.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/quickstart.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/usage/usage.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/usage/custom_models.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/usage/mteb_evaluation.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/pretrained_models.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/training_overview.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/dataset_overview.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/loss_overview.html"),
    TargetPage("sentence_transformers", "https://www.sbert.net/docs/sentence_transformer/training/examples.html"),
)


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return "index"
    cleaned = [re.sub(r"\.(html|md)$", "", part) for part in parts]
    if len(cleaned) >= 2:
        slug_parts = cleaned[-2:]
    else:
        slug_parts = cleaned
    slug = "-".join(slug_parts)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "index"


def pick_content_node(soup: BeautifulSoup, domain: str) -> BeautifulSoup:
    selectors = SITE_SELECTORS[domain]
    candidates: list[tuple[int, BeautifulSoup]] = []
    for selector in selectors:
        for node in soup.select(selector):
            text = " ".join(node.stripped_strings)
            if len(text) >= 400:
                candidates.append((len(text), node))
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return soup.body or soup


def absolutize_links(node: BeautifulSoup, base_url: str) -> None:
    for tag in node.select("[href]"):
        href = tag.get("href")
        if href:
            tag["href"] = urljoin(base_url, href)
    for tag in node.select("[src]"):
        src = tag.get("src")
        if src:
            tag["src"] = urljoin(base_url, src)


def extract_title(soup: BeautifulSoup) -> str:
    heading = soup.find("h1")
    if heading and heading.get_text(strip=True):
        return normalize_title(heading.get_text(" ", strip=True))
    if soup.title and soup.title.string:
        return normalize_title(soup.title.string.strip())
    return "Untitled document"


def normalize_title(title: str) -> str:
    cleaned = title.replace("\uf0c1", " ").replace("ï", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def clean_html_to_markdown(html: str, domain: str, base_url: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup)
    content_node = pick_content_node(soup, domain)
    content = BeautifulSoup(str(content_node), "html.parser")

    for selector in REMOVE_SELECTORS:
        for tag in content.select(selector):
            tag.decompose()

    absolutize_links(content, base_url)
    markdown = html_to_markdown(
        str(content),
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
    )
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    if not markdown.startswith("#"):
        markdown = f"# {title}\n\n{markdown}"
    return title, markdown


def parse_markdown_source(markdown: str, fallback_title: str) -> tuple[str, str]:
    cleaned = markdown.strip()
    cleaned = re.sub(r"\[(?:ï|)\]\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"^> ## Documentation Index.*?(?:\n\s*\n|\Z)", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    title = normalize_title(fallback_title)
    for line in cleaned.splitlines():
        if line.startswith("# "):
            title = normalize_title(line[2:].strip())
            break
    return title, cleaned


def render_frontmatter(source_url: str, title: str, domain: str) -> str:
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return (
        "---\n"
        f"source_url: {source_url}\n"
        f"title: {title}\n"
        f"domain: {domain}\n"
        f"fetched_at: {fetched_at}\n"
        "---\n\n"
    )


def fetch_document(session: requests.Session, target: TargetPage) -> tuple[str, str, str]:
    response = session.get(target.url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    response.raise_for_status()
    content_type = (response.headers.get("content-type") or "").lower()
    if "text/markdown" in content_type or response.url.endswith(".md"):
        title, markdown = parse_markdown_source(response.text, fallback_title=slugify_url(response.url).replace("-", " "))
    else:
        title, markdown = clean_html_to_markdown(response.text, target.domain, response.url)
    return response.url, title, markdown


def write_document(output_path: Path, source_url: str, title: str, domain: str, markdown: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_frontmatter(source_url=source_url, title=title, domain=domain) + markdown.strip() + "\n"
    output_path.write_text(content)


def prune_stale_outputs() -> None:
    expected = {
        TECH_DOCS_DIR / target.domain / f"{slugify_url(target.url)}.md"
        for target in TARGETS
    }
    for domain_dir in TECH_DOCS_DIR.iterdir():
        if not domain_dir.is_dir():
            continue
        for path in domain_dir.glob("*.md"):
            if path not in expected:
                path.unlink()


def main() -> None:
    TECH_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    prune_stale_outputs()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    successes = 0
    failures: list[tuple[str, str]] = []
    for target in TARGETS:
        output_path = TECH_DOCS_DIR / target.domain / f"{slugify_url(target.url)}.md"
        try:
            source_url, title, markdown = fetch_document(session, target)
            write_document(output_path, source_url=source_url, title=title, domain=target.domain, markdown=markdown)
            successes += 1
            print(f"[OK] {target.domain}: {title} -> {output_path.relative_to(PROJECT_ROOT)}", flush=True)
            time.sleep(REQUEST_DELAY_SECONDS)
        except Exception as exc:  # pragma: no cover - validation is end-to-end
            failures.append((target.url, str(exc)))
            print(f"[FAIL] {target.url}: {exc}", flush=True)

    print(f"\nFetched {successes} documents into {TECH_DOCS_DIR.relative_to(PROJECT_ROOT)}", flush=True)
    if failures:
        print(f"{len(failures)} documents failed:", flush=True)
        for url, error in failures:
            print(f"- {url}: {error}", flush=True)


if __name__ == "__main__":
    main()
