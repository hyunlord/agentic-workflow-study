---
source_url: https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool
title: Code execution tool
domain: anthropic
fetched_at: 2026-03-15T09:27:49+00:00
---

# Code execution tool

Claude can analyze data, create visualizations, perform complex calculations, run system commands, create and edit files, and process uploaded files directly within the API conversation. The code execution tool allows Claude to run Bash commands and manipulate files, including writing code, in a secure, sandboxed environment.

**Code execution is free when used with web search or web fetch.** When `web_search_20260209` or `web_fetch_20260209` is included in your request, there are no additional charges for code execution tool calls beyond the standard input and output token costs. Standard code execution charges apply when these tools are not included.

Code execution is a core primitive for building high-performance agents. It enables dynamic filtering in web search and web fetch tools, allowing Claude to process results before they reach the context window—improving accuracy while reducing token consumption.

Reach out through the [feedback form](https://forms.gle/LTAU6Xn2puCJMi1n6) to share your feedback on this feature.

This feature is **not** eligible for [Zero Data Retention (ZDR)](https://platform.claude.com/docs/en/build-with-claude/zero-data-retention). Data is retained according to the feature's standard retention policy.

## Model compatibility

The code execution tool is available on the following models:

| Model | Tool Version |
| --- | --- |
| Claude Opus 4.6 (`claude-opus-4-6`) | `code_execution_20250825` |

Was this page helpful?
