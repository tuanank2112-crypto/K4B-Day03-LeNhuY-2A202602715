# NITRO Cyber Gaming Hub — Data Architecture and Flow

## 1. Current storage

The current v1.0.0 implementation has no database. `src/tools.py` owns three process-local dictionaries:

- `MOCK_PC_DATABASE`: 32 PC records across VIP, PRO_GAMING, STANDARD, and STREAM. Each record includes zone, specs, status, and hourly price; booking adds `booked_by`, `booking_id`, and `duration_hours`.
- `MOCK_MEMBER_DATABASE`: 2 member records (`NET2026` and `NET1001`) with name, tier, balance, and favorite zone.
- `MOCK_CANTEEN_DATABASE`: 8 menu records with category, price, availability, and description.

There are no durable writes. The CLI, web server, and in-process MCP wrapper share these dictionaries only while the same Python process is alive. Restarting the process restores the seed state. `docs/trace_waterfall.json` is a separate trace artifact written by the CLI when a run produces logs; it is not application state.

## 2. Current flow

```text
Web UI / CLI ReAct loop
        ↓
web_server.py endpoints or app.py
        ↓
MCPAcademicServer (local MCP-shaped wrapper)
        ↓
dispatch_tool_call in tools.py
        ↓
in-memory PC/member/canteen dictionaries
```

The five current operations are availability lookup, PC booking, PC release, menu lookup, and canteen ordering. Booking and release mutate PC records directly. The web server reports counts from the same dictionaries through `/api/pcs`; `/api/book` and `/api/cancel` call the execution functions directly; `/api/chat` runs the ReAct loop.

## 3. Planned data architecture (Plan 01, target v1.1.0)

Plan 01 proposes SQLite as the durable source of truth for PCs, members, bookings, and canteen orders, with mock data retained only as seed input. A single domain service is planned to own business rules, while CLI, REST, and MCP remain adapters. The plan requires transactional all-or-nothing multi-seat booking, idempotency for mutations, ownership checks for cancellation, and restart persistence.

FastAPI/Pydantic REST contracts, a standard MCP protocol adapter, and WebSocket/realtime UI updates are also planned. None of those layers exists in the current tracked implementation, so they must not be represented as current storage or flow.
