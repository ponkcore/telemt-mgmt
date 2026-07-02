#!/usr/bin/env python3
"""
validate_docs.py — universal docs-as-code validator for the omo pipeline.

Stack-agnostic and dependency-free (Python 3.8+ stdlib only). It validates ONLY the
markdown/frontmatter layer, which is identical across every project regardless of the
code language. Copy it into any project unchanged.

Checks
------
  1. Frontmatter: required fields present per artefact type; status from the allowed set.
  2. id ↔ filename: frontmatter `id` matches the filename prefix (PRD-003-foo.md → PRD-003).
  3. version: PRD/ARCH are semver X.Y.Z.
  4. Version-pinned references: any reference to ANOTHER artefact in prose (outside code
     fences/inline code) must be `ID@X.Y.Z`. A bare `PRD-001` is rejected.
  5. Dangling references: every referenced PRD/ARCH/ADR/TKT/ROADMAP id must exist.
  6. depends_on: every TKT dependency must reference an existing ticket.
  7. DAG: the ticket depends_on graph must be acyclic.

Usage
-----
  python3 scripts/validate_docs.py [--docs DIR] [--quiet]
Exit code 0 = clean, 1 = errors found.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

# ── artefact taxonomy ───────────────────────────────────────────────────────
# prefix -> (subdir glob hint, required frontmatter fields, allowed statuses)
ARTEFACTS = {
    "PRD":      ("prd",          ["id", "type", "status", "version"], {"draft", "in_review", "approved", "superseded"}),
    "ROADMAP":  ("roadmap",      ["id", "type", "status"],            {"draft", "in_review", "approved", "superseded"}),
    "ARCH":     ("architecture", ["id", "type", "status", "version"], {"draft", "in_review", "approved", "superseded"}),
    "ADR":      ("architecture/adr", ["id", "type", "status"],        {"proposed", "accepted", "superseded", "rejected"}),
    "TKT":      ("tickets",      ["id", "type", "status"],            {"draft", "ready", "in_progress", "in_review", "blocked", "done"}),
    "RV-CODE":  ("reviews",      ["id", "type", "status"],            {"in_review", "done"}),
    "RV-ARCH":  ("reviews",      ["id", "type", "status"],            {"in_review", "done"}),
    "BACKLOG":  ("backlog",      ["id", "type", "status"],            {"open", "in_progress", "done", "wontfix"}),
    "Q":        ("questions",    ["id", "type", "status"],            {"open", "answered", "closed"}),
}
# Reference prefixes that must exist somewhere when cited:
EXISTENCE_CHECKED = {"PRD", "ROADMAP", "ARCH", "ADR", "TKT"}

# id token, e.g. PRD-003, RV-CODE-012, Q-TKT-003-01, ADR-001
ID_RE = re.compile(r"\b(PRD|ROADMAP|ARCH|ADR|TKT|RV-CODE|RV-ARCH|BACKLOG|Q-TKT|Q)-\d+(?:-\d+)?\b")
PINNED_SUFFIX_RE = re.compile(r"@\d+\.\d+\.\d+")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def prefix_of(artefact_id: str) -> str:
    for p in ("RV-CODE", "RV-ARCH", "Q-TKT", "PRD", "ROADMAP", "ARCH", "ADR", "TKT", "BACKLOG", "Q"):
        if artefact_id.startswith(p + "-"):
            return p
    return artefact_id.split("-")[0]


# ── tiny YAML-subset frontmatter parser (no deps) ───────────────────────────
def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:])
    data, key = {}, None
    for raw in fm_lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if re.match(r"^\s*-\s+", raw) and key is not None:  # list item
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(raw.strip()[1:].strip().strip("\"'"))
            continue
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            data[key] = []            # likely a block list follows
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            data[key] = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
        else:
            data[key] = val.strip().strip("\"'")
    return data, body


def strip_code(body: str) -> str:
    """Remove fenced blocks and inline code so references inside them are ignored."""
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = re.sub(r"`[^`]*`", "", body)
    return body


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="docs", help="docs directory (default: docs)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    errors, warnings = [], []
    known_ids = set()                  # all artefact ids found
    ticket_deps = {}                   # TKT id -> [dep ids]
    docs_seen = 0

    md_files = []
    for root, _dirs, files in os.walk(args.docs):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            if fn.startswith("TEMPLATE") or fn == "README.md":
                continue
            md_files.append(os.path.join(root, fn))

    parsed = []
    for path in sorted(md_files):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        fm, body = parse_frontmatter(text)
        base = os.path.basename(path)
        m = ID_RE.match(base)          # filename should start with an id token
        file_id = m.group(0) if m else None
        if not fm or "id" not in fm:
            # only flag files that look like artefacts (id-prefixed names)
            if file_id:
                errors.append(f"{path}: missing or unparseable frontmatter (no `id`).")
            continue
        docs_seen += 1
        aid = fm["id"]
        known_ids.add(aid)
        parsed.append((path, fm, body, file_id, aid))

    for path, fm, body, file_id, aid in parsed:
        pref = prefix_of(aid)
        spec = ARTEFACTS.get(pref)
        if not spec:
            warnings.append(f"{path}: unknown artefact prefix for id `{aid}` — skipping deep checks.")
            continue
        _hint, required, allowed_status = spec

        for field in required:
            if field not in fm or fm[field] in ("", [], None):
                errors.append(f"{path}: frontmatter missing required field `{field}`.")
        if "status" in fm and fm["status"] not in allowed_status:
            errors.append(f"{path}: status `{fm['status']}` not in allowed {sorted(allowed_status)} for {pref}.")
        if "version" in required and "version" in fm and not SEMVER_RE.match(str(fm["version"])):
            errors.append(f"{path}: version `{fm['version']}` is not semver X.Y.Z.")
        if file_id and file_id != aid:
            errors.append(f"{path}: frontmatter id `{aid}` ≠ filename id `{file_id}`.")
        if not file_id:
            errors.append(f"{path}: filename does not start with the artefact id (expected `{aid}-...md`).")

        if pref == "TKT":
            deps = fm.get("depends_on", [])
            if isinstance(deps, str):
                deps = [deps]
            ticket_deps[aid] = [re.sub(r"@.*$", "", d) for d in deps]

        # reference checks (prose only)
        prose = strip_code(body)
        # also scan select frontmatter ref fields
        for rf in ("prd_ref", "arch_ref", "depends_on", "adrs", "tickets", "target_arch", "ticket_ref"):
            v = fm.get(rf)
            if isinstance(v, list):
                prose += "\n" + "\n".join(str(x) for x in v)
            elif isinstance(v, str):
                prose += "\n" + v

        for mref in ID_RE.finditer(prose):
            ref = mref.group(0)
            if ref == aid:
                continue                                   # self-mention is fine
            tail = prose[mref.end(): mref.end() + 8]
            rpref = prefix_of(ref)
            if rpref in EXISTENCE_CHECKED and not PINNED_SUFFIX_RE.match(tail):
                errors.append(f"{path}: reference `{ref}` is not version-pinned (use `{ref}@X.Y.Z`).")

    # dangling reference + dependency existence + DAG
    for path, fm, body, file_id, aid in parsed:
        prose = strip_code(body)
        for mref in ID_RE.finditer(prose):
            ref = mref.group(0)
            if prefix_of(ref) in EXISTENCE_CHECKED and ref not in known_ids and ref != aid:
                errors.append(f"{path}: dangling reference `{ref}` — no such artefact in {args.docs}/.")

    for tkt, deps in ticket_deps.items():
        for d in deps:
            if d and d not in known_ids:
                errors.append(f"{tkt}: depends_on `{d}` does not exist.")

    # cycle detection (Kahn)
    cyc = detect_cycle(ticket_deps)
    if cyc:
        errors.append(f"depends_on graph has a cycle: {' -> '.join(cyc)}")

    # report
    if not args.quiet:
        for w in warnings:
            print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print(f"\nvalidate_docs: FAILED — {len(errors)} error(s) across {docs_seen} document(s).")
        return 1
    print(f"validate_docs: OK — {docs_seen} document(s) validated, 0 errors.")
    return 0


def detect_cycle(deps: dict):
    color = {}  # 0=unvisited,1=in-stack,2=done

    def dfs(node, stack):
        color[node] = 1
        stack.append(node)
        for nxt in deps.get(node, []):
            if nxt not in deps:        # dependency not a ticket node; existence handled elsewhere
                continue
            if color.get(nxt, 0) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if color.get(nxt, 0) == 0:
                r = dfs(nxt, stack)
                if r:
                    return r
        stack.pop()
        color[node] = 2
        return None

    for n in deps:
        if color.get(n, 0) == 0:
            r = dfs(n, [])
            if r:
                return r
    return None


if __name__ == "__main__":
    sys.exit(main())
