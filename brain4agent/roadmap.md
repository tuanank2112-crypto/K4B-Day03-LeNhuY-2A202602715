# Roadmap and Active Tasks

## Active plan

`planning/01_2026-09-15_cyber-ops-v2/` is the active MINOR upgrade plan. Current version is `1.0.0`; target version is `1.1.0`. The target is planning metadata only and is not a released version.

### Milestone checklist

- [x] Record the current NITRO baseline: Python + vanilla web, ReAct loop, local MCP simulation, five tools, and in-memory seed data.
- [x] Record inventory baseline: 32 PCs, 2 members, and 8 canteen items.
- [x] Mark current versus planned architecture in project intro and data architecture.
- [x] Register Plan 01 as active in hot state and roadmap.
- [ ] Complete and approve the full Plan 01 SPEC package.
- [ ] WP01-WP02: implement SQLite persistence, migration, and transactional domain services.
- [ ] WP03-WP04: implement FastAPI REST/session/idempotency and standard MCP adapter.
- [ ] WP05: implement realtime web updates and trace redaction.
- [ ] WP06: add unit, contract, integration, concurrency, and browser acceptance evidence.
- [ ] WP07-WP08: update module docs, runbook, SemVer 1.1.0, and independent security/race/rollback review.
- [ ] Close Plan 01 only after all local Exit Gates and evidence are complete.

## Planned direction

- Durable SQLite state with seed migrations.
- One domain service shared by CLI, REST, and MCP adapters.
- FastAPI/Pydantic REST contracts and local member session/idempotency rules.
- Standard MCP lifecycle and structured tool responses while retaining a compatibility alias.
- WebSocket/realtime UI state and redacted operational traces.

## Idea Vault

- [ ] Consider PostgreSQL only after the single-process SQLite design needs a multi-server deployment.
- [ ] Consider production OAuth/SSO, payments, multi-branch operations, machine control, and deep inventory as separate future decisions; they are outside Plan 01.

## Done

- [x] Initial repository and brain4agent governance scaffold (v1.0.0).
- [x] NITRO Cyber Gaming Hub demo baseline: five tools, ReAct flow, MCP-shaped wrapper, vanilla web UI, and mock inventory.
