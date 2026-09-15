# P02 — REST, Sessions, MCP and Compatibility

## 1. Hợp đồng adapter

`create_app(settings: Settings) -> FastAPI` không mở DB/LLM ở import time; lifespan mở repository, kiểm migration, tạo services/dispatcher rồi đóng sạch khi shutdown. `start_server(port: int = 8080) -> None` giữ CLI `python src/web_server.py 8080`, gọi Uvicorn một worker, host local theo OPERATIONS. Sync service chạy trong worker thread; LLM gọi ngoài transaction và có timeout.

REST prefix canonical `/api/v1`; alias `/api/pcs`, `/api/book`, `/api/cancel`, `/api/chat`, `/api/traces` tồn tại trọn 1.1.x. Alias cũng cần auth/key và cùng status code khi lỗi. Không giữ lỗ hổng CORS/bypass auth để mô phỏng compatibility.

## 2. Session và perimeter

`POST /api/v1/session` nhận `{member_id:MemberId,pin:str}`; PIN 8–64 ký tự, không trim. Hash PBKDF2-HMAC-SHA256 ≥600.000 iterations, salt random 16 byte, so bằng constant-time. Lệnh member-pin local provision riêng, không dùng PIN mặc định hoặc ID làm mật khẩu. Member chưa provision/sai PIN/không tồn tại cùng UNAUTHENTICATED 401; đường kiểm sai member vẫn chạy KDF dummy.

Login thành công 201: `{status:"SUCCESS",data:{token,member_id,expires_at_ms},message,correlation_id}`; token random 32 byte encode base64url không padding, DB lưu SHA-256 token. Thời hạn tuyệt đối 8 giờ, không sliding. Cookie `cyber_session` HttpOnly, SameSite=Strict, Path=/, Max-Age=28800; local HTTP không Secure, nếu dùng HTTPS phải Secure. Token chỉ trả lúc login; CẤM log hoặc lưu localStorage. Web dùng cookie, CLI/MCP dùng token qua process environment riêng.

`GET /api/v1/session` trả 200 data `{member_id,expires_at_ms}` sau auth; `DELETE /api/v1/session` revoke token, expire cookie, trả 204. Login/logout là lifecycle exception: không đòi business idempotency key và login không đòi session có sẵn. Tất cả mutation booking/cancel/order/chat bắt buộc session và key.

Auth nhận cookie hoặc `Authorization: Bearer TOKEN`; nếu cả hai có giá trị khác nhau → 401. Không nhận token trong query string, JSON tool args hay chat. Mutating request có cookie bắt buộc Origin đúng allowlist; Bearer từ CLI được phép không Origin. Origin có mặt nhưng ngoài allowlist → 403 trên mọi endpoint, bao gồm preflight/login/WS. Host allowlist `127.0.0.1`, `localhost`, `[::1]` với port đang chạy; không tin X-Forwarded headers.

CORS mặc định exact `http://127.0.0.1:8080`, `http://localhost:8080`; credentials=true; methods GET/POST/DELETE/OPTIONS, headers Content-Type/Authorization/Idempotency-Key/X-Correlation-ID. CẤM `*` và phản chiếu Origin tùy ý. Preflight hợp lệ 204. Body streaming giới hạn 65.536 byte kể cả thiếu Content-Length/chunked; sai JSON=400, sai content-type=415, extra field/type/range=422. Request deadline 10s thông thường, chat 60s.

Rate limit token bucket in-memory một worker: login 5 lần/phút/IP, burst5; mutation 120/phút/member, burst30; chat 10/phút/member, burst2; read 300/phút/IP, burst60. 429 có `Retry-After` số giây tối thiểu1. Giới hạn connection WebSocket tại P03. Không dùng rate limit thay permission.

## 3. REST matrix và body

Success/Failure chuẩn từ 01 §2, luôn `Content-Type: application/json`; lỗi theo 01 §5. GET lists không có item trả 200 với list/dict rỗng. Mutations phải có `Idempotency-Key`; thiếu/sai → 422. Replay giữ status thành công ban đầu, thêm `Idempotency-Replayed: true`.

| Endpoint | Input | Success | data schema |
| :-- | :-- | :--: | :-- |
| GET `/api/v1/health` | Không | 200 / 503 | `{version:"1.1.0",schema_version:1,database:"ok"|"unavailable"}` |
| GET `/api/v1/pcs` | `zone=ALL` hoặc Zone, `available_only=false` boolean | 200 | `{center_name,stats,pcs:dict[PcId,MachineView],cursor:int}` |
| GET `/api/v1/menu` | `category=ALL` hoặc Category | 200 | MenuResult |
| GET `/api/v1/bookings` | Session bắt buộc | 200 | `{bookings:list[BookingResult]}` chỉ ACTIVE của principal |
| POST `/api/v1/bookings` | `{pc_ids:list[PcId],duration_hours:int=2}` | 201 | BookingResult |
| POST `/api/v1/cancellations` | `{pc_id:PcId,held_minutes:int=30}` | 200 | CancelResult |
| POST `/api/v1/orders` | `{item_name:str,pc_id:PcId|null=null,quantity:int=1}` | 201 | OrderResult |
| POST `/api/v1/chat` | `{message:str,history:list[HistoryItem]=[]}` | 200 | `{final_answer:str,trace_logs:list[TraceEvent],operation_results:list[Success|Failure]}` |
| GET `/api/v1/traces` | Session; `limit:int=100`, range1–100 | 200 | `{traces:list[TraceEvent]}` của member/session hiện tại |

`stats` gồm TOTAL/AVAILABLE/OCCUPIED/BOOKED/MAINTENANCE; tính trên toàn 32 máy dù filter có dùng. `cursor` và pcs đọc trong cùng SQLite read transaction. Public machine data không chứa owner/name/booking_id. Unknown route=404, method sai=405, body response schema sai=500 và log correlation ID.

Ví dụ canonical lỗi: `{"status":"ERROR","error":{"code":"PC_UNAVAILABLE","message":"Máy đã được giữ.","retryable":false,"details":{"pc_ids":["VIP-08"]}},"correlation_id":"57b19994-57cd-482a-b251-610e91eeefc0"}` với HTTP409. Không trả HTTP200 cho lỗi nghiệp vụ ở REST.

### 3.1. Chat orchestration

`HistoryItem(role:Literal['user','assistant'],content:str)` tối đa 20 item, content mỗi item ≤4000 ký tự; message strip dài1–4000. Không nhận role system/tool hay forged tool_result. History là nội dung tham khảo, không thể cấp quyền hoặc chứng minh tool đã chạy.

`ChatCoordinator.run(message: str, history: list[HistoryItem], context: RequestContext) -> ChatResult`: reserve idempotency `(member,'chat',key)` PENDING trong transaction ngắn, hash cả normalized message/history, owner_instance UUID của web process. Provider timeout30s/call, tổng60s, tối đa10 vòng và tối đa10 tool calls. Child mutation key = SHA-256 của `chat_key + ':' + sequential_tool_index` (index0–9); actor luôn từ context, không từ model. Mỗi child dùng CyberService; sau khi tất cả xong lưu parent COMPLETED + final response trong transaction ngắn.

Duplicate parent COMPLETED replay nguyên kết quả; PENDING cùng instance →409 REQUEST_IN_PROGRESS/Retry-After1, tuyệt đối không chạy provider lần hai. Boot web đổi những parent PENDING từ instance cũ thành INTERRUPTED với CHAT_INTERRUPTED và timestamp; không chạy lại chuỗi suy luận vì kết quả tool đã commit có thể tồn tại. Nếu chat timeout/provider lỗi sau child commit, response 503 có operation_results đã hoàn tất và trace summary; lưu response này như COMPLETED để retry không gọi provider lại. Trước khi user tạo key mới, UI refresh bookings. Các child transaction đã commit không bị giả vờ rollback bởi lỗi LLM.

Giữ `run_react_agent(user_query, provider, mcp_server) -> list` cho Python callers; thêm keyword context tùy chọn. Context thiếu chỉ được gọi read tools, write trả UNAUTHENTICATED. Không dùng shared mutable provider/chat history xuyên request. CLI và web dùng cùng coordinator để giữ key/timeout/redaction semantics.

## 4. MCP chuẩn qua stdio

Chốt protocol revision `2025-06-18`; triển khai bằng MCP Python SDK, dùng actual installed version tương thích và khóa trong requirements lock. Transport bắt buộc stdio: `python -m src.mcp_server --stdio`. HTTP MCP chưa trong scope; REST không tự xưng là MCP.

Protocol: initialize → notifications/initialized → tools/list hoặc tools/call. ServerInfo name `cyber-gaming-mcp-server`, version `1.1.0`, capabilities `{tools:{listChanged:false}}`; unsupported requested revision trả revision được hỗ trợ `2025-06-18`, client không hỗ trợ thì disconnect. Request id giữ nguyên kiểu string/integer; notifications không có response. `ping` trả result `{}`. Stdout chỉ JSON-RPC UTF-8 một message mỗi dòng; mọi diagnostic ra stderr. Quy định dựa trên [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle) và [stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

`tools/list` trả đúng5 tools dưới đây, stable sort theo name, không pagination khi chỉ5; inputSchema `type:object,additionalProperties:false`. Các giới hạn/enum dùng 01 §1. outputSchema mỗi tool là union Success[T]/Failure trong 01; root type object với discriminator status. Read tool không đòi session. Stdio mutation lấy token từ `CYBER_SESSION_TOKEN` tại launcher và authenticate mỗi call; idempotency từ `params._meta["cyber.local/idempotency-key"]`, correlation từ `_meta["cyber.local/correlation-id"]` hoặc server sinh. Không đưa token/key vào model schema.

| Tool name | inputSchema properties và required | Kết quả T |
| :-- | :-- | :-- |
| `check_available_pcs` | zone enum + ALL, default ALL; required=[] | AvailabilityResult |
| `book_gaming_pc` | customer_id MemberId; pc_id string1–256; duration_hours integer1–24; required cả3 | BookingResult |
| `cancel_or_release_pc` | customer_id MemberId; pc_id PcId; held_minutes integer0–1440 default30; required customer_id,pc_id | CancelResult |
| `get_canteen_menu` | category enum + ALL, default ALL; required=[] | MenuResult |
| `order_canteen_item` | customer_id MemberId; item_name string1–120; pc_id string1–32 default `TẠI QUẦY`; quantity integer1–20 default1; required customer_id,item_name | OrderResult |

MCP book pc_id hỗ trợ CSV/semicolon legacy, normalize thành PcIds trước service; không loại bỏ duplicate im lặng. customer_id khác principal → FORBIDDEN. `tools/call` kết quả có `content:[{type:"text",text:JSON.stringify(envelope)}]`, `structuredContent:envelope`, `isError:false` khi SUCCESS, true khi business Failure. Không gửi JSON-RPC error kèm result. Đây là contract app chọn theo [MCP tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).

### 4.1. Phân loại protocol và business execution errors

| Tình huống | Response | Caller bắt buộc |
| :-- | :-- | :-- |
| JSON parse hỏng | JSON-RPC error -32700, id=null | Sửa framing/JSON |
| Envelope sai/invalid id/batch | error -32600, id=null nếu không xác định được | Sửa envelope |
| Method không hỗ trợ | error -32601, giữ request id | Dùng capability đã công bố |
| tools/call thiếu name, arguments không object, unknown tool, schema types/range sai | error -32602, giữ id | Sửa params theo inputSchema |
| DTO nội dung không hợp lệ sau normalize (duplicate CSV), thiếu key, expired session | result.isError=true, structured Failure | Sửa input/login/key; không gọi lại mù |
| PC_NOT_FOUND/PC_UNAVAILABLE/FORBIDDEN/IDEMPOTENCY_CONFLICT | result.isError=true, structured Failure | Xử lý nghiệp vụ theo 01 §5 |
| Repository busy/provider dependency lỗi đã phân loại | result.isError=true, structured Failure | Retry hữu hạn cùng key nếu retryable |
| Adapter hỏng trước thực thi/không serialize được output | error -32603 | Dừng và giữ request id/correlation |

Conformance tests phải bao phủ cả `duration_hours:"2"` → -32602 và unknown PC đúng cú pháp → structured PC_NOT_FOUND, tránh nhập nhằng hai lớp lỗi. SDK validators phải được cấu hình để giữ mapping này. Request tools trước initialized → error -32000 `Server not initialized`; notification lạ bỏ qua theo protocol, không ghi DB. Khi stdin EOF, shutdown hoàn tất và exit0; không in banner test legacy trên stdout.

## 5. Compatibility contract 1.1.x

Giữ tên hàm, positional args/defaults hiện tại trong `src/tools.py`: `execute_check_available_pcs(zone='ALL')`, `execute_book_gaming_pc(customer_id,pc_id,duration_hours=2)`, `execute_cancel_or_release_pc(customer_id,pc_id,held_minutes=30)`, `execute_get_canteen_menu(category='ALL')`, `execute_order_canteen_item(customer_id,item_name,pc_id='TẠI QUẦY',quantity=1)`, `dispatch_tool_call(tool_name,arguments)`; tất cả trả JSON string. Thêm keyword-only `context: RequestContext|None=None` để truyền auth; legacy caller không context chỉ được read.

`MCPAcademicServer` và alias `MCPCyberGameServer` còn tồn tại, `list_tools()` trả TOOLS_SCHEMA dạng parameters cho provider cũ; `call_tool(tool_name,arguments)` trả `{server,tool,result:legacy_result}`. Đây là Python compatibility envelope, không được gắn jsonrpc='2.0' vì thiếu request id. Class nhận keyword-only session/context factory để app không cần thay hai positional args. `version` đổi 1.1.0.

Serializer legacy flatten Success.data, thêm status/message. Single-seat book thêm pc_id/zone/specs/price_per_hour/duration_hours/total_cost, giữ booked_pcs/failed_pcs nếu có; booking_id là opaque UUID mới, không giữ định dạng mã lặp cũ. Availability rỗng → status NOT_FOUND. PC_NOT_FOUND → status NOT_FOUND/error_code PC_DOES_NOT_EXIST; PC_UNAVAILABLE → OCCUPIED/PC_ALREADY_OCCUPIED; FORBIDDEN → FORBIDDEN/UNAUTHORIZED_CANCELLATION khi cancel; lỗi khác ERROR với error_code canonical. Không giữ SUCCESS trên partial booking hay thời lượng âm.

Alias REST GET /api/pcs trả flattened center_name/stats/pcs/cursor; POST /api/book nhận đúng một trong pc_ids array hoặc pc_id string/list, duration_hours=2, customer_id optional phải bằng session nếu có; /api/cancel tương tự; /api/chat nhận body canonical và flatten final_answer/trace_logs; /api/traces trả list đã redacted của session. Aliases trả header `Deprecation: true`, Link tới docs adapter, chưa xóa trong 1.1.x.

CLI giữ `python src/app.py`, `--interactive`, `--all`. Auth có thể lấy từ CYBER_SESSION_TOKEN; interactive thiếu token yêu cầu member/PIN qua getpass, không echo. `--all` cần token đã cấp, thiếu token thì exit2 trước chạy case mutation; CI cấp session trong fixture. TC01–TC05 giữ nội dung và thứ tự tool dự kiến, không phụ thuộc format booking code/thought. Live LLM không phải gate CI.

## 6. Luật và vùng cấm

BẮT BUỘC xác thực actor trước gọi service; key nằm ngoài LLM input. BẮT BUỘC mọi alias đi qua validation/ownership giống canonical route. CẤM nhận member ID từ text như quyền; CẤM static token/PIN mặc định; CẤM schema permissive để che lỗi; CẤM async endpoint giữ SQLite lock khi chờ provider. CẤM sửa contract unknown-tool thành SUCCESS empty payload vì caller sẽ hiểu sai.

## 7. Số đo thật / nghiệm thu local

Base có5 tool, MCPAcademicServer.call_tool không có request id/lifecycle và dùng key `parameters`; server bind0.0.0.0, CORS*, POST thường trả200 ngay cả business error. Đây là baseline đã đọc từ tracked source, không là bằng chứng MCP chuẩn.

Gate local: tools/list count5, gọi đủ5 bằng MCP SDK ClientSession; test integer và string request id giữ nguyên, unknown tool=-32602, business conflict có isError=true/structuredContent; REST 401/403/409/413/422/429 đúng body và 0 business write; hai member không hủy chéo; replay20 request cùng key =1 booking; CLI compatibility5/5. Evidence theo TESTING-ACCEPTANCE, chưa có kết quả runtime 1.1.0.
