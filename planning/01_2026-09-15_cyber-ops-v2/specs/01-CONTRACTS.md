# 01 — Data and Domain Contracts

## 1. Quy ước kiểu dữ liệu

BẮT BUỘC Pydantic v2 models với `ConfigDict(extra="forbid", strict=True)`. JSON integer không nhận bool, float hay chuỗi số; số tiền dùng integer VND. ID normalize `strip().upper()` chỉ ở input ID, không trên token/key. Timestamp là UTC epoch milliseconds, JSON field có hậu tố `_at_ms`; clock injectable vào service.

| Kiểu | Ràng buộc chính xác |
| :-- | :-- |
| `MemberId` | Regex `^[A-Z0-9_]{3,32}$` |
| `PcId` | Regex `^(VIP|PRO|STD|STREAM)-[0-9]{2,3}$`; đúng cú pháp chưa có row vẫn `PC_NOT_FOUND` |
| `EntityId` | UUID canonical lowercase; seed dùng UUID5, runtime UUID4 |
| `Zone` | `VIP`, `STANDARD`, `PRO_GAMING`, `STREAM`; filter thêm `ALL` |
| `Category` | `FOOD`, `DRINK`, `SNACK`; filter thêm `ALL` |
| `IdempotencyKey` | 16–128 ký tự ASCII `[A-Za-z0-9._:-]`; phân biệt hoa thường |
| `CorrelationId` | UUID4 do server sinh; inbound hợp lệ được giữ, inbound sai thay mới |
| `DurationHours` | Strict integer 1–24 |
| `Quantity` | Strict integer 1–20 |
| `HeldMinutes` | Strict integer 0–1440, mặc định 30 cho compatibility; chỉ tính phí demo |
| `PcIds` | Mảng 1–8 PcId, không trùng sau normalize; thứ tự canonical = sort |
| `ItemName` | Chuỗi NFC, strip, dài 1–120; resolve theo P01 §4 |

## 2. DTO và kết quả

Tất cả field không đánh dấu mặc định đều bắt buộc. `Principal` là object nội bộ do SessionService tạo, không deserialize từ JSON caller.

```text
Principal(member_id: MemberId, session_hash: str, expires_at_ms: int)
RequestContext(principal: Principal, idempotency_key: IdempotencyKey, correlation_id: CorrelationId)
BookCommand(pc_ids: list[PcId], duration_hours: DurationHours = 2)
CancelCommand(pc_id: PcId, held_minutes: HeldMinutes = 30)
OrderCommand(item_name: ItemName, pc_id: PcId | None = None, quantity: Quantity = 1)
MachineView(pc_id: PcId, zone: Zone, specs: str, status: AVAILABLE|OCCUPIED|BOOKED|MAINTENANCE,
            price_per_hour: int)
SeatResult(pc_id: PcId, zone: Zone, price_per_hour: int, duration_hours: int, total_cost: int)
BookingResult(booking_id: EntityId, customer_id: MemberId, customer_name: str,
              booked_pcs: list[PcId], failed_pcs: list[str], seats: list[SeatResult],
              duration_hours: int, total_cost: int, created_at_ms: int)
CancelResult(booking_id: EntityId, pc_id: PcId, customer_id: MemberId, refund_code: EntityId,
             duration_hours: int, held_minutes: int, initial_cost: int, deducted_fee: int,
             refund_amount: int, counter_notice: str)
OrderResult(order_id: EntityId, customer_id: MemberId, pc_id: PcId | None,
            item_name: str, quantity: int, unit_price: int, total_cost: int, created_at_ms: int)
AvailabilityResult(zone_filter: str, total_available: int, pcs: dict[PcId, MachineView])
MenuItemView(item_id: EntityId, item_name: str, category: Category, price: int,
             status: AVAILABLE|UNAVAILABLE, specs: str)
MenuResult(category_filter: str, total_items: int, menu: dict[str, MenuItemView])
ErrorBody(code: str, message: str, retryable: bool, details: dict[str, str | int | list[str]])
Success[T](status: Literal["SUCCESS"], data: T, message: str, correlation_id: CorrelationId)
Failure(status: Literal["ERROR"], error: ErrorBody, correlation_id: CorrelationId)
```

`BookingResult.failed_pcs` luôn `[]`; field giữ cho compatibility. Phí = tổng `price_per_hour_snapshot * duration_hours`. Không có JSON `NaN`, Infinity, raw exception hay SQL. `Success`/`Failure` là envelope canonical REST/MCP; compatibility serializer flatten `data` theo P02 §5.

## 3. SQLite DDL bất biến

`PRAGMA user_version=1` là schema version, độc lập app 1.1.0. Mọi connection: `foreign_keys=ON`, `busy_timeout=5000`; database file bật WAL và `synchronous=FULL`. DDL migration 001:

```sql
CREATE TABLE schema_migration (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  applied_at_ms INTEGER NOT NULL
);
CREATE TABLE member (
  member_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  tier TEXT NOT NULL,
  balance_vnd INTEGER NOT NULL CHECK(balance_vnd>=0),
  favorite_zone TEXT NOT NULL,
  pin_salt TEXT,
  pin_hash TEXT,
  pin_iterations INTEGER CHECK(pin_iterations>=600000),
  CHECK((pin_salt IS NULL AND pin_hash IS NULL AND pin_iterations IS NULL)
     OR (pin_salt IS NOT NULL AND pin_hash IS NOT NULL AND pin_iterations IS NOT NULL))
);
CREATE TABLE machine (
  pc_id TEXT PRIMARY KEY,
  zone TEXT NOT NULL CHECK(zone IN ('VIP','STANDARD','PRO_GAMING','STREAM')),
  specs TEXT NOT NULL,
  base_status TEXT NOT NULL CHECK(base_status IN ('AVAILABLE','OCCUPIED','MAINTENANCE')),
  price_per_hour INTEGER NOT NULL CHECK(price_per_hour>0)
);
CREATE TABLE booking (
  booking_id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES member(member_id),
  duration_hours INTEGER NOT NULL CHECK(typeof(duration_hours)='integer' AND duration_hours BETWEEN 1 AND 24),
  status TEXT NOT NULL CHECK(status IN ('ACTIVE','CANCELLED')),
  created_at_ms INTEGER NOT NULL,
  closed_at_ms INTEGER,
  CHECK((status='ACTIVE' AND closed_at_ms IS NULL) OR (status='CANCELLED' AND closed_at_ms IS NOT NULL))
);
CREATE TABLE booking_seat (
  booking_id TEXT NOT NULL REFERENCES booking(booking_id),
  pc_id TEXT NOT NULL REFERENCES machine(pc_id),
  price_per_hour INTEGER NOT NULL CHECK(price_per_hour>0),
  released_at_ms INTEGER,
  held_minutes INTEGER CHECK(typeof(held_minutes)='integer' AND held_minutes BETWEEN 0 AND 1440),
  deducted_fee INTEGER CHECK(deducted_fee>=0),
  refund_amount INTEGER CHECK(refund_amount>=0),
  refund_code TEXT UNIQUE,
  PRIMARY KEY(booking_id,pc_id),
  CHECK((released_at_ms IS NULL AND held_minutes IS NULL AND deducted_fee IS NULL AND refund_amount IS NULL AND refund_code IS NULL)
     OR (released_at_ms IS NOT NULL AND held_minutes IS NOT NULL AND deducted_fee IS NOT NULL AND refund_amount IS NOT NULL AND refund_code IS NOT NULL))
);
CREATE UNIQUE INDEX uq_active_machine ON booking_seat(pc_id) WHERE released_at_ms IS NULL;
CREATE TABLE menu_item (
  item_id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL CHECK(category IN ('FOOD','DRINK','SNACK')),
  price_vnd INTEGER NOT NULL CHECK(price_vnd>0),
  status TEXT NOT NULL CHECK(status IN ('AVAILABLE','UNAVAILABLE')),
  specs TEXT NOT NULL
);
CREATE TABLE food_order (
  order_id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES member(member_id),
  item_id TEXT NOT NULL REFERENCES menu_item(item_id),
  item_name TEXT NOT NULL,
  pc_id TEXT REFERENCES machine(pc_id),
  quantity INTEGER NOT NULL CHECK(typeof(quantity)='integer' AND quantity BETWEEN 1 AND 20),
  unit_price_vnd INTEGER NOT NULL CHECK(unit_price_vnd>0),
  total_cost_vnd INTEGER NOT NULL CHECK(total_cost_vnd=unit_price_vnd*quantity),
  status TEXT NOT NULL CHECK(status='PLACED'),
  created_at_ms INTEGER NOT NULL
);
CREATE TABLE member_session (
  token_hash TEXT PRIMARY KEY CHECK(length(token_hash)=64),
  member_id TEXT NOT NULL REFERENCES member(member_id),
  created_at_ms INTEGER NOT NULL,
  expires_at_ms INTEGER NOT NULL CHECK(expires_at_ms>created_at_ms),
  revoked_at_ms INTEGER
);
CREATE TABLE idempotency_record (
  member_id TEXT NOT NULL REFERENCES member(member_id),
  operation TEXT NOT NULL CHECK(operation IN ('book','cancel','order','chat')),
  request_key TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
  state TEXT NOT NULL CHECK(state IN ('PENDING','COMPLETED','INTERRUPTED')),
  response_json TEXT,
  owner_instance TEXT,
  created_at_ms INTEGER NOT NULL,
  completed_at_ms INTEGER,
  PRIMARY KEY(member_id,operation,request_key),
  CHECK((state='PENDING' AND response_json IS NULL AND completed_at_ms IS NULL)
     OR (state IN ('COMPLETED','INTERRUPTED') AND response_json IS NOT NULL AND completed_at_ms IS NOT NULL))
);
CREATE TABLE event_outbox (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL CHECK(kind IN ('machines.changed','food_order.created')),
  payload_json TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  correlation_id TEXT NOT NULL
);
CREATE VIEW machine_state AS
SELECT m.pc_id,m.zone,m.specs,m.price_per_hour,
       CASE WHEN EXISTS(SELECT 1 FROM booking_seat s WHERE s.pc_id=m.pc_id AND s.released_at_ms IS NULL)
            THEN 'BOOKED' ELSE m.base_status END AS status
FROM machine m;
PRAGMA user_version=1;
```

BẮT BUỘC service duy trì: ACTIVE header có ≥1 seat chưa release; CANCELLED header có 0 seat chưa release; active seat chỉ trên machine.base_status=AVAILABLE. Partial unique index là bảo vệ tranh chấp cuối cùng. Không cập nhật machine.status song song với view. `food_order` không trừ stock hay số dư.

`response_json` lưu envelope nghiệp vụ đã loại secret; canonical JSON UTF-8 `sort_keys=True,separators=(',',':'),ensure_ascii=False`, hash SHA-256 trên `{operation,payload}` đã normalize. Không đưa correlation ID, key, token, PIN vào payload hash. Response replay giữ correlation ID của lần commit đầu tiên; header `X-Correlation-ID` vẫn phản ánh request hiện tại.

## 4. Chữ ký domain/service

```text
CyberService.__init__(repository: Repository, clock: Callable[[], int], uuid_factory: Callable[[], str])
CyberService.list_machines() -> list[MachineView]
CyberService.check_available_pcs(zone: str = "ALL") -> AvailabilityResult
CyberService.get_canteen_menu(category: str = "ALL") -> MenuResult
CyberService.book(command: BookCommand, context: RequestContext) -> Success[BookingResult]
CyberService.cancel(command: CancelCommand, context: RequestContext) -> Success[CancelResult]
CyberService.order(command: OrderCommand, context: RequestContext) -> Success[OrderResult]
CyberService.list_my_bookings(principal: Principal) -> list[BookingResult]
SessionService.login(member_id: MemberId, pin: str) -> SessionGrant
SessionService.authenticate(token: str) -> Principal
SessionService.logout(principal: Principal) -> None
```

`SessionGrant(token: str, member_id: MemberId, expires_at_ms: int)` không được log. Domain validation chạy cả khi gọi từ Python; không chỉ dựa vào REST DTO. Re-check session chưa hết hạn/chưa revoked trong cùng transaction mutation, không tin Principal cũ vô thời hạn. SessionService có quyền ghi session/PIN, migration có quyền DDL/seed; mọi adapter nghiệp vụ chỉ gọi CyberService.

## 5. Error taxonomy và caller

| Code | REST | Điều kiện | Caller bắt buộc |
| :-- | :--: | :-- | :-- |
| `INVALID_JSON` | 400 | JSON hỏng | Sửa body; không retry tự động |
| `VALIDATION_ERROR` | 422 | Type/range/enum/duplicate IDs/extra field | Hiển thị field lỗi, 0 business mutation |
| `UNAUTHENTICATED` | 401 | Session thiếu/sai/expired/revoked, login sai | Đăng nhập lại; không tiết lộ member có tồn tại |
| `FORBIDDEN` | 403 | customer_id khác principal, hủy/giao đến máy người khác | Dừng, không đổi actor |
| `PC_NOT_FOUND`, `ITEM_NOT_FOUND`, `BOOKING_NOT_FOUND` | 404 | ID hợp lệ nhưng không có đối tượng | Refresh/chọn lại |
| `PC_UNAVAILABLE` | 409 | Bận/đã đặt/bảo trì hoặc unique conflict | Refresh máy; không tự đặt máy thay thế |
| `ITEM_UNAVAILABLE`, `AMBIGUOUS_ITEM` | 409 | Món tắt hoặc nhiều ứng viên | Chọn tên đầy đủ từ menu |
| `IDEMPOTENCY_CONFLICT` | 409 | Key cũ, payload khác | Khôi phục payload cũ hoặc ý định mới với key mới |
| `REQUEST_IN_PROGRESS` | 409 | Chat key đang PENDING trong process sống | Đợi Retry-After rồi gửi cùng key |
| `CHAT_INTERRUPTED` | 409 | Chat PENDING từ instance cũ | Xem booking thực tế trước khi tạo ý định mới |
| `REQUEST_TOO_LARGE` | 413 | Body >65.536 byte | Giảm body |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Mutation không JSON | Gửi application/json |
| `RATE_LIMITED` | 429 | Vượt token bucket | Theo Retry-After; cùng key |
| `DB_BUSY`, `PROVIDER_UNAVAILABLE` | 503 | Busy quá 5s/provider timeout | Retry hữu hạn cùng key; không báo thất bại booking đã commit |
| `INTERNAL_ERROR` | 500 | Lỗi ngoài phân loại | Giữ correlation ID, kiểm trạng thái; server rollback transaction hiện tại |

`DomainError` mang code/message/retryable/details; `retryable=true` chỉ DB_BUSY/PROVIDER_UNAVAILABLE/REQUEST_IN_PROGRESS/RATE_LIMITED. Mapping MCP riêng tại P02; không biến mọi lỗi thành JSON-RPC error. `details` không chứa owner ID, session hoặc traceback.

## 6. Vùng cấm

- CẤM key sinh từ suffix member/máy: booking UUID bảo đảm không trùng khi đặt-hủy-đặt lại.
- CẤM cân đối tiền bằng float, nhận quantity/duration âm, nhận bool như integer.
- CẤM xóa idempotency_record trong 1.1.0: xóa có thể lặp tác động của request cũ; retention là migration sau.
- CẤM dùng field `booked_by` công khai; endpoint owner chỉ trả dữ liệu principal.
- CẤM nâng schema âm thầm khi boot có checksum khác; dừng theo OPERATIONS.

## 7. Số đo thật / nghiệm thu

Baseline tracked HEAD có 0 bảng SQLite; 32/2/8 mock records. Probe `duration_hours=-1` trả SUCCESS với `total_cost=-18000`; đó là lỗi hiện tại, không phải behavior giữ lại.

Cổng local sau thi công: DDL chạy trên DB trống, `foreign_key_check` trả 0 row, `integrity_check` trả `ok`; 20 request cùng máy cho 1 active seat, 19 PC_UNAVAILABLE; so count booking/seat/order/idempotency/outbox trước/sau input sai = không đổi. Evidence máy theo TESTING-ACCEPTANCE, chưa được đánh dấu đạt tại thời điểm viết SPEC.
