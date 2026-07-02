#!/usr/bin/env python3
"""Interactive model wiring for the pipeline roles.

Asks for a model (and optional reasoning effort) per role and writes it into the
YAML frontmatter of each .opencode/agents/<role>.md. Built-in oh-my-openagent
agents/categories are NOT touched here — those come from your omo system settings
(~/.config/opencode/oh-my-openagent.json).

Run from the project root:

    python3 scripts/set-models.py

Stdlib only. Re-runnable: shows the current value as the default; press Enter to
keep it, type a new value to change it, or type "-" to clear a role's override
(it then falls back to opencode's default model).

Enforced rule: executor family != reviewer family. Also warns when
architect-consult / architecture-reviewer likely share a family with their
counterpart (separation of perspectives).
"""
from __future__ import annotations

import os
import re
import sys

# role file -> (label, hint, default reasoningEffort suggestion)
ROLES = [
    ("mentor.md",                "mentor (local primary, navigator/debugger)",       None),
    ("executor.md",              "executor (writes code)",                           None),
    ("reviewer.md",              "reviewer (audits each PR)",                         "high"),
    ("architect-consult.md",     "architect-consult (in-flight ArchSpec patches)",   "high"),
    ("architecture-reviewer.md", "architecture-reviewer (audits ArchSpec vs PRD)",   "high"),
]

# heuristic model-family tokens (lineage, not provider)
FAMILY_TOKENS = [
    "claude", "gpt", "gemini", "llama", "qwen", "glm", "deepseek", "mistral",
    "grok", "command", "kimi", "phi", "yi", "o1", "o3", "o4", "sonnet", "opus",
    "haiku", "gemma", "nova", "jamba",
]

AGENTS_DIR = os.path.join(".opencode", "agents")


def family_of(model: str) -> str:
    """Best-effort model family token from a 'provider/model' string."""
    if not model:
        return ""
    tail = model.split("/")[-1].lower()
    for tok in FAMILY_TOKENS:
        if tok in tail:
            # collapse claude variants (sonnet/opus/haiku) into 'claude'
            if tok in ("sonnet", "opus", "haiku"):
                return "claude"
            if tok in ("o1", "o3", "o4", "gpt"):
                return "gpt"
            return tok
    return tail  # fall back to the raw tail so identical models still clash


def split_frontmatter(text: str):
    """Return (pre, fm_lines, post) where fm_lines is the YAML between the first
    two '---' fences. Raises if no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[0], lines[1:i], lines[i:]
    raise ValueError("unterminated frontmatter")


def current_model(fm_lines):
    for ln in fm_lines:
        m = re.match(r"\s*model:\s*(\S.*)$", ln)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def write_role(path: str, model: str | None, effort: str | None):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    head, fm, tail = split_frontmatter(text)

    cleaned = []
    for ln in fm:
        s = ln.strip()
        if re.match(r"#?\s*model:\s*", s):
            continue
        if re.match(r"#?\s*reasoningEffort:\s*", s):
            continue
        if s.startswith("# TODO: set model"):
            continue
        cleaned.append(ln)

    insert = []
    if model:
        insert.append(f'model: {model}')
        if effort:
            insert.append(f'reasoningEffort: {effort}')

    # place the model line right after `mode:` if present, else after `description:`
    out = []
    placed = False
    for ln in cleaned:
        out.append(ln)
        if not placed and re.match(r"\s*mode:\s*", ln):
            out.extend(insert)
            placed = True
    if not placed:
        # after description (which may span — just put at top of fm)
        out = insert + cleaned

    new_text = "\n".join([head] + out + tail) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)


def ask(prompt: str, default: str | None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        return default or ""
    if val == "":
        return default or ""
    return val


def main() -> int:
    if not os.path.isdir(AGENTS_DIR):
        print(f"error: {AGENTS_DIR}/ not found — run this from the project root.", file=sys.stderr)
        return 2

    print("Model wiring for pipeline roles (built-in omo models come from your")
    print("system config and are left untouched). Format: provider/model, e.g.")
    print("  anthropic/claude-sonnet-4-5   openai/gpt-5   google/gemini-2.5-pro")
    print('Press Enter to keep current, "-" to clear a role.\n')

    chosen: dict[str, str | None] = {}
    for fname, label, eff_sugg in ROLES:
        path = os.path.join(AGENTS_DIR, fname)
        if not os.path.isfile(path):
            print(f"  (skip {fname} — file missing)")
            continue
        _, fm, _ = split_frontmatter(open(path, encoding="utf-8").read())
        cur = current_model(fm)
        val = ask(f"{label}\n  model", cur)
        if val == "-":
            chosen[fname] = None
            write_role(path, None, None)
            print("  -> cleared (falls back to opencode default)\n")
            continue
        if not val:
            chosen[fname] = cur
            print("  -> unchanged\n")
            continue
        effort = None
        if eff_sugg is not None:
            effort = ask("  reasoningEffort (blank = none)", eff_sugg) or None
            if effort == "-":
                effort = None
        chosen[fname] = val
        write_role(path, val, effort)
        print(f"  -> {val}{' / effort=' + effort if effort else ''}\n")

    # validate the hard rule + warn on soft rules
    exe = chosen.get("executor.md")
    rev = chosen.get("reviewer.md")
    ac = chosen.get("architect-consult.md")
    ar = chosen.get("architecture-reviewer.md")

    print("─" * 60)
    problems = []
    if exe and rev and family_of(exe) == family_of(rev):
        problems.append(
            f"HARD RULE VIOLATION: executor and reviewer share family "
            f"'{family_of(exe)}'. Pick different model families (separation of "
            f"perspectives). Re-run and change one of them."
        )
    if ar and ac and family_of(ar) == family_of(ac):
        print(
            "  note: architecture-reviewer shares a family with architect-consult; "
            "fine, but ideally distinct."
        )
    if ar:
        print(
            "  reminder: architecture-reviewer should be a DIFFERENT family than "
            "your (external) Architect model. Pick that Architect accordingly when "
            "you paste docs/prompts/architect.md."
        )

    if problems:
        for p in problems:
            print("  ✗ " + p, file=sys.stderr)
        print("\nModels written, but fix the violation above.", file=sys.stderr)
        return 1

    print("  ✓ executor/reviewer families differ." if exe and rev else "")
    print("Done. Models written to .opencode/agents/*.md frontmatter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
