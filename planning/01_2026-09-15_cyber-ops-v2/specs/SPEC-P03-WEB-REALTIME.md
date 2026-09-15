# P03 — Web Realtime and Safe Trace

## 1. Phạm vi và contract UI

WP05 sửa `web/app.js`, `web/index.html`, `web/style.css`; bổ sung `src/cyber_ops/realtime.py`, `trace.py` và wiring trong web_server. Giữ bố cục sơ đồ32 máy, filter khu, chọn nhóm, booking/manage modal, chat drawer, trace viewer; không đưa React hay build chain mới vào ứng dụng.

```text
AppState = {machines: Map<PcId,MachineView>, selectedPcIds:Set<PcId>, myBookings:BookingResult[],
            memberId:string|null, connection:'connecting'|'online'|'offline', cursor:number,
            pendingOperation:{key:string,payload:object,operation:string}|null}
applySnapshot(message: SnapshotMessage): void
applyMachineEvent(message: MachineEvent): void
renderMachines(state: AppState): void
submitMutation(operation: 'book'|'cancel'|'order'|'chat', payload: object, key: string): Promise<object>
appendChatMessage(sender: 'user'|'ai', plainText: string): void
renderTraceEvents(events: TraceEvent[]): void
```

API auth/session theo P02. Bỏ CURRENT_CUSTOMER_ID hardcoded làm nguồn quyền; lấy memberId từ GET session. Chưa login vẫn xem snapshot GET pcs, nhưng nút mutation bị khóa với thông báo đăng nhập. Không dựa vào cookie khả dụng trong JavaScript; cookie HttpOnly được trình duyệt gửi. Có login form member/PIN và logout; PIN không lưu history/DOM sau submit.

Khi mở form mutation tạo `crypto.randomUUID()` key, giữ nguyên key và normalized payload tới khi có kết quả xác định. Bấm đôi chỉ1 request đang pending. Network failure giữ form/key, cho “Thử lại” cùng key; sửa lựa chọn tạo ý định mới/key mới sau khi bỏ pending cũ một cách tường minh. 409 conflict refresh snapshot và thông báo máy xung đột, không tự giữ một phần hay thay máy. Cancel cùng quy tắc key.

## 2. WebSocket / outbox contract

`GET /api/v1/events` upgrade WebSocket, cookie session hợp lệ và Origin exact allowlist bắt buộc. Sai auth/Origin từ chối trước accept (401/403 nếu ASGI hỗ trợ denial response, fallback close1008); không token query. Tối đa4 connection/member và32 toàn process; quá giới hạn từ chối429 hoặc close1013. App không nhận mutation qua socket.

```text
SnapshotMessage = {type:'snapshot',cursor:number,server_time_ms:number,
                   data:{stats:Stats,pcs:Record<PcId,MachineView>}}
MachineEvent = {type:'machines.changed',seq:number,event_id:UUID,created_at_ms:number,
                correlation_id:UUID,data:{pcs:MachineView[]}}
Heartbeat = {type:'heartbeat',cursor:number,server_time_ms:number}
ClientMessage = {type:'pong'}
```

Server snapshot đọc machine_state và `COALESCE(MAX(event_outbox.seq),0)` trong cùng read transaction. Gửi snapshot trước, sau đó đọc outbox `WHERE seq > cursor ORDER BY seq LIMIT 100` mỗi250ms. Không snapshot ngoài transaction rồi lấy cursor sau vì sẽ mất event giữa hai lần đọc. Snapshot không chứa owner; UI dùng GET bookings riêng sau login/snapshot/event máy để hiển thị máy của mình.

`machines.changed` payload được ghi trong transaction nghiệp vụ là `{pcs:[MachineView...]}` với trạng thái sau mutation; một booking nhóm chỉ1 event chứa cả nhóm. `event_id`, created_at_ms/correlation_id nằm cột outbox, không sinh lại lúc phát. Chỉ event committed mới visible qua connection đọc. Không có flag “published” toàn cục: mỗi client có cursor riêng. Event `food_order.created` không gửi lên socket công khai, nhưng dispatcher vẫn tăng internal cursor khi đi qua seq đó.

Dispatcher poll database qua worker thread, có queue tối đa256 message/client; send deadline5s, queue đầy đóng1013. Không giữ transaction khi send. Heartbeat15s chứa cursor đã xử lý; client pong trong30s, thiếu thì close1001. Kiểm session expired/revoked ít nhất mỗi15s và trước gửi machine event; đóng1008 nếu mất quyền. Inbound body >4096 byte →close1009; type lạ/mutation request →close1008.

Reconnect exponential1s/2s/4s/8s/16s tối đa30s, jitter0–20%; pause khi offline browser, resume theo online event. Mỗi reconnect bắt đầu bằng snapshot mới (không nhận cursor từ URL, không cần replay từ browser). Sau snapshot chỉ apply seq lớn hơn local cursor; duplicate/old event bỏ qua. Seq không nhất thiết liên tiếp vì có event riêng tư bị lọc; không coi gap là mất dữ liệu. Snapshot mới thay toàn bộ machine map atomically rồi reconcile selection.

Outbox không prune trong1.1.0. Restart web/MCP/CLI không mất committed state/event. Khi một client offline, browser hiển thị “Mất kết nối” và khóa mutation đến khi snapshot mới nhận; không giả label MCP ONLINE. Khi cần refresh manual dùng GET pcs, không đặt lại interval polling15s hiện tại.

## 3. DOM/XSS và hành vi tương tác

BẮT BUỘC user input, provider text, menu/specs, error.message và JSON trace được gắn bằng `textContent`/`createTextNode`; không dùng `innerHTML`/`insertAdjacentHTML` chứa chuỗi từ dữ liệu. `formatMarkdown` runtime bỏ regex-to-HTML hiện tại; v1.1.0 render plain text với `white-space:pre-wrap`. Không thêm Markdown library chỉ để giữ styling demo.

Static template HTML còn được phép nếu không nội suy untrusted data. Chuyển inline onclick/onerror sang addEventListener để áp CSP: `default-src 'self'; script-src 'self'; connect-src 'self' ws://127.0.0.1:8080 ws://localhost:8080; img-src 'self' data:; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`. Port WS cấu hình từ server, không hardcode8080 khi chạy port khác. X-Content-Type-Options:nosniff, Referrer-Policy:no-referrer; external font lỗi dùng font system, không làm test phụ thuộc internet.

Máy chọn bằng button keyboard-focusable có tên gồm ID/status/giá; status có text, không chỉ màu. Modal có role=dialog, aria-modal, focus ban đầu, Escape đóng, trả focus về nút mở. Pending button disabled; lỗi form có role=alert, không chỉ browser alert. Screen 360px và1280px không mất nút chính, sơ đồ có scroll vùng rõ ràng.

## 4. Trace schema và redaction

```text
TraceEvent = {action_summary:string,tool:string|null,
              redacted_args:Record<string,JSONScalar|JSONScalar[]>,
              result:{status:'SUCCESS'|'ERROR',code:string|null,summary:string},
              latency_ms:number,correlation_id:UUID}
build_trace(tool: str | None, validated_args: dict, result: Success | Failure,
            started_ns: int, completed_ns: int, correlation_id: str) -> TraceEvent
```

Đây là allowlist6 trường cấp cao, không lưu raw input/output rồi blacklist. action_summary lấy template do code kiểm soát (“Tra cứu máy”, “Đặt giữ máy”, “Hủy giữ máy”, “Tra cứu thực đơn”, “Đặt món”, “Trả lời khách”); không lấy từ model.thought/reasoning. tool chỉ5 tên trong registry hoặc null. latency_ms đo monotonic_ns thực, ≥0; không Math.random/fallback thời gian giả.

redacted_args chỉ giữ zone/category/pc_id/pc_ids/duration_hours/quantity/held_minutes và customer_id=`[REDACTED]` nếu field có mặt. Không giữ item_name tự do, prompt/history/member name/token/PIN/authorization/cookie/key. result chỉ status/code và summary template, không serialize nguyên provider text/exception/booking row. Trace không chứa raw chain-of-thought ở API, UI, stdout, stderr hay file runtime; không emit field thought/query/arguments/observation.

Trace ring buffer riêng session tối đa100 events; restart xóa buffer và GET traces trả rỗng là behavior công bố. Business persistence không phụ thuộc trace buffer. CLI `save_waterfall_trace(trace_data:list) -> None` giữ hàm nhưng chỉ ghi TraceEvent allowlist sang runtime trace path cấu hình dưới `data/traces/`; không ghi đè `docs/trace_waterfall.json` học thuật. Web không phục vụ docs như static directory và không tự load fixture thought.

Chat final_answer là nội dung trả lời riêng qua API, render text; không sao chép vào trace summary. Header X-Correlation-ID nối request vào log; trace replay có correlation ID ban đầu theo kết quả đã lưu. Copy trace chỉ copy6 field đã redacted. UI label là “Nhật ký thao tác”, không “raw thought/reasoning”.

## 5. Error taxonomy / caller

| Lỗi | UI/dispatcher bắt buộc |
| :-- | :-- |
| HTTP401/WS1008 do session | Xóa member view, giữ máy công khai, yêu cầu login |
| HTTP403 ownership/Origin | Dừng mutation; không fallback ID NET2026 |
| HTTP409 PC_UNAVAILABLE | Refresh snapshot, bỏ selected seat không còn available, thông báo rõ |
| HTTP409 CHAT_INTERRUPTED | Hiển thị trạng thái chưa rõ của chat, tải booking; không gửi lại key mới tự động |
| Network/503 | Pending key giữ nguyên; reconnect/Thử lại hữu hạn |
| WS1013/queue full | Đóng và reconnect từ snapshot, không bỏ event âm thầm |
| JSON/schema event sai | Không apply; đóng socket và reconnect snapshot, ghi summary local |
| HTML payload | Render nguyên văn dạng text, không “sanitize” bằng regex |

## 6. Vùng cấm

CẤM backend pub owner ID/session qua outbox; CẤM coi event nhận hai lần là thêm hai booking; CẤM optimistic BOOKED trước response/committed event; CẤM silent selection substitution; CẤM raw thought trong fixture hiển thị ở runtime; CẤM mở CDN script hoặc unsafe-inline để tránh sửa DOM event handlers. Đây là ranh giới bảo mật, không phải tùy chọn thẩm mỹ.

## 7. Số đo thật / nghiệm thu local

Base web/app.js có671 dòng, dùng polling15.000ms, CURRENT_CUSTOMER_ID=NET2026, appendChatMessage/trace inspector chèn nội dung bằng innerHTML; runtime trace có thought. Số đo này từ tracked HEAD.

Gate local: 2 browser contexts nhận cùng booking event trong≤1000ms, p95 đo trên20 mutation; reconnect sau3 mutation offline khớp snapshot/32 máy; không nhận ghost event sau transaction rollback; 20 XSS payload qua chat/menu/trace/error không gọi dialog/script và text còn đọc được; trace100 event không có secret/field cấm, latency đo thật. Browser tests fail0/skip0, screenshot ở360px/1280px và timing JSON là evidence, chưa phải kết quả đã đạt.
