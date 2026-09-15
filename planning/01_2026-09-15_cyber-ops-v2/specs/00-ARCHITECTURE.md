# 00 — Architecture / Cyber Operations 1.1.0

## 1. Phạm vi và nguồn quyết định

Hợp đồng thiết kế cho MINOR 1.1.0; thực thi sau khi bộ SPEC được duyệt. Nguồn quyết định là [plan §2](../plan.md#2-nhật-ký-quyết-định). Base đã đối chiếu: `eb1022a4f801215a691cfd0b6f5e313274618a6f`.

Mục tiêu: booking và canteen tồn tại qua restart, đặt nhóm nguyên tử, cùng luật nghiệp vụ qua CLI/REST/MCP, web nhận sự kiện đã commit, kiểm thử local lặp lại được. Giữ HTML/CSS/JavaScript hiện tại và năm kịch bản TC01–TC05.

Non-goals: production deploy, thanh toán thật, OAuth/SSO, đa chi nhánh, điều khiển máy trạm, inventory chuyên sâu. Các việc này cần quyết định/hạ tầng riêng; số dư và hoàn tiền trong bản này chỉ là dữ liệu demo và báo giá, không hạch toán tài chính.

## 2. Router bắt buộc

| Thứ tự | File | Sở hữu hợp đồng |
| :--: | :-- | :-- |
| 1 | [00-ARCHITECTURE.md](00-ARCHITECTURE.md) | Boundaries, bất biến, WBS |
| 2 | [01-CONTRACTS.md](01-CONTRACTS.md) | DDL, types, kết quả, lỗi chung |
| 3 | [SPEC-P01-BOOKING-CORE.md](SPEC-P01-BOOKING-CORE.md) | Transaction, seed, booking/cancel/order |
| 4 | [SPEC-P02-API-MCP.md](SPEC-P02-API-MCP.md) | REST, session, MCP protocol, compatibility |
| 5 | [SPEC-P03-WEB-REALTIME.md](SPEC-P03-WEB-REALTIME.md) | WebSocket, UI, trace |
| 6 | [SPEC-P04-QUALITY-MIGRATION.md](SPEC-P04-QUALITY-MIGRATION.md) | Migration, CI, tài liệu, version |
| 7 | [OPERATIONS.md](OPERATIONS.md) | Local rollout, backup, rollback |
| 8 | [TESTING-ACCEPTANCE.md](TESTING-ACCEPTANCE.md) | Ma trận đo và Exit Gates local |

Nếu hai hợp đồng mâu thuẫn, dừng gói bị ảnh hưởng và chuyển architect; CẤM worker tự chọn một nghĩa mới. DDL/types do 01 sở hữu, protocol do P02 sở hữu, event/trace do P03 sở hữu, lệnh vận hành do OPERATIONS sở hữu.

## 3. Module và contract biên

```text
CLI src/app.py ───────────┐
Legacy src/tools.py ──────┤
REST src/web_server.py ───┼─> cyber_ops.service.CyberService ─> repository ─> SQLite
MCP src/mcp_server.py ────┘                              └─> event_outbox
Web HTML/CSS/JS <─ REST + WebSocket <─ cyber_ops.realtime <─ event_outbox
ChatCoordinator ─> provider ─> proposed tools ─> validated CyberService calls
```

| Đường dẫn đích | Trách nhiệm / contract |
| :-- | :-- |
| `src/cyber_ops/models.py` | Pydantic DTO/JSON Schema, `DomainError`, public projections theo 01 |
| `src/cyber_ops/db.py` | `connect(db_path: Path) -> sqlite3.Connection`; bật FK/WAL/busy timeout |
| `src/cyber_ops/repository.py` | SQL tham số hóa; connection và transaction do service sở hữu |
| `src/cyber_ops/service.py` | `CyberService` với chữ ký trong 01 §4; toàn bộ luật booking/cancel/canteen |
| `src/cyber_ops/security.py` | `SessionService`; xác thực, token hash, ownership context |
| `src/cyber_ops/migrations/001_initial.sql` | DDL nguyên văn 01 §3; bất biến sau phát hành |
| `src/cyber_ops/seed.py` | Seed cố định từ tracked mock; không chạy mỗi request |
| `src/cyber_ops/realtime.py` | Snapshot có cursor nhất quán + outbox dispatcher theo P03 |
| `src/cyber_ops/trace.py` | Tạo trace bằng allowlist, không serialize raw provider output |
| `src/cyber_ops/chat.py` | `ChatCoordinator.run`; timeout, request ledger, tool key dẫn xuất |
| `src/cyber_ops/manage.py` | Entry point migrate/inspect/backup/restore/member-pin theo OPERATIONS |
| `src/tools.py`, `src/mcp_server.py` | Adapter tương thích; không còn dictionary runtime |
| `src/web_server.py` | `create_app(settings: Settings) -> FastAPI`; giữ `start_server(port=8080)` |
| `web/app.js`, `web/index.html`, `web/style.css` | UI hiện tại, thêm session/reconnect/errors, render an toàn |

Không tạo framework frontend mới. SQLite dùng thư viện chuẩn `sqlite3`; FastAPI/Pydantic và MCP Python SDK được khóa dependency thực tế ở WP01/WP04 sau khi resolver xác minh, không suy đoán số phiên bản package.

## 4. Bất biến BẮT BUỘC / CẤM

1. BẮT BUỘC SQLite là nguồn chân lý duy nhất. Seed chỉ dùng trên database mới; adapters không được ghi SQL hay sửa dict giữ trạng thái.
2. BẮT BUỘC mỗi transaction mutation dùng `BEGIN IMMEDIATE`; unique index ở 01 bảo vệ một ghế đang giữ trên một máy, kể cả hai process CLI/API.
3. BẮT BUỘC multi-seat cùng booking, cùng transaction, cùng event; lỗi bất kỳ ghế nào rollback toàn bộ. CẤM `PARTIAL_SUCCESS` và retry tự đổi danh sách máy.
4. BẮT BUỘC booking, seats, idempotency result và outbox commit cùng nhau. Không giữ transaction khi chờ LLM, network hoặc WebSocket.
5. BẮT BUỘC member session hợp lệ cho mutation nghiệp vụ; `customer_id` trong lời nhắc không cấp quyền. Auth/session lifecycle có contract riêng để tạo được session đầu tiên.
6. BẮT BUỘC operation key chống lặp; cùng member/operation/key khác payload là conflict. Lỗi input/ownership không thay đổi dữ liệu nghiệp vụ.
7. BẮT BUỘC mặc định bind `127.0.0.1:8080`, CORS/Origin/Host allowlist; WebSocket chỉ phát dữ liệu công khai của máy.
8. BẮT BUỘC trace là action summary/tool/redacted args/result/latency/correlation ID. CẤM raw chain-of-thought, token, PIN, header xác thực và raw prompt trong runtime telemetry.
9. BẮT BUỘC runtime version 1.1.0 thống nhất; protocol MCP riêng là `2025-06-18`. Không trộn với brain template version.
10. BẮT BUỘC test bắt buộc fail=0, skip=0; không dùng live LLM/network làm điều kiện thành công cho CI.

### Vùng cấm và lý do

| CẤM | Lý do |
| :-- | :-- |
| Khóa bằng `threading.Lock` thay database constraint | Không bảo vệ nhiều process/restart |
| Tự giải phóng booking khi hết duration | v1.1.0 là giữ chỗ demo, chưa có check-in/billing lifecycle; chỉ cancel giải phóng |
| Sửa `src/ai_levels/level3_native_mcp_agent.py` | Tracked file khai báo reference-only, không nằm luồng runtime |
| Đọc fixture trace học thuật làm live telemetry | Chứa nội dung thought và không thể hiện lần chạy hiện tại |
| Tự nhận production-ready hoặc deploy remote | Đ10 chỉ duyệt local |
| Xóa/bù dữ liệu đã ghi sau backup khi rollback ngầm | Cần export và quyết định rõ về dữ liệu mới |

## 5. WBS: phụ thuộc và ước lượng riêng

| WP | Kết quả | Tầng | Phụ thuộc |
| :-- | :-- | :--: | :-- |
| WP00 | Bộ 8 SPEC được đo và duyệt | 🔴 | Không |
| WP01 | Models, DDL, seed, migration | 🟠 | WP00 |
| WP02 | Service transactional + idempotency domain | 🟠 | WP01 |
| WP03 | REST, session, chat request ledger | 🟠 | WP02 |
| WP04 | MCP stdio và alias nội bộ | 🟠 | WP02 |
| WP05 | UI, WebSocket, safe trace | 🟠 | WP03 |
| WP06 | Unit/contract/integration/concurrency/browser + CI | 🟠 | WP01–WP05 |
| WP07 | Docs/runbook/brain/version | 🟢 | WP06 |
| WP08 | Thẩm định độc lập security/race/rollback | 🔴 | WP06–WP07 |

| WP | Ước lượng ngày công |
| :-- | --: |
| WP00 | 0,5 |
| WP01 | 1,5 |
| WP02 | 1,5 |
| WP03 | 1,5 |
| WP04 | 1,0 |
| WP05 | 1,5 |
| WP06 | 2,0 |
| WP07 | 0,5 |
| WP08 | 0,5 |
| Tổng | 10,5 |

Đường găng: WP00 → WP01 → WP02 → WP03 → WP05 → WP06 → WP07 → WP08 (9,5 ngày công tuần tự theo ước lượng; WP04 có thể song song). Không coi ước lượng là SLA hoặc bằng chứng đã hoàn thành.

## 6. Error taxonomy và hành vi caller

| Nhóm lỗi | Owner | Caller bắt buộc |
| :-- | :-- | :-- |
| Validation/auth/ownership | DTO + SessionService + CyberService | Dừng mutation, hiển thị mã lỗi; không retry khác actor |
| Máy bận/idempotency conflict | CyberService | Refresh dữ liệu; chỉ dùng key mới khi người dùng tạo ý định mới |
| SQLite busy/network disconnect | Repository/transport | Retry có giới hạn với cùng key; không suy đoán transaction thất bại |
| Protocol MCP | MCP adapter | Sửa message/lifecycle; không diễn giải thành nghiệp vụ thành công |
| Contract/schema/migration mismatch | Boot/quality gate | Dừng khởi động hoặc rollout; chuyển architect |

## 7. Số đo thật và nghiệm thu

Baseline đo từ tracked HEAD: 32 máy = VIP 8 + PRO_GAMING 6 + STANDARD 16 + STREAM 2; 2 member, 8 menu item; trạng thái 13 AVAILABLE, 14 OCCUPIED, 3 BOOKED, 2 MAINTENANCE. Bước 0 exit 0. Dictionary runtime, lớp `ThreadingHTTPServer`, 5 tool và polling web 15.000 ms đã đối chiếu mã nguồn.

Hiện chưa thi công 1.1.0; CẤM đánh dấu cổng runtime xanh từ tài liệu này. Gate local: 8/8 SPEC, 20 request một máy = 1 success/19 conflict, 0 partial write, 5/5 compatibility, restart giữ booking; output máy và checksum theo [TESTING-ACCEPTANCE §3–5](TESTING-ACCEPTANCE.md#3-ma-trận-kiểm-thử-bắt-buộc-local).
