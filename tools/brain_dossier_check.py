#!/usr/bin/env python3
"""Project-local guardrail for brain4agent planning dossiers.

The external brain engine remains authoritative. This checker only makes the
HANDOFF_PROTOCOL §11-§14 invariants executable in this repository so a plan
cannot be called "ready" without its on-disk dossier.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

H_RE = re.compile(r"^H(\d{2})_(thi-cong|tham-dinh)_([A-Za-z0-9][A-Za-z0-9.-]*)\.md$")
R_RE = re.compile(r"^R(\d{2})_(thi-cong|tham-dinh)_([A-Za-z0-9][A-Za-z0-9.-]*)\.md$")
EVIDENCE_REF_RE = re.compile(r"(?:\.\./)?evidence/([A-Za-z0-9][A-Za-z0-9.-]*)/([^/\s)`\]]+\.[^/\s)`\]]+)")
SPEC_REF_RE = re.compile(r"(specs/[A-Za-z0-9._-]+\.md)")
DRAFT_RE = re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:TODO|TBD|FIXME|PLACEHOLDER)\s*[:\-]")


def fail(errors: list[str], code: str, message: str) -> None:
    errors.append(f"{code}:{message}")


def last_nonempty(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir", type=Path)
    ap.add_argument("--phase", choices=("planning", "dispatch", "ready", "close"), default="planning")
    ns = ap.parse_args()
    d = ns.plan_dir
    errors: list[str] = []

    plan_path = d / "plan.md"
    specs_dir = d / "specs"
    if not plan_path.is_file():
        fail(errors, "PLAN-MISSING", "plan.md")
        plan = ""
    else:
        plan = plan_path.read_text(encoding="utf-8")
    if not specs_dir.is_dir():
        fail(errors, "SPECS-MISSING", "specs/")

    # Brain source invariants that are easy to regress during plan normalization.
    for token, code in [
        ("Quyết định bị thay thế", "PLAN-SUPERSEDED"),
        ("Mốc giờ", "PLAN-TIMESTAMP"),
        ("Chặn bởi", "PLAN-DEPENDENCY"),
        ("Ước lượng", "PLAN-ESTIMATE"),
    ]:
        if token not in plan:
            fail(errors, code, token)

    spec_refs = sorted(set(SPEC_REF_RE.findall(plan)))
    required = {"specs/00-ARCHITECTURE.md", "specs/01-CONTRACTS.md", "specs/OPERATIONS.md", "specs/TESTING-ACCEPTANCE.md"}
    if not required.issubset(spec_refs):
        fail(errors, "SPEC-ROUTER", "missing required router entries")
    if not any(Path(x).name.startswith("SPEC-P") for x in spec_refs):
        fail(errors, "SPEC-FEATURE", "no SPEC-Pxx router entry")
    for ref in spec_refs:
        if not (d / ref).is_file():
            fail(errors, "SPEC-BROKEN", ref)

    scan_files = [plan_path] + [d / ref for ref in spec_refs if (d / ref).is_file()]
    for p in scan_files:
        if p.is_file() and DRAFT_RE.search(p.read_text(encoding="utf-8")):
            fail(errors, "DRAFT-MARKER", str(p))

    # Evidence under dossier must be .txt, even when its content is JSON/JUnit XML.
    for p in scan_files:
        if not p.is_file():
            continue
        txt = p.read_text(encoding="utf-8")
        for _, name in EVIDENCE_REF_RE.findall(txt):
            clean = name.rstrip(".,;:")
            if "*" not in clean and not clean.endswith(".txt"):
                fail(errors, "EVIDENCE-EXT", f"{p}:{clean}")
    evidence_dir = d / "evidence"
    if evidence_dir.exists():
        for p in evidence_dir.rglob("*"):
            if p.is_file() and p.suffix != ".txt":
                fail(errors, "EVIDENCE-FILE-EXT", str(p))

    handoff_dir = d / "handoffs"
    report_dir = d / "reports"
    handoffs = sorted(handoff_dir.glob("H*.md")) if handoff_dir.is_dir() else []
    reports = sorted(report_dir.glob("R*.md")) if report_dir.is_dir() else []

    if ns.phase in {"dispatch", "ready", "close"} and not handoffs:
        fail(errors, "HANDOFF-MISSING", "no handoff on disk")

    numbers: list[int] = []
    for h in handoffs:
        m = H_RE.match(h.name)
        if not m:
            fail(errors, "H-NAME", h.name)
            continue
        numbers.append(int(m.group(1)))
        text = h.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > 80:
            fail(errors, "H-LINES", f"{h.name}:{len(lines)}")
        if len(lines) < 3 or not lines[0].startswith("1. Bạn là worker của repo này."):
            fail(errors, "H-L1", h.name)
        if len(lines) < 3 or not lines[1].startswith("2. Bước 0"):
            fail(errors, "H-L2", h.name)
        if len(lines) < 3 or not lines[2].startswith("3. Đọc theo thứ tự"):
            fail(errors, "H-L3", h.name)
        tail = last_nonempty(text)
        expected_report = "R" + h.name[1:]
        if f"reports/{expected_report}" not in tail or "Evidence:" not in tail or ".txt`" not in tail:
            fail(errors, "H-TAIL", h.name)
    if numbers:
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            fail(errors, "H-SEQUENCE", f"got={numbers} expected={expected}")

    report_map = {p.name: p for p in reports}
    approved_audit = False
    evidence_count = sum(1 for p in evidence_dir.rglob("*.txt")) if evidence_dir.is_dir() else 0

    for h in handoffs:
        expected_report = "R" + h.name[1:]
        r = report_map.get(expected_report)
        if ns.phase in {"ready", "close"} and r is None:
            fail(errors, "R-MISSING", expected_report)
            continue
        if r is None:
            continue
        if not R_RE.match(r.name):
            fail(errors, "R-NAME", r.name)
        text = r.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("Vai: worker (vai-thi-cong)"):
            fail(errors, "R-L1", r.name)
        expected_h_line = f"Handoff: handoffs/{h.name}"
        if len(lines) < 4 or lines[1].strip() != expected_h_line:
            fail(errors, "R-L2", r.name)
        if len(lines) < 4 or not lines[2].startswith("Base: "):
            fail(errors, "R-L3", r.name)
        if len(lines) < 4 or not lines[3].startswith("Head: "):
            fail(errors, "R-L4", r.name)
        tail = last_nonempty(text)
        if ns.phase in {"ready", "close"} and not tail.startswith("✅ DUYỆT"):
            fail(errors, "R-VERDICT", f"{r.name}:{tail}")
        if "_tham-dinh_" in r.name and tail.startswith("✅ DUYỆT"):
            approved_audit = True
        for group, name in EVIDENCE_REF_RE.findall(text):
            clean = name.rstrip(".,;:")
            if "*" in clean:
                continue
            ev = d / "evidence" / group / clean
            if not ev.is_file():
                fail(errors, "EVIDENCE-MISSING", str(ev))

    if ns.phase in {"ready", "close"}:
        if not approved_audit:
            fail(errors, "RED-AUDIT", "no approved independent audit report")
        if evidence_count < 1:
            fail(errors, "EVIDENCE-EMPTY", "no machine evidence .txt")

    status_ready = "sẵn sàng thi công" in plan.lower()
    g00_green = bool(re.search(r"\|\s*G00\s*\|[^\n]*\|\s*✅\s*\|", plan))
    if ns.phase == "planning" and (status_ready or g00_green):
        fail(errors, "PREMATURE-READY", "plan claims ready/G00 green before --phase ready")

    if ns.phase == "close":
        if "✅ ĐÃ HOÀN THÀNH" not in plan:
            fail(errors, "CLOSED-STATUS", "plan not closed")
        for r in reports:
            tail = last_nonempty(r.read_text(encoding="utf-8"))
            if not tail.startswith("✅ DUYỆT"):
                fail(errors, "CLOSED-PENDING", r.name)

    if errors:
        print(f"ok:false phase={ns.phase} errors={len(errors)} codes=" + ",".join(x.split(':',1)[0] for x in errors))
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print(f"ok:true phase={ns.phase} specs={len(spec_refs)} handoffs={len(handoffs)} reports={len(reports)} evidence={evidence_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
