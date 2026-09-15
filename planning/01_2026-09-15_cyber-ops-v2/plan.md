# Kế hoạch #01 — Cyber Operations v2

## 1. Metadata

| Trường | Giá trị |
| :-- | :-- |
| ID | 01 |
| Thư mục bất biến | planning/01_2026-09-15_cyber-ops-v2 |
| Trạng thái | 📐 ĐANG LẬP KẾ HOẠCH — chờ duyệt bộ SPEC |
| Loại phát hành dự kiến | MINOR |
| Phiên bản hiện tại | 1.0.0 |
| Phiên bản mục tiêu | 1.1.0 |
| Ngày tạo | 2026-09-15 23:11:54 +07:00 |
| Base SHA | eb1022a4f801215a691cfd0b6f5e313274618a6f |
| Chủ trì | Super Orchestrator |
| Mục tiêu một câu | Biến demo Cyber Gaming thành nền tảng vận hành cục bộ có booking bền vững, API/MCP chuẩn hóa, giao diện realtime an toàn và bằng chứng kiểm thử lặp lại được. |

## 2. Nhật ký quyết định

### 2.1. Bản tổng hợp đã được người dùng duyệt

- Mục tiêu: nâng cấp toàn bộ nền tảng theo đề xuất đã thảo luận, ưu tiên độ đúng của booking trước tính năng trình diễn.
- Phạm vi theo gói: booking persistence; REST và MCP adapters; bảo mật và realtime web; test, CI, migration, tài liệu và SemVer.
- Không làm trong hồ sơ này: production deploy, thanh toán thật, OAuth/SSO, đa chi nhánh, điều khiển máy trạm và quản lý kho chuyên sâu. Lý do: cần quyết định chiến lược, tài khoản hoặc hạ tầng riêng.
- Số đo cam kết: dữ liệu sống qua restart; một máy chỉ có một booking hoạt động; input sai không đổi dữ liệu; MCP và REST cùng dùng một domain service; toàn bộ test bắt buộc xanh, không skip.

### 2.2. Quyết định đang hiệu lực

| ID | Mốc giờ | Quyết định | Cách đo đúng/sai | Chỗ có thể lật và chi phí |
| :-- | :-- | :-- | :-- | :-- |
| Đ01 | 2026-09-15 23:11:54 +07:00 | Hồ sơ là MINOR v1.1.0, giữ tương thích luồng lab hiện tại. | CLI, REST và UI cũ vẫn chạy các kịch bản TC01–TC05; version đích là 1.1.0. | Có thể tách thành nhiều PATCH; chi phí là migration và contract phải lặp lại. |
| Đ02 | 2026-09-15 23:11:54 +07:00 | SQLite là nguồn chân lý cho máy, hội viên, booking và đơn canteen; dữ liệu mock chỉ làm seed. | Restart process không làm mất booking; test database tạm chạy độc lập. | Có thể thay PostgreSQL khi đa máy chủ; chi phí đổi driver, migration và vận hành. |
| Đ03 | 2026-09-15 23:11:54 +07:00 | Một domain service duy nhất sở hữu luật nghiệp vụ; CLI, REST và MCP chỉ là adapters. | Không adapter nào sửa trực tiếp database; contract test cho cùng input cho kết quả nghiệp vụ tương đương. | Có thể tách service khi tăng tải; chi phí phân tán transaction và observability. |
| Đ04 | 2026-09-15 23:11:54 +07:00 | Multi-seat booking mặc định all-or-nothing; trạng thái PARTIAL_SUCCESS bị cấm trong v1.1.0. | Một máy không hợp lệ làm toàn transaction rollback; số booking mới bằng 0. | Có thể mở partial booking bằng API version mới; chi phí UX và hoàn tiền phức tạp. |
| Đ05 | 2026-09-15 23:11:54 +07:00 | REST dùng FastAPI/Pydantic; web giữ HTML/CSS/JS hiện tại và nhận cập nhật qua WebSocket. | OpenAPI validate input/output; UI đổi trạng thái không cần reload. | Có thể giữ polling; chi phí thấp nhưng tăng độ trễ và request. |
| Đ06 | 2026-09-15 23:11:54 +07:00 | MCP dùng protocol chuẩn với tools/list, tools/call, request ID, structuredContent và lỗi phân loại; giữ alias tương thích một phiên bản. | MCP client/inspector liệt kê và gọi đủ 5 tool; response khớp schema. | Có thể chỉ giữ adapter mô phỏng cho lab; chi phí là không chứng minh được tương thích MCP thật. |
| Đ07 | 2026-09-15 23:11:54 +07:00 | Mutation cần member session nội bộ và idempotency key; external OAuth chưa thuộc phạm vi. | Khách khác không hủy booking; gửi lại cùng key không tạo bản ghi thứ hai. | Có thể bỏ auth ở demo mode; chi phí là phải cô lập rõ mode và không được bind public. |
| Đ08 | 2026-09-15 23:11:54 +07:00 | Trace công khai chỉ chứa action summary, tool, input đã che, output, latency và correlation ID; cấm phát raw chain-of-thought. | API/UI trace không có trường thought thô hoặc secret; test redaction xanh. | Có thể giữ trace học thuật trong fixture tĩnh; chi phí thấp nếu tách khỏi runtime. |
| Đ09 | 2026-09-15 23:11:54 +07:00 | CI và test là cổng phát hành; không chấp nhận skip ở ma trận bắt buộc. | Test unit, contract, integration, concurrency và browser smoke đều exit 0; skip = 0. | Có thể tách browser test khỏi PR; chi phí là lỗi UI phát hiện muộn. |
| Đ10 | 2026-09-15 23:11:54 +07:00 | Rollout chỉ ở local trong hồ sơ này; production/server là kế hoạch độc lập. | Mọi Exit Gate của hồ sơ mang nhãn local; không có lệnh deploy hoặc secret production. | Mở production cần quyết định hạ tầng và tài khoản; chi phí một hồ sơ vận hành riêng. |

### 2.3. Quyết định bị thay thế

| Quyết định cũ | Thay bằng | Lý do |
| :-- | :-- | :-- |
| Dùng dictionary toàn cục làm nguồn dữ liệu runtime. | Đ02 — SQLite là nguồn chân lý. | Dictionary mất dữ liệu khi restart và không bảo vệ tranh chấp ghi. |
| Multi-booking cho phép thành công một phần nhưng trả SUCCESS. | Đ04 — transaction all-or-nothing. | Tránh trạng thái khó giải thích và chi phí hoàn tiền ngoài ý muốn. |
| Phản hồi tự nhận là JSON-RPC/MCP dù chưa có request ID và lifecycle. | Đ06 — adapter MCP đúng protocol. | Contract hiện tại chỉ là mô phỏng nội bộ. |
| Phục vụ API bằng ThreadingHTTPServer bind 0.0.0.0 và CORS *. | Đ05/Đ07 — FastAPI, cấu hình bind/CORS và session nội bộ. | Cần validation, lỗi nhất quán và ranh giới truy cập rõ. |
| Công khai trường thought trong runtime trace. | Đ08 — action summary và redaction. | Giảm rò rỉ dữ liệu và tách bằng chứng học thuật khỏi telemetry vận hành. |

## 3. Router SPEC

Đọc theo thứ tự từ trên xuống:

| Thứ tự | Tệp | Hợp đồng |
| :--: | :-- | :-- |
| 1 | specs/00-ARCHITECTURE.md | Mục tiêu, non-goals, bất biến, boundaries và thứ tự triển khai |
| 2 | specs/01-CONTRACTS.md | Schema, types, API/MCP contracts, error taxonomy |
| 3 | specs/SPEC-P01-BOOKING-CORE.md | Persistence, transaction, booking/cancel/canteen |
| 4 | specs/SPEC-P02-API-MCP.md | REST, auth nội bộ, idempotency và MCP adapters |
| 5 | specs/SPEC-P03-WEB-REALTIME.md | UI state, WebSocket, DOM safety và trace |
| 6 | specs/SPEC-P04-QUALITY-MIGRATION.md | Migration, test, CI, compatibility và docs |
| 7 | specs/OPERATIONS.md | Trình tự local rollout, backup, rollback và runbook |
| 8 | specs/TESTING-ACCEPTANCE.md | Ma trận test, bằng chứng và Exit Gates |

## 4. Work Packages và phân tầng

| WP | Gói việc | Tầng | Chặn bởi | Ước lượng |
| :-- | :-- | :--: | :-- | :-- |
| WP00 | Hoàn thiện và duyệt bộ SPEC | 🔴 | Không | 0,5 ngày |
| WP01 | Domain models, SQLite schema, seed và migration | 🟠 | WP00 | 1,5 ngày |
| WP02 | Transactional booking, cancel và canteen services | 🟠 | WP01 | 1,5 ngày |
| WP03 | REST API, validation, session và idempotency | 🟠 | WP02 | 1,5 ngày |
| WP04 | MCP adapter chuẩn và compatibility alias | 🟠 | WP02 | 1 ngày |
| WP05 | Realtime UI, DOM safety và trace redaction | 🟠 | WP03 | 1,5 ngày |
| WP06 | Unit, contract, integration, concurrency và browser tests | 🟠 | WP01–WP05 | 2 ngày |
| WP07 | Runbook, tài liệu module, brain sync và SemVer | 🟢 | WP06 | 0,5 ngày |
| WP08 | Thẩm định đối kháng security, race và rollback | 🔴 | WP06–WP07 | 0,5 ngày |

Đường găng dự kiến: WP00 → WP01 → WP02 → WP03 → WP05 → WP06 → WP07 → WP08.

## 5. Checklist thực thi

### Lập kế hoạch

- [x] Chốt mục tiêu, phạm vi, non-goals và số đo cam kết.
- [x] Tạo hồ sơ kế hoạch theo Path Invariant.
- [ ] Architect tạo đủ bộ SPEC.
- [ ] Super Orchestrator đo cấu trúc và contract bắt buộc.
- [ ] Đồng bộ brain4agent cho trạng thái kế hoạch active.

### Thi công

- [ ] WP01 — persistence và migration.
- [ ] WP02 — domain services transactional.
- [ ] WP03 — REST/session/idempotency.
- [ ] WP04 — MCP protocol adapter.
- [ ] WP05 — realtime UI và trace an toàn.
- [ ] WP06 — test suite và CI.
- [ ] WP07 — docs, brain sync và SemVer 1.1.0.
- [ ] WP08 — thẩm định đối kháng độc lập.

### Đóng hồ sơ

- [ ] Mọi handoff có report cùng đuôi và evidence được trỏ.
- [ ] Không report nào còn trạng thái chờ hoặc yêu cầu sửa ở dòng cuối.
- [ ] Mọi Exit Gate local chuyển ✅.
- [ ] Người duyệt ghi phán quyết cuối và chuyển trạng thái hồ sơ thành ✅ ĐÃ HOÀN THÀNH.

## 6. Exit Gates theo môi trường

| Gate | Môi trường | Trạng thái | Bằng chứng bắt buộc |
| :-- | :-- | :--: | :-- |
| G00 | local | ⬜ | Bộ SPEC đủ 8 tệp, không có placeholder, mọi router link tồn tại |
| G01 | local | ⬜ | Migration tạo đúng 32 máy, 2 hội viên và 8 món seed |
| G02 | local | ⬜ | Restart process vẫn đọc được booking đã commit |
| G03 | local | ⬜ | 20 request đồng thời cùng một máy: đúng 1 success, 19 conflict |
| G04 | local | ⬜ | Multi-seat có một máy lỗi: rollback toàn bộ, 0 booking mới |
| G05 | local | ⬜ | duration, quantity, held_minutes và ID sai: lỗi phân loại, 0 mutation |
| G06 | local | ⬜ | Gửi lại cùng idempotency key: cùng kết quả, không thêm record |
| G07 | local | ⬜ | REST contract/OpenAPI tests xanh; auth và ownership tests xanh |
| G08 | local | ⬜ | MCP client liệt kê/gọi đủ 5 tool; structured output khớp schema |
| G09 | local | ⬜ | UI nhận trạng thái realtime; payload HTML không thực thi script |
| G10 | local | ⬜ | Runtime trace không có raw thought hoặc secret; có correlation ID |
| G11 | local | ⬜ | Toàn bộ test bắt buộc exit 0, fail 0, skip 0 |
| G12 | local | ⬜ | Backup → migrate → rollback được chứng minh bằng checksum/count |
| G13 | local | ⬜ | CLI và TC01–TC05 giữ hành vi tương thích đã công bố |
| G14 | local | ⬜ | Ma trận tài liệu và version 1.1.0 đồng bộ đầy đủ |

## 7. Chỉ số quản trị hồ sơ

| Chỉ số | Giá trị hiện tại |
| :-- | :--: |
| Quyết định bị thay thế sau khi lập | 0 |
| Câu hỏi mở của worker do SPEC/handoff thiếu | 0 |
| Vòng sửa do lỗi chữ/kỳ vọng của orchestrator | 0 |
| Lỗi 🔴 lọt qua auditor tới người | 0 |
| Chi phí ghế orchestrator | Chưa đo |
