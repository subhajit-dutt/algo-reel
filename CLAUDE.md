# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Info
- Project Name: algo-reel
- Project Description: A tool that turns a text prompt into a short (≤3 min) illustrative video. Mostly used for tutorial videos. See TRD for more details. Frontend and Backend stay in the same project. Frontend is built with Next.js (CSR), this will generate static pages that will be served from FastAPI, and Backend is built with FastAPI + LLM + Postgres + PydenticAI.

## Coding standard

1. Use Python + PydenticAI + LLM best practices everywhere and define proper types.
2. [Important] Must follow Single Responsibility and Open/Closed Principles and DRY.
3. [Important] Make sure to avoid any duplicate logic or repeated code. If any minor refactor needed to reuse existing
   methods / functionalities, suggest those.
4. [CRITICAL] When doing any refactor, make sure all the references are updated top to bottom. Verify it again after all
   changes. Keep the code simple to understand and maintain and easy to read. No complex error handling, no
   unnecessary fallbacks. No backwards compatibility.
5. [Important] Use Claude skills, plugins, and mcps efficiently
6. If there is any proven prod grade library for any solution, suggest and prefer using that instead of reinventing the
   wheel or writing from scratch.
7. Catch errors or negative cases early, Avoid nested conditions, try to flatten them for max readability. see the below example for good and bad patterns.
8. Always challenge my solution if that is not scalable or industry standard
9. For Postgres tables, use serial autoincrement type for an id primary key.
10. When writing new api or updating existing api, update the api docs in docs→apis

## Subagent / agent model policy

Never spawn a subagent (Agent / Task tool) or invoke an agent-type hook on Haiku. Use Opus or Sonnet only — pass the
`model` parameter explicitly when spawning if needed. The project also enforces this via
`availableModels: ["opus", "sonnet"]` in `.claude/settings.json`, but the rule applies even where that allowlist is not
consulted (e.g. hardcoded `model:` in agent frontmatter or hooks).

### Bad pattern

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    active: bool
    premium: bool


def get_discount(user: User | None) -> int:
    if user:
        if user.active:
            if user.premium:
                return 20
    return 0
```

### Good pattern

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    active: bool
    premium: bool


def get_discount(user: User | None) -> int:
    if user is None:
        return 0
    if not user.active:
        return 0
    if not user.premium:
        return 0

    return 20
```



