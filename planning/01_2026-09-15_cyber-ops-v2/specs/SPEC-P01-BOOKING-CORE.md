# P01 — Persistence and Booking Core

## 1. Hợp đồng phạm vi

WP01/WP02 triển khai `src/cyber_ops/{models,db,repository,service,seed,security}.py` và migration 001 theo [01 §1–4](01-CONTRACTS.md). `src/tools.py` trở thành adapter tại P02; CẤM thêm SQL vào adapter. Không sửa UI/provider trong gói này.

```text
Repository.transaction(mode: Literal["IMMEDIATE"]) -> ContextManager[sqlite3.Connection]
Repository.read_snapshot() -> ContextManager[sqlite3.Connection]
seed_database(connection: sqlite3.Connection, now_ms: int) -> SeedReport
SeedReport(machines: int, members: int, menu_items: int, bookings: int, seats: int)
```

Connection riêng cho mỗi transaction; không chia sẻ mutable cursor qua thread. `isolation_level=None`, bắt đầu/kết thúc explicit. Exception bất kỳ trước COMMIT phải ROLLBACK; dispose connection bằng context manager. I/O sync chạy trong worker thread khi được gọi từ ASGI.

## 2. Seed và dữ liệu legacy

BẮT BUỘC trích seed một lần từ dictionary tracked ở base `eb1022a4f801215a691cfd0b6f5e313274618a6f`; seed nằm trong module, không import dictionary runtime. Giữ tên/specs/giá của cả 32 máy, 2 member, 8 món. UUID5 namespace `uuid.NAMESPACE_URL` với chuỗi `cyber:seed:booking:{pc_id}` và `cyber:seed:menu:{name}` cho row seed; không hash theo thứ tự dict.

| Dữ liệu nguồn | Biến đổi bắt buộc |
| :-- | :-- |
| AVAILABLE 13 / OCCUPIED 14 / MAINTENANCE 2 | machine.base_status giữ nguyên |
| BOOKED: VIP-03, PRO-05, STD-13, owner NET1001 | base_status AVAILABLE; tạo 3 booking ACTIVE, mỗi booking 1 seat, duration 2 theo fallback legacy |
| Seed booking thiếu timestamp | Dùng cùng `now_ms` của migration, đánh dấu nguồn qua deterministic UUID5; không bịa lịch sử trước import |
| Seed member | Giữ name/tier/balance/favorite_zone; PIN chưa provision (`NULL`) |
| Seed menu | AVAILABLE 8; FOOD 4, DRINK 4, SNACK 0 |

Seed report bắt buộc `{machines:32,members:2,menu_items:8,bookings:3,seats:3}`. Không tạo outbox cho seed: subscriber nhận snapshot đầy đủ khi kết nối. Cấm `INSERT OR REPLACE` ghi đè dữ liệu trên boot. Migrate lần hai không tăng count và không đổi UUID/timestamp/checksum.

Không có DB v1.0 để nâng tại base. Dictionary của v1.0 là state process-local và không durable; Plan 01 **không được tuyên bố tự động phục hồi mutation chưa có snapshot**. Migration mặc định dùng tracked seed. Chỉ khi người vận hành đã có snapshot legacy ngoài tiến trình, đúng schema P04 và pass validation thì mới được import bằng `legacy_json`. CẤM thêm endpoint/IPC mới chỉ để “cứu” live in-memory state trong Plan 01; nếu cần khả năng đó phải mở kế hoạch riêng. Không tự nhận đã phục hồi những giao dịch trước đây chưa được persist.

## 3. Transaction book / cancel

### 3.1. Book

`CyberService.book(BookCommand, RequestContext)` theo 01 §4:

1. Validate DTO và canonicalize pc_ids trước transaction; duplicate sau normalize trả VALIDATION_ERROR.
2. `BEGIN IMMEDIATE`; re-check member session, sau đó đọc idempotency `(member_id,'book',key)`.
3. Có COMPLETED cùng payload hash: trả response_json đã lưu, không thêm booking/seat/event. Khác hash: IDEMPOTENCY_CONFLICT. Không có key: tiếp tục.
4. SELECT tất cả machine/active seats bằng query tham số hóa. ID không tồn tại được ưu tiên PC_NOT_FOUND, sau đó PC_UNAVAILABLE cho base_status khác AVAILABLE hoặc active seat; `details.pc_ids` chỉ chứa requested IDs lỗi.
5. INSERT một booking ACTIVE, N seats với giá snapshot, một idempotency COMPLETED, một outbox `machines.changed` chứa N machine projections BOOKED. Tạo tất cả IDs bằng UUID4; timestamp dùng cùng clock sample.
6. COMMIT, rồi trả Success. Không publish WebSocket trước commit; dispatcher tự đọc outbox sau đó.

`sqlite3.IntegrityError` từ uq_active_machine → PC_UNAVAILABLE và rollback; không đổi mọi IntegrityError thành máy bận (FK/check khác là INTERNAL_ERROR). `OperationalError` busy/locked quá 5000ms → DB_BUSY. Một transaction không chờ LLM. Không tự retry một phần danh sách máy.

### 3.2. Cancel một seat

`CyberService.cancel(CancelCommand, RequestContext)` giải phóng đúng một máy, kể cả trong booking nhóm. Kiểm tra session và idempotency trước; tìm active seat theo pc_id, kiểm owner theo booking.member_id. Máy không tồn tại → PC_NOT_FOUND; máy có nhưng không active seat → BOOKING_NOT_FOUND; owner khác → FORBIDDEN, không trả owner ID.

Phí demo dùng integer: `initial_cost = seat.price_per_hour * booking.duration_hours`; `deducted_fee = min(initial_cost, seat.price_per_hour * held_minutes // 60)`; `refund_amount = initial_cost - deducted_fee`. Lưu held_minutes, deducted_fee, refund_amount, refund_code và released_at_ms. Nếu hết active seats, header CANCELLED + closed_at_ms; còn seat thì header ACTIVE. COMMIT seat/header/idempotency/outbox trong cùng transaction.

`held_minutes` mặc định 30 giữ contract demo; caller được khai báo 0–1440 cho ước tính, không phải bằng chứng thời gian dùng máy. Không chuyển số dư hoặc trả tiền thật. `counter_notice` giữ ý nghĩa đến quầy để xử lý khoản ước tính. Thay đổi sang billing theo đồng hồ server cần kế hoạch riêng.

Cancel lặp cùng key trả cùng refund_code. Key mới sau đã release trả BOOKING_NOT_FOUND, không tạo khoản hoàn thứ hai. Đặt lại máy vừa hủy tạo booking UUID mới.

## 4. Canteen và read

`get_canteen_menu(category)` trả menu rỗng là SUCCESS, total_items=0. `check_available_pcs(zone)` trả canonical SUCCESS rỗng, compatibility ánh xạ NOT_FOUND theo P02. Không thay đổi dữ liệu khi read.

Resolve tên món bằng NFC + casefold + strip. Ưu tiên exact match; sau đó tìm mọi tên có chứa chuỗi input. Đúng 1 ứng viên thì nhận; 0 → ITEM_NOT_FOUND, >1 → AMBIGUOUS_ITEM và `details.candidates` danh sách tên. CẤM fallback chọn món đầu tiên vì cùng có chữ “mì”. `Sting dâu` khớp duy nhất `Sting dâu / vàng` để giữ demo.

`CyberService.order(OrderCommand, RequestContext)` dùng IMMEDIATE + session + idempotency như book. Món phải AVAILABLE. `pc_id=None` nghĩa nhận tại quầy; legacy `TẠI QUẦY` normalize thành None. Nếu có pc_id, bắt buộc active seat của chính principal tại thời điểm đặt; không có seat → BOOKING_NOT_FOUND, owner khác → FORBIDDEN. Lưu snapshot tên/giá, quantity, total trong food_order + key + event cùng transaction. Không tính stock hoặc trừ member.balance.

`food_order.created` outbox payload chỉ `{order_id,created_at_ms}`; dispatcher công khai không phát event này (P03). Response riêng cho owner chứa chi tiết. Order không bị hủy khi booking được release sau đó.

## 5. Idempotency chính xác

- Key scope là `(member_id, operation, request_key)`, độc lập session: login lại vẫn replay được kết quả của chính member.
- Hash payload bao gồm DTO đã normalize: book list sorted + duration; cancel pc_id + held_minutes; order normalized item_name + pc_id + quantity. Không hash giá lookup có thể đổi.
- Replay chạy sau auth và trước kiểm availability/ownership hiện trạng; không lặp mutation chỉ vì máy nay đã bận.
- Lỗi input, auth, không tìm thấy, conflict và transaction rollback không lưu completed record; request với key đó có thể thực hiện sau khi điều kiện được giải quyết.
- Nếu COMMIT thành công nhưng response mất, caller gửi lại cùng key. Nếu lỗi COMMIT không biết chắc, đóng connection và đọc key trên connection mới trước khi kết luận; tuyệt đối không tự tạo key mới.
- `PENDING` chỉ dùng cho chat orchestration tại P02; book/cancel/order insert COMPLETED cùng transaction, không để pending xuyên crash.
- Không TTL/prune idempotency trong 1.1.0. Token hết hạn không xóa kết quả nghiệp vụ.

## 6. Luật BẮT BUỘC / CẤM và vùng cấm

BẮT BUỘC đọc giá/owner/status trong transaction, không dựa vào snapshot UI. BẮT BUỘC persist booking-seat relationship và released seats để audit lịch sử. BẮT BUỘC foreign key trên mọi connection, bao gồm CLI/test.

CẤM dùng machine.booked_by làm nguồn owner thứ hai; CẤM unlock bằng sửa dictionary; CẤM mock runtime fallback khi DB lỗi (che giấu mất dữ liệu); CẤM retry 409 sang máy khác; CẤM auto-release theo duration vì chưa có lifecycle check-in. CẤM hứa bảo toàn mutation in-memory v1.0 khi không có snapshot legacy nguồn. Thay đổi schema/fee semantics ngoài các công thức trên phải quay lại architect.

## 7. Error taxonomy / caller

| Lỗi | Transaction | Caller |
| :-- | :-- | :-- |
| VALIDATION_ERROR | Chưa BEGIN | Sửa đúng field; không đổi key tự động |
| UNAUTHENTICATED / FORBIDDEN | Rollback | Login lại hoặc dừng theo quyền |
| PC_NOT_FOUND / PC_UNAVAILABLE | Rollback toàn nhóm | Refresh, chọn một ý định mới |
| BOOKING_NOT_FOUND / ITEM_NOT_FOUND / AMBIGUOUS_ITEM / ITEM_UNAVAILABLE | Rollback | Xem booking/menu rồi chọn lại |
| IDEMPOTENCY_CONFLICT | Không mutate | Khôi phục payload cũ |
| DB_BUSY | Rollback hoặc xác minh key khi commit chưa rõ | Retry cùng key tối đa 2 lần, delay 250ms rồi 750ms |
| IntegrityError khác uq_active_machine / I/O error | Rollback, INTERNAL_ERROR | Giữ correlation ID, không che bằng SUCCESS |

## 8. Số đo thật và cổng local

Baseline đã chạy source tracked trong process riêng: `[VIP-02,VIP-999]` trả SUCCESS và `VIP-02=BOOKED`; duration=-1 trả SUCCESS/total_cost=-18000. Cổng sửa bắt buộc đo lại cùng input: error, delta booking/seat/key/outbox = 0.

Sau thi công: 20 đồng thời trên VIP-08 → success=1/conflict=19/busy=0; restart process giữ cùng booking_id và outbox seq; fault injection sau seat thứ nhất và trước COMMIT đều để delta=0; cancel/book-again cho 2 UUID khác nhau; book 8 máy = 1 booking/8 seats/1 event. Lệnh/evidence của các phép đo ở TESTING-ACCEPTANCE §3. Chưa có claim các phép đo 1.1.0 đã đạt.
