# Algo-Reel M2 Hardening — Few-Shot Examples + Named Style Reference (Manim)

**Status:** Approved (brainstorming)
**Owner:** Subhajit Dutta
**Date:** 2026-06-07
**Related:** [docs/trd.md](../../trd.md) §5.2, [M2 design](2026-05-19-algo-reel-m2-design.md) §14

---

## 1. Purpose

TRD v0.3 §5.2 marks few-shot prompting **REQUIRED** for Pass-1 script generation:

> "The Pass-1 system prompt MUST carry 1–2 worked examples of a good `VideoScript` JSON for the target renderer, plus a named style reference ('pace and visual style of 3Blue1Brown' for Manim …). Concrete references move structured-output quality measurably more than abstract instructions."

The M2 implementation shipped on v0.2 assumptions and never picked this up: `app/llm/prompts.py` has zero worked examples and no named style reference. This spec closes that gap **for the manim renderer only** — the v1 renderer. ai_image is deferred until its renderer exists (v1.1).

This is "done" when:

- A manim job's Pass-1 prompt includes a named 3Blue1Brown style reference and one worked, schema-valid `VideoScript` JSON example.
- An ai_image job's prompt is unchanged (no manim example leakage, no example of its own yet).
- The worked example is constructed through the real `VideoScript` model, so schema drift breaks the module at import rather than shipping a malformed example.

## 2. Scope

### In scope
- `app/llm/prompts.py`: add a named style reference for manim and one worked `VideoScript` few-shot example, injected per-renderer in `build_user_prompt`.
- One typed few-shot constant built via `VideoScript(...)` and serialized for the prompt.
- Unit tests for prompt assembly (presence/absence per renderer) and example validity.

### Out of scope (explicitly not this round)
- **`VideoScript.style_guide` field** — not selected; schema is unchanged.
- **Pass-1 critic** (script-validation pass) — not selected.
- **Model change** (Haiku → Sonnet 4.6) — not selected.
- **Ops/robustness hardening** (key validation, pricing-table boot check, LLM timeout, SSE reconnect) — not selected.
- **ai_image worked example** — deferred with its renderer (v1.1). ai_image keeps its existing one-line hint only.

## 3. Design

### 3.1 Placement — per-renderer injection (not the system prompt)

The few-shot example and style reference go into `build_user_prompt`'s **manim branch**, extending the existing `_RENDERER_HINTS` pattern. They do **not** go into `SCRIPT_SYSTEM_PROMPT`.

Rationale: `script_agent` is constructed once at import with a *static* `system_prompt` (`app/llm/script_agent.py:42`). A renderer-conditional system prompt would force per-call agent rebuilds or a dynamic-system-prompt decorator — complexity for no benefit. A static system prompt would also ship the manim example to ai_image jobs (wasted tokens + a misleading example). Per-renderer injection keeps the example beside the renderer it demonstrates and costs ai_image nothing. The "few-shot belongs in the system prompt" convention has no measurable effect with current models.

`SCRIPT_SYSTEM_PROMPT` stays general (role, output contract, constraints). Renderer-specific content — including the example — lives in the per-renderer injection.

### 3.2 Worked example as a typed constant

The example is built by constructing the actual model, then serialized for the prompt:

```python
_MANIM_FEWSHOT_SCRIPT = VideoScript(
    title="Why a² + b² = c²",
    renderer=Renderer.MANIM,
    voice="alloy",
    total_duration=60.0,
    scenes=[Scene(index=0, ...), ...],
)
_MANIM_FEWSHOT_JSON = _MANIM_FEWSHOT_SCRIPT.model_dump_json(indent=2)
```

Building through `VideoScript`/`Scene` guarantees the example is schema-valid and keeps it in lockstep with the schema: any future field/constraint change makes the module fail loudly at import instead of silently shipping an invalid few-shot. This directly mitigates M2 spec §13's "`TestModel` is blind to schema mistakes."

**Example content** — a canonical 3B1B-style topic (Pythagorean theorem), 4 scenes, durations summing to 60s, each narration ≤300 chars, diagrammatic `visual_prompt`s:

| idx | duration | narration (abbrev.) | visual_prompt (abbrev.) |
|---|---|---|---|
| 0 | 12 | Introduce a right triangle and name its sides a, b, c. | Right triangle, legs a and b, hypotenuse c, labels fade in. |
| 1 | 16 | Build a square on each of the three sides. | Squares grown outward on each side; areas a², b², c² labeled. |
| 2 | 18 | Show the two small squares' area rearranging to fill the large one. | Animate a²+b² tiles transforming to tile the c² square. |
| 3 | 14 | Conclude with the relation a² + b² = c². | Equation a²+b²=c² writes on; triangle dims to background. |

(Exact narration strings are authored during implementation; the table fixes shape, count, and durations.)

### 3.3 Prompt assembly

`build_user_prompt(renderer=manim)` returns, in order:
1. existing user/renderer/duration/max-scenes lines,
2. existing `_RENDERER_HINTS[MANIM]`,
3. **new** named style reference: *"Match the pacing and visual style of 3Blue1Brown — clean geometric constructions, smooth transforms, one idea per scene."*,
4. **new** `"Here is a well-formed VideoScript for this renderer:\n" + _MANIM_FEWSHOT_JSON`.

`build_user_prompt(renderer=ai_image)` is unchanged.

## 4. Testing

`TestModel` is deterministic and blind to prompt quality, so tests assert prompt *content*, not LLM behavior (consistent with M2 spec §10/§13):

- `build_user_prompt(manim, …)` contains the 3B1B style-reference text **and** the example title `"Why a² + b² = c²"`.
- `build_user_prompt(ai_image, …)` contains **neither** the style reference nor the example.
- `_MANIM_FEWSHOT_SCRIPT` is a valid `VideoScript` with ≥3 scenes and every narration ≤300 chars (guaranteed by construction; one explicit assertion documents intent).
- Manual: `make smoke-llm` on a manim prompt to eyeball the real quality lift (required for any prompt change, M2 spec §13).
- Coverage stays ≥80% on `app/`.

## 5. Risks & trade-offs

- **Token cost.** The example adds ~300–500 input tokens per manim call. Negligible against the `MAX_SCRIPT_COST_USD=0.10` cap; no change to the circuit breaker.
- **Few-shot anchoring.** A worked example can over-anchor the model toward the example's structure (4 scenes, ~15s each). Mitigation: the example targets the mid tier and the system prompt still states the 3–MAX scene range and ±20% duration rule; revisit via `smoke-llm` across the 30/60/180s tiers if anchoring shows up.
- **Single example, not 1–2.** TRD allows 1–2; we ship 1 to limit tokens and anchoring. Adding a second is a trivial follow-up if quality warrants.

## 6. Files touched

- `app/llm/prompts.py` — style reference constant, `_MANIM_FEWSHOT_SCRIPT` + serialized JSON, `build_user_prompt` manim branch.
- `tests/llm/test_prompts.py` — assertions in §4.

No schema migration, no new dependency, no config change, no model change.

## 7. Open questions

None blocking.

## 8. Self-review notes

- No `TBD`/`TODO` placeholders. Example narration strings are intentionally authored at implementation time; shape/count/durations are fixed here.
- Internally consistent: scope (manim-only, prompt-only) matches design, testing, and files-touched. ai_image untouched stated in §1, §2, §3.3, §4.
- Scope is a single small implementation plan; no decomposition needed.
- Naming consistent: `_MANIM_FEWSHOT_SCRIPT`, `_MANIM_FEWSHOT_JSON`, `build_user_prompt`, `_RENDERER_HINTS`, `SCRIPT_SYSTEM_PROMPT`.
