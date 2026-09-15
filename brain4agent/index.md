# NITRO Cyber Gaming Hub — Project Index

This is the central router for the current repository. Treat tracked source code as the source of truth. The active upgrade is documented in `planning/01_2026-09-15_cyber-ops-v2/`; its SQLite, domain-service, FastAPI, standard MCP, and realtime items are planned and not current behavior.

## 1. Documentation and planning router

| Need | Read | Notes |
| --- | --- | --- |
| Startup rules and current kernel | [`memory-distill.txt`](memory-distill.txt) | Current stack and invariants. |
| Latest session and machine state | [`memory/hot/today.md`](memory/hot/today.md), [`memory/hot/state.json`](memory/hot/state.json) | Hot memory; JSON must remain valid. |
| Product overview | [`project-intro.md`](project-intro.md) | Current versus planned boundary. |
| Storage and state flow | [`-data-architecture.md`](-data-architecture.md) | In-memory current state; SQLite planned. |
| Roadmap and active plan | [`roadmap.md`](roadmap.md), [`planning/`](../planning/) | Plan 01 is active; target 1.1.0. |
| Version and decisions | [`changelog.md`](changelog.md) | Unreleased/Planning entries only for 1.1.0. |
| Technical learning materials | [`docs/CODELAB.md`](../docs/CODELAB.md), [`docs/trace_eval.md`](../docs/trace_eval.md) | Existing lab and evaluation artifacts. No module doc changed in this sync. |
| Technical gotchas | [`-known-gotchas.md`](-known-gotchas.md) | Read when diagnosing an unusual failure. |

## 2. Source map

```text
project-root/
├── README.md                         # Python setup and lab overview
├── config/
│   ├── test_cases.json               # Five active NITRO test prompts
│   └── test_cases.example.json       # Generic example fixture
├── src/
│   ├── app.py                         # ReAct loop, provider orchestration, trace writing
│   ├── mcp_server.py                  # In-process MCP-shaped server and tool dispatch
│   ├── tools.py                       # Five schemas, mock data, execution functions
│   ├── providers.py                   # Mock, Gemini, and OpenAI provider adapters
│   ├── prompts.py                     # Baseline and ReAct prompts
│   ├── web_server.py                  # stdlib HTTP server and /api endpoints
│   └── ai_levels/                     # Reference implementation material
├── web/
│   ├── index.html                     # NITRO Cyber Gaming Hub page
│   ├── app.js                         # Vanilla UI, booking, chat, trace inspector
│   ├── style.css                      # Visual styling
│   └── assets/                        # Cyber arena image asset
├── docs/                              # Existing codelab, evaluation, and trace artifacts
├── planning/                          # Spec-first upgrade plans
└── brain4agent/                       # Project memory and governance records
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

Plan 01 proposes durable SQLite state, a shared domain service for CLI/REST/MCP, FastAPI/Pydantic REST, an interoperable MCP adapter, realtime updates, and expanded quality gates. These must be described as planned until source code and acceptance evidence land.
