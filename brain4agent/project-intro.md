# NITRO Cyber Gaming Hub — Project Overview

## 1. Product purpose

NITRO Cyber Gaming Hub is a Vietnamese cyber cafe demo. A customer can inspect PC availability, reserve one or more gaming PCs, release a reservation, browse eight canteen items, and order food or drinks to a seat. The web page also demonstrates a ReAct agent and its tool trace.

## 2. Current implementation (v1.0.0)

- Backend: Python 3.10-3.12. `src/web_server.py` uses `ThreadingHTTPServer` and `SimpleHTTPRequestHandler`; there is no FastAPI application.
- Agent: `src/app.py` performs a ReAct loop. `src/providers.py` supplies Mock Offline, Gemini, and OpenAI adapters. The mock provider is available without an API key.
- MCP: `src/mcp_server.py` exposes a local `MCPAcademicServer` wrapper around five tool schemas and dispatch functions. This is an MCP-shaped simulation, not a deployed MCP transport.
- Frontend: `web/index.html`, `web/style.css`, and `web/app.js` are a vanilla HTML/CSS/JavaScript interface. The browser calls the local HTTP endpoints and renders booking, chat, and trace views.
- Data: `src/tools.py` stores seed records in process-local dictionaries: 32 PCs, 2 members, and 8 canteen items. Booking and release mutate those dictionaries; restarting Python resets the state.

## 3. Planned upgrade (Plan 01, target v1.1.0)

The active plan proposes SQLite as the source of truth, one shared domain service, FastAPI/Pydantic REST contracts, a standard MCP adapter, realtime/WebSocket UI updates, migrations, stronger tests, and an operational runbook. These are planned work only; current code and current version remain v1.0.0.

## 4. Scope boundary

The current demo does not provide durable persistence, multi-process consistency, production authentication, payment processing, machine control, or production deployment. Plan 01 also keeps production rollout, OAuth/SSO, multi-branch operation, payment, direct machine control, and deep inventory management out of scope.
