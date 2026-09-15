# NITRO Cyber Gaming Hub — Project Index

This is the central router for the current repository. Treat tracked source code as the source of truth. The active upgrade is documented in `planning/01_2026-09-15_cyber-ops-v2/`; its SQLite, domain-service, FastAPI, standard MCP, and realtime items are planned and not current behavior.

## 1. Documentation and planning router

| Need | Read | Notes |
| --- | --- | --- |
| Startup rules and current kernel | [`memory-distill.txt`](memory-distill.txt) | Current stack and invariants. |
| Latest session and machine state | [`memory/hot/today.md`](memory/hot/today.md), [`memory/hot/state.json`](memory/hot/state.json) | Hot memory; JSON must remain valid. |
| Product overview | [`project-intro.md`](project-intro.md) | Current versus planned boundary. |
| Storage and state flow | [`-data-architecture.md`](-data-architecture.md) | In-memory current state; SQLite planned. |
| Roadmap and active plan | [`roadmap.md`](roadmap.md), [`planning/`](../planning/) | Plan 01 active; WP00 independent audit pending. |
| Plan dossier guard | [`../tools/brain_dossier_check.py`](../tools/brain_dossier_check.py) | Enforces project-local planning/dispatch/ready/close invariants derived from hub HANDOFF_PROTOCOL §11–§14. |
| Version and decisions | [`changelog.md`](changelog.md) | Unreleased/Planning entries only for 1.1.0. |
| Technical learning materials | [`docs/CODELAB.md`](../docs/CODELAB.md), [`docs/trace_eval.md`](../docs/trace_eval.md) | Existing lab and evaluation artifacts. |
| Technical gotchas | [`-known-gotchas.md`](-known-gotchas.md) | Includes planning/dossier anti-regression notes. |

## 2. Source map

```text
project-root/
├── README.md
├── config/
├── src/
├── web/
├── docs/
├── tools/
│   └── brain_dossier_check.py         # project-local dossier guard; hub protocol remains authoritative
├── planning/
│   └── 01_2026-09-15_cyber-ops-v2/
│       ├── plan.md
│       ├── specs/
│       └── handoffs/                   # reports/evidence appear only from real worker/auditor runs
└── brain4agent/
```

## 3. Entry points and current flow

- CLI baseline/demo: `python src/app.py`; full configured suite: `python src/app.py --all`; interactive agent: `python src/app.py --interactive`.
- Web server: `python src/web_server.py [port]`, default `8080`, serving `web/` and binding `0.0.0.0`.
- Web GET endpoints: `/api/pcs` returns the in-memory PC map and counts; `/api/traces` reads `docs/trace_waterfall.json` when present.
- Web POST endpoints: `/api/book`, `/api/cancel`, `/api/chat`.
- Current state flow: UI/API or ReAct agent -> `MCPAcademicServer` -> `dispatch_tool_call` -> mock dictionaries. Mutations are process-local.

## 4. Current NITRO inventory

- Seed inventory: 32 PCs across VIP, PRO_GAMING, STANDARD, and STREAM; 2 member records; 8 canteen menu records.
- Tool names: `check_available_pcs`, `book_gaming_pc`, `cancel_or_release_pc`, `get_canteen_menu`, `order_canteen_item`.
- The MCP layer is a local simulation with a server class and tool list/call wrapper; it is not yet a production protocol transport.

## 5. Active plan boundary

Plan 01 proposes durable SQLite state, a shared domain service for CLI/REST/MCP, FastAPI/Pydantic REST, an interoperable MCP adapter, realtime updates, and expanded quality gates. These remain planned. Before WP01, H01 must be independently audited and G00 approved with real `.txt` evidence; never infer implementation readiness from SPEC presence alone.
