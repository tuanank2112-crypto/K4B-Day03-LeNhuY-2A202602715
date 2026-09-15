# Kế hoạch #01 — Cyber Operations v2

## 1. Metadata

| Trường | Giá trị |
| :-- | :-- |
| ID | 01 |
| Thư mục bất biến | `planning/01_2026-09-15_cyber-ops-v2` |
| Trạng thái | 📐 SPEC ĐÃ DUYỆT — sẵn sàng thi công WP01 |
| Loại phát hành dự kiến | MINOR |
| Phiên bản hiện tại | 1.0.0 |
| Phiên bản mục tiêu | 1.1.0 |
| Ngày tạo | 2026-09-15 23:11:54 +07:00 |
| Base SHA | `eb1022a4f801215a691cfd0b6f5e313274618a6f` |
| Chủ trì | Super Orchestrator |
| Mục tiêu | Nâng demo Cyber Gaming thành nền tảng vận hành local có booking bền vững, API/MCP chuẩn hóa, realtime an toàn và acceptance evidence lặp lại được. |

## 2. Nhật ký quyết định

### 2.1. Phạm vi đã duyệt

- Ưu tiên độ đúng của booking trước tính năng trình diễn.
- Phạm vi: SQLite persistence; domain service; REST + MCP adapters; session/idempotency; realtime web; trace redaction; migration; test/CI; runbook; docs và SemVer.
- Không thuộc Plan 01: production deploy, thanh toán thật, OAuth/SSO, đa chi nhánh, điều khiển máy trạm, inventory chuyên sâu.
- Chỉ công bố `1.1.0` sau khi toàn bộ Exit Gate local đạt.

### 2.2. Quyết định đang hiệu lực

| ID | Quyết định | Cách đo |
| :-- | :-- | :-- |
| Đ01 | Plan 01 là MINOR target `1.1.0`, giữ compatibility của lab. | TC01–TC05 tiếp tục chạy đúng contract. |
| Đ02 | SQLite là nguồn chân lý runtime; mock chỉ dùng làm seed. | Booking sống qua restart; DB test độc lập. |
| Đ03 | Một `CyberService` sở hữu luật nghiệp vụ; CLI/REST/MCP chỉ là adapters. | Adapter không ghi SQL trực tiếp; cùng input cho kết quả nghiệp vụ tương đương. |
| Đ04 | Multi-seat booking là all-or-nothing; cấm `PARTIAL_SUCCESS`. | Một seat lỗi làm rollback toàn transaction. |
| Đ05 | REST dùng FastAPI/Pydantic; UI giữ HTML/CSS/JS và nhận realtime bằng WebSocket. | OpenAPI validate input/output; UI nhận state không cần polling 15s. |
| Đ06 | MCP dùng protocol chuẩn, stdio, `tools/list`, `tools/call`, request ID và `structuredContent`; giữ compatibility alias 1.1.x. | Client MCP thật liệt kê/gọi đủ 5 tool. |
| Đ07 | Mutation bắt buộc member session + idempotency key; OAuth ngoài scope. | Actor khác không hủy booking; replay không tạo bản ghi thứ hai. |
| Đ08 | Runtime trace chỉ lưu action summary/tool/redacted args/result/latency/correlation ID; cấm raw chain-of-thought. | Trace audit không có secret hoặc field reasoning/thought. |
| Đ09 | CI/test là release gate; fail/error/skip/xfail/xpass đều phải bằng 0. | `verify-junit` exit 0. |
| Đ10 | Rollout của Plan 01 chỉ local. | Không có production deploy/secret trong hồ sơ. |
| Đ11 | v1.0 không có persistent DB; Plan 01 không hứa bảo toàn mutation in-memory nếu không có snapshot ngoài tiến trình đã được xác thực. Fresh rollout dùng tracked seed hoặc snapshot legacy hợp lệ. Sau khi 1.1.0 có mutation mới, restore backup cũ là destructive và cần quyết định người. | OPERATIONS R12-A/R12-B chứng minh riêng existing-DB rollback và fresh-migration recovery; không có bước “export live state” giả. |

### 2.3. Quyết định bị thay thế

| Quyết định cũ | Thay bằng | Lý do |
| :-- | :-- | :-- |
| Dictionary toàn cục là runtime source of truth. | Đ02 — SQLite. | Mất dữ liệu khi restart và không bảo vệ multi-process race. |
| Multi-booking có thể thành công một phần. | Đ04 — atomic all-or-nothing. | Tránh trạng thái/hoàn tiền mơ hồ. |
| Wrapper nội bộ tự nhận là MCP/JSON-RPC chuẩn. | Đ06 — MCP protocol adapter thật. | Contract cũ chỉ là mô phỏng. |
| `ThreadingHTTPServer` bind `0.0.0.0` + CORS `*`. | Đ05/Đ07 — FastAPI + local perimeter. | Cần validation và ranh truy cập rõ. |
| Public raw `thought` runtime. | Đ08 — safe trace allowlist. | Giảm rò rỉ reasoning/secret. |
| CLI migration có thể tự chụp live state v1.0 đang chạy. | Đ11 — chỉ import snapshot legacy ngoài tiến trình đã có nguồn gốc. | Process mới không thể đọc dictionary của process cũ. |

## 3. Router SPEC

Đọc đúng thứ tự:

| # | Tệp | Sở hữu contract |
| :--: | :-- | :-- |
| 1 | `specs/00-ARCHITECTURE.md` | Mục tiêu, non-goals, boundaries, invariants |
| 2 | `specs/01-CONTRACTS.md` | DDL, DTO, service signatures, canonical errors |
| 3 | `specs/SPEC-P01-BOOKING-CORE.md` | Persistence, transaction, booking/cancel/canteen |
| 4 | `specs/SPEC-P02-API-MCP.md` | REST, session, idempotency, MCP, compatibility |
| 5 | `specs/SPEC-P03-WEB-REALTIME.md` | UI/WebSocket/outbox/trace safety |
| 6 | `specs/SPEC-P04-QUALITY-MIGRATION.md` | Migration, CI, compatibility, docs/release |
| 7 | `specs/OPERATIONS.md` | Local rollout, backup, rollback, runbook |
| 8 | `specs/TESTING-ACCEPTANCE.md` | Test matrix, evidence, Exit Gates |

Nếu hai SPEC mâu thuẫn, worker dừng gói bị ảnh hưởng và trả lại architect; không tự chọn một nghĩa mới.

## 4. Work Packages và model tier

| WP | Gói | Tầng | Chặn bởi |
| :-- | :-- | :--: | :-- |
| WP00 | Duyệt bộ SPEC | 🔴 | — |
| WP01 | Models, DDL, seed, migration | 🟠 | WP00 |
| WP02 | Transactional booking/cancel/canteen service | 🟠 | WP01 |
| WP03 | REST, session, idempotency, chat ledger | 🟠 | WP02 |
| WP04 | MCP stdio + compatibility alias | 🟠 | WP02 |
| WP05 | Realtime UI + safe trace | 🟠 | WP03 |
| WP06 | Unit/contract/integration/concurrency/browser + CI | 🟠 | WP01–WP05 |
| WP07 | Runbook/docs/brain/version sync | 🟢 | WP06 |
| WP08 | Adversarial audit security/race/rollback | 🔴 | WP06–WP07 |

Đường găng: WP00 → WP01 → WP02 → WP03 → WP05 → WP06 → WP07 → WP08. WP04 có thể chạy song song sau WP02.

## 5. Checklist thực thi

### Lập kế hoạch
- [x] Chốt mục tiêu, phạm vi, non-goals và số đo.
- [x] Tạo package theo Path Invariant.
- [x] Tạo đủ 8 SPEC.
- [x] Audit contract/router ở mức planning.
- [x] Brain hiện ghi Plan 01 active và target 1.1.0.

### Thi công
- [ ] WP01 — persistence/migration.
- [ ] WP02 — transactional domain service.
- [ ] WP03 — REST/session/idempotency/chat.
- [ ] WP04 — MCP protocol adapter.
- [ ] WP05 — realtime UI + safe trace.
- [ ] WP06 — tests + CI + RED/mutant evidence.
- [ ] WP07 — docs/brain/runbook/version sync.
- [ ] WP08 — adversarial audit độc lập.

### Đóng hồ sơ
- [ ] Mỗi handoff có report cùng đuôi và evidence tồn tại.
- [ ] Không report nào còn 🔁/⛔.
- [ ] G00–G14 local đều ✅.
- [ ] Người duyệt ghi sign-off cuối và đổi trạng thái `✅ ĐÃ HOÀN THÀNH`.

## 6. Exit Gates local

| Gate | Trạng thái | Điều kiện bắt buộc |
| :-- | :--: | :-- |
| G00 | ✅ | Bộ SPEC đủ 8 tệp; router resolve; planning không còn contract placeholder. |
| G01 | ⬜ | Fresh migration: 32 machines, 2 members, 8 menu items; schema/integrity/FK đúng. |
| G02 | ⬜ | Booking đã commit vẫn tồn tại sau restart process. |
| G03 | ⬜ | 20 contender cùng một PC: đúng 1 success, 19 `PC_UNAVAILABLE`, 0 `DB_BUSY`. |
| G04 | ⬜ | Multi-seat lỗi bất kỳ seat nào: delta booking/seat/key/outbox = 0. |
| G05 | ⬜ | Input sai/range/type/ID sai: lỗi đúng taxonomy, 0 mutation. |
| G06 | ⬜ | Replay cùng idempotency key không nhân bản; payload khác → conflict. |
| G07 | ⬜ | REST/OpenAPI/auth/ownership/Origin/Host/body-limit tests đạt. |
| G08 | ⬜ | MCP client thật initialize/list/call đủ 5 tool; protocol/business errors tách đúng. |
| G09 | ⬜ | Realtime + reconnect đạt; XSS corpus không thực thi script. |
| G10 | ⬜ | 100 runtime trace events không có secret/raw reasoning; correlation/latency hợp lệ. |
| G11 | ⬜ | Full quality suite exit 0; fail/error/skip/xfail/xpass = 0. |
| G12 | ⬜ | Existing-DB backup/restore và fresh-migration fault recovery đều có evidence. |
| G13 | ⬜ | TC01–TC05 compatibility đạt, TC05 không write. |
| G14 | ⬜ | Docs/link/version matrix đồng bộ 1.1.0; brain template version không đổi. |

G00 chỉ xác nhận planning package hoàn chỉnh; không được dùng G00 để suy ra application 1.1.0 đã thi công.

## 7. Chỉ số quản trị hồ sơ

| Chỉ số | Hiện tại |
| :-- | :--: |
| Quyết định bị thay thế sau khi lập | 1 |
| Vòng sửa planning do audit contract | 1 |
| Câu hỏi mở do SPEC thiếu | 0 |
| Lỗi 🔴 lọt qua auditor tới người | 0 |
| Application version | 1.0.0 |
| Target version | 1.1.0 |
