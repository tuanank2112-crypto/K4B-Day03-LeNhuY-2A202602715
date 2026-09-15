# TESTING-ACCEPTANCE — Local Verification, Evidence and Exit Gates

## 1. Mục tiêu và nguyên tắc

Tệp này sở hữu phép đo cho Plan 01. Một claim chỉ được coi là đạt khi có **lệnh + exit code + machine evidence**. “Test xanh”, screenshot bằng mắt hoặc report kể chuyện không đủ.

BẮT BUỘC:
1. Dùng DB temp/disposable cho test; không chạm `data/cyber_ops.db` của người dùng.
2. Không dùng live LLM/network/API key trong gate bắt buộc; provider fake deterministic.
3. Fail=0, error=0, skip=0, xfail=0, xpass=0.
4. Các phép đo race chạy nhiều process/thread theo đúng boundary cần bảo vệ; không thay bằng mock lock.
5. RED proof phải tồn tại trước claim fix; mutant phải từng làm test fail.
6. Evidence dưới `planning/01_2026-09-15_cyber-ops-v2/evidence/`, là output máy và CẤM sửa tay.
7. G00 chỉ ✅ sau khi WP00 🔴 có H01/R01 thẩm định độc lập, R01 dòng cuối `✅ DUYỆT`, và machine evidence `.txt` tồn tại.
8. Mọi file committed dưới `planning/.../evidence/` BẮT BUỘC đuôi `.txt` theo HANDOFF_PROTOCOL §14, kể cả khi nội dung bên trong là JSON, XML/JUnit hoặc text.

## 1.1. G00 — cổng dossier trước WP01

G00 KHÔNG được dùng helper trong `tests.acceptance` vì helper đó thuộc WP06. Trình tự bắt buộc:
1. H01 auditor chạy `python tools/brain_dossier_check.py planning/01_2026-09-15_cyber-ops-v2 --phase dispatch` và redirect stdout vào `evidence/wp00-spec-audit/dossier.txt`.
2. Auditor tự thiết kế ≥3 cách phá, ghi output máy vào `.txt`, nộp `R01_tham-dinh_wp00-spec-package.md` với dòng cuối `⏳ Chờ phán quyết.`.
3. SO đo lại, ghi phán quyết vào R01. Nếu dòng cuối là `✅ DUYỆT`, chạy `python tools/brain_dossier_check.py planning/01_2026-09-15_cyber-ops-v2 --phase ready` → `evidence/wp00-spec-audit/ready.txt`.
4. Chỉ sau `ready` exit 0 mới đổi G00 thành ✅ và tạo handoff thi công WP01.

CẤM tạo report/evidence placeholder để làm checker xanh.

## 2. Baseline RED proof trên base SHA

Base cố định:
`eb1022a4f801215a691cfd0b6f5e313274618a6f`.

WP06 phải cung cấp helper `python -m tests.acceptance ...`; helper được chạy từ code mới nhưng có thể probe một Git worktree ở base.

PowerShell contract:

```powershell
$base = "eb1022a4f801215a691cfd0b6f5e313274618a6f"
$wt = Join-Path $env:TEMP "nitro-base-eb1022a"
git worktree add --detach $wt $base
python -m tests.acceptance probe-base --repo $wt `
  --out planning/01_2026-09-15_cyber-ops-v2/evidence/baseline/base-probe.txt
$probeExit = $LASTEXITCODE
git worktree remove --force $wt
exit $probeExit
```

`probe-base` pass nghĩa **đã tái hiện đúng bug cũ**, không phải base đúng.

Bắt buộc ghi nhận:
- `B01_NEGATIVE_DURATION`: `duration_hours=-1` trên legacy trả SUCCESS với total âm; expected RED reproduced.
- `B02_PARTIAL_MULTI_BOOK`: request nhóm gồm một PC hợp lệ + `VIP-999` làm PC hợp lệ bị mutation trước khi toàn request thất bại/hoặc trả sai success; expected RED reproduced.
- Baseline probe không được sửa base worktree.
- Evidence ghi base SHA, Python version, input, before/after state và observed result.

Nếu không tái hiện được một bug, dừng và cập nhật SPEC; CẤM đổi test cho khớp giả định cũ.

## 3. Cấu trúc test bắt buộc

```text
tests/
├── conftest.py
├── unit/
│   ├── test_models_validation.py
│   ├── test_fee_and_normalization.py
│   └── test_trace_redaction.py
├── integration/
│   ├── test_migration.py
│   ├── test_booking_transactions.py
│   ├── test_idempotency.py
│   ├── test_restart_persistence.py
│   └── test_operations_backup_restore.py
├── concurrency/
│   └── test_booking_race.py
├── contract/
│   ├── test_rest_api.py
│   ├── test_mcp_protocol.py
│   └── test_legacy_compatibility.py
├── browser/
│   ├── test_realtime_ui.py
│   ├── test_xss_dom_safety.py
│   └── test_accessibility_smoke.py
└── acceptance/
    ├── __main__.py
    ├── test_tc01_tc05.py
    └── test_exit_gates.py
```

Tên file là contract tối thiểu; được tách nhỏ thêm nhưng không được bỏ phạm vi.

## 4. Lệnh quality gate

```powershell
python -m compileall -q src
python -m ruff check src tests
python -m mypy src

python -m pytest -q --strict-markers `
  --junitxml=planning/01_2026-09-15_cyber-ops-v2/evidence/quality/pytest-junit.txt

python -m playwright install chromium

python -m pytest -q -m browser `
  --junitxml=planning/01_2026-09-15_cyber-ops-v2/evidence/quality/browser-junit.txt

python -m tests.acceptance verify-junit `
  planning/01_2026-09-15_cyber-ops-v2/evidence/quality/pytest-junit.txt `
  planning/01_2026-09-15_cyber-ops-v2/evidence/quality/browser-junit.txt
```

`verify-junit` exit `1` nếu:
- failure/error/skipped/xfail/xpass >0;
- report thiếu;
- mandatory node thiếu;
- unique collected count giảm so với baseline acceptance đã ghi cho cùng matrix.

Lệnh browser riêng chỉ tạo evidence/reproduce; tổng unique tests không được double-count.

## 5. Ma trận bắt buộc theo Gate

| Gate | Phép đo bắt buộc | Kỳ vọng | Evidence tối thiểu |
| :-- | :-- | :-- | :-- |
| G00 | `python tools/brain_dossier_check.py planning/01_2026-09-15_cyber-ops-v2 --phase ready` | đủ 8 SPEC, 0 dấu nháp, 0 broken link, router khớp | `wp00-spec-audit/ready.txt` |
| G01 | fresh migrate + inspect | schema1; 32 machines, 2 members, 8 menu, 3 active bookings/seats; integrity ok/FK0 | `migration/fresh.txt` |
| G02 | book → stop process → process mới read | cùng booking_id/seat; không mất mutation | `migration/restart.txt` |
| G03 | 20 contender cùng `VIP-08` trên DB fresh có PC available | exactly success=1, PC_UNAVAILABLE=19, DB_BUSY=0 | `concurrency/book-race.txt` |
| G04 | group book có 1 PC invalid/unavailable + fault after first seat | delta booking/seat/idempotency/outbox =0 | `transactions/all-or-nothing.txt` |
| G05 | invalid duration/quantity/held/id/bool/extra field | đúng code/status; delta business=0 | `validation/negative.txt` |
| G06 | replay cùng key/payload + cùng key khác payload | replay cùng result/record count; mismatch=IDEMPOTENCY_CONFLICT | `idempotency/replay.txt` |
| G07 | REST/OpenAPI/auth/ownership/origin/body limit | status/schema đúng; actor khác không mutation | `api/rest.txt`, `api/security.txt` |
| G08 | MCP initialize + tools/list + tools/call đủ 5 tool + invalid protocol | protocol/business error tách đúng; structuredContent schema đúng | `mcp/conformance.txt` |
| G09 | 2 browser contexts + reconnect + 20 XSS payload | event p95≤1000ms local; snapshot đúng; 0 script/dialog execution | `web/browser.txt`, `web/latency.txt` |
| G10 | 100 runtime trace events | 0 field/raw secret cấm; correlation ID valid; latency≥0 | `security/trace-redaction.txt` |
| G11 | full quality commands | exit0; fail/error/skip/xfail/xpass=0 | `quality/*.txt` |
| G12 | OPERATIONS R12-A + R12-B | restore manifest/SHA/count khớp; fresh fault không schema nửa vời | `operations/rollback-*.txt` |
| G13 | TC01–TC05 qua fake provider + service thật | completed5; expected tool sequence/result; TC05 0 write | `compatibility/tc01-tc05.txt` |
| G14 | version/doc/link audit | app=1.1.0 mọi nguồn; brain template không đổi; 0 broken link | `release/docs-version.txt` |

G00–G14 đều là `local`; không có server/production gate trong hồ sơ này.

## 6. Cases bắt buộc chi tiết

### 6.1. Validation / G05

BẮT BUỘC có case:
- duration: `0`, `-1`, `25`, `2.0`, `"2"`, `true`;
- quantity: `0`, `-1`, `21`, float/string/bool;
- held_minutes: `-1`, `1441`, float/string/bool;
- pc id sai syntax; pc id đúng syntax nhưng không tồn tại;
- duplicate pc IDs sau normalize;
- 9 PCs trong group;
- extra JSON field;
- body >65.536 byte;
- wrong content-type và invalid JSON.

Mỗi case mutation ghi before/after counts/hash projection để chứng minh `0 business mutation`.

### 6.2. Transaction / G03–G04

Race harness:
- process/thread barrier để 20 contenders bắt đầu gần đồng thời;
- mỗi contender có **member/session/key riêng hợp lệ theo case** hoặc cùng member nhưng key riêng;
- target PC ban đầu AVAILABLE;
- sau join: 1 active seat đúng target, 1 booking, 1 machines.changed outbox cho winner;
- 19 loser `PC_UNAVAILABLE`, không `DB_BUSY`;
- `integrity_check=ok`, FK0.

Atomicity:
- group 2–8 seats;
- invalid/not-found/unavailable ở vị trí đầu/giữa/cuối;
- fault injection sau insert booking, sau seat #1, trước idempotency, trước outbox, trước COMMIT;
- mọi fault trước commit ⇒ delta=0.

### 6.3. Idempotency / G06

Bắt buộc:
- book/cancel/order: same key+same normalized payload replay;
- same key+different payload → conflict;
- response mất sau COMMIT rồi retry cùng key;
- new login/session nhưng cùng member/key vẫn replay;
- auth fail không tạo completed record;
- DB_BUSY không sinh key mới;
- chat PENDING same instance → REQUEST_IN_PROGRESS;
- stale PENDING old instance → CHAT_INTERRUPTED;
- child tool commit + provider timeout: parent response persisted, retry không gọi provider lần hai.

### 6.4. REST / G07

Bắt buộc:
- `/api/v1/health`, pcs, menu, bookings, bookings POST, cancellations, orders, chat, traces;
- legacy aliases theo P02 §5;
- missing/expired/revoked session;
- cookie/Bearer mismatch;
- owner khác cancel/order;
- Origin allowed/denied + preflight;
- Host invalid;
- Idempotency-Key missing/malformed;
- rate-limit trả Retry-After;
- response schema mismatch forced →500;
- no endpoint trả business failure bằng HTTP200.

### 6.5. MCP / G08

Bắt buộc chạy **client/SDK thật**, không gọi class alias trực tiếp:
- initialize → initialized → tools/list;
- exactly 5 tools stable sort;
- ping;
- mỗi tool có success case;
- mutation thiếu token/key;
- request trước initialized;
- parse error, invalid request, unknown method, invalid params;
- `duration_hours:"2"` → -32602;
- `VIP-999` đúng type → structured `PC_NOT_FOUND`, `isError=true`;
- stdout không có banner/log ngoài protocol; stderr diagnostic được phép;
- EOF shutdown exit0.

### 6.6. Web/trace / G09–G10

Realtime:
- two contexts cùng nhận one committed event;
- p95 local over 20 mutations ≤1000ms;
- offline 3 mutations → reconnect snapshot có state cuối;
- private outbox seq gap không bị coi lost event;
- rollback transaction không phát ghost event;
- queue/backpressure close/reconnect từ snapshot.

XSS corpus tối thiểu 20 payload đi qua chat final text, error, menu/specs và trace projection; payload phải hiện như text và `window.alert`/script marker không chạy.

Trace corpus 100 events:
- allowlist đúng 6 field top-level;
- không có `thought`, `reasoning`, raw prompt/history, token, PIN, cookie, Authorization, key, raw provider output;
- customer_id nếu có = `[REDACTED]`;
- correlation UUID valid;
- latency real và >=0.

## 7. TC01–TC05 compatibility / G13

Nguồn câu hỏi/ID/type giữ nguyên `config/test_cases.json`.

Bắt buộc:
- TC01: không tool call; trả thông tin quán đã công bố.
- TC02: `check_available_pcs(zone='VIP')`.
- TC03: `book_gaming_pc` NET2026/VIP-08/3h; canonical total 54.000 VND.
- TC04: read PRO_GAMING trước, sau đó book PRO-01/2h; canonical total 50.000 VND.
- TC05: VIP-999 → legacy NOT_FOUND / canonical PC_NOT_FOUND; 0 booking/seat/key/outbox mutation.

CI provision session fixture; không hardcode/bypass auth trong application code.

## 8. Mutation RED proof / WP08

Harness contract:

```powershell
python -m tests.acceptance run-mutants `
  --mutants unique-guard,partial-seat-commit,ownership-bypass,xss-sink,outbox-before-commit `
  --out planning/01_2026-09-15_cyber-ops-v2/evidence/quality/mutants.txt
```

Mỗi mutant:
- chỉ tồn tại trong temp copy/worktree;
- ít nhất 1 test mục tiêu phải fail;
- code đúng cùng test phải pass;
- tổng `killed=5`, `survived=0`.

CẤM commit mutant hoặc sửa expected để làm mutant “chết”.

## 9. Thẩm định đối kháng WP08

Auditor độc lập, không đọc report worker trước khi tự thiết kế phá. Tối thiểu 3 nhóm:

1. **Race/atomicity:** two-process same PC, kill/exception ở ranh COMMIT, idempotent lost-response.
2. **Security/perimeter:** ownership tamper, cookie/Bearer mismatch, Origin/Host, XSS/trace secret.
3. **Rollback/data safety:** backup corrupted, target exists, new post-upgrade mutation rồi thử restore backup cũ.

Phán quyết chỉ:
- `✅ DUYỆT`
- `🔁 SỬA: <mục SPEC/gate>`
- `⛔ DỪNG: <rủi ro>`

Fail hai lần hoặc evidence mâu thuẫn ⇒ phân xử 🔴.

## 10. Error taxonomy của acceptance

| Code | Điều kiện | Hành vi |
| :-- | :-- | :-- |
| `SPEC_AUDIT_FAILED` | thiếu file/link/section hoặc còn dấu nháp | G00 đỏ; sửa SPEC |
| `BASELINE_NOT_REPRODUCED` | probe base không thấy bug đã tuyên bố | dừng; sửa assumption |
| `TEST_FAILURE` | assertion/error >0 | gate tương ứng đỏ |
| `TEST_SKIPPED` | skip/xfail/xpass >0 | G11 đỏ; không miễn trừ âm thầm |
| `TEST_COUNT_DECREASE` | mandatory node/count giảm | G11 đỏ; giải trình contract |
| `MUTANT_SURVIVED` | mutant không làm test đỏ | sửa test/phép đo trước |
| `EVIDENCE_MISSING` | command pass nhưng file evidence thiếu | gate chưa đạt |
| `EVIDENCE_SECRET_FOUND` | evidence chứa secret/raw thought | xóa artifact rò rỉ, rotate secret nếu có, gate đỏ |
| `VERSION_MISMATCH` | source/docs/health/MCP version lệch | G14 đỏ |
| `DOC_LINK_BROKEN` | link/router không resolve | G00/G14 đỏ |

## 11. Vùng cấm

- CẤM `skip`, `xfail`, `continue-on-error`, `importorskip` ở gate bắt buộc.
- CẤM mock `CyberService` trong integration/concurrency/browser E2E.
- CẤM dùng `threading.Lock` trong test harness để vô tình serialize race.
- CẤM gọi class MCP compatibility thay client protocol thật để claim conformance.
- CẤM dùng live provider/network làm điều kiện pass.
- CẤM sửa `config/test_cases.json` để test dễ hơn.
- CẤM hand-edit XML/JSON/TXT evidence.
- CẤM mark gate ✅ chỉ từ report worker; người duyệt phải chạy/đo lại.
