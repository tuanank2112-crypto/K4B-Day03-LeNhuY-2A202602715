# OPERATIONS — Local Rollout, Backup, Rollback and Runbook

## 1. Phạm vi vận hành và nguồn chân lý

Tệp này sở hữu contract vận hành cho Plan 01 / target `1.1.0`. Chỉ áp dụng cho **local rollout** theo Đ10; không chứa deploy remote, production secret, reverse proxy, TLS public, multi-node hoặc multi-branch.

Nguồn contract:
- Kiến trúc và bất biến: `00-ARCHITECTURE.md`.
- DDL/types/error canonical: `01-CONTRACTS.md`.
- Transaction nghiệp vụ: `SPEC-P01-BOOKING-CORE.md`.
- REST/session/MCP: `SPEC-P02-API-MCP.md`.
- WebSocket/trace: `SPEC-P03-WEB-REALTIME.md`.
- Migration/CI/release: `SPEC-P04-QUALITY-MIGRATION.md`.
- Phép đo và Exit Gates: `TESTING-ACCEPTANCE.md`.

Nếu runbook này mâu thuẫn DDL/protocol/domain contract, **DỪNG rollout** và trả lại architect; CẤM người vận hành tự chọn một nghĩa mới.

### Bất biến local

1. BẮT BUỘC mặc định bind HTTP/WebSocket ở `127.0.0.1:8080`; không mở `0.0.0.0` trong hồ sơ này.
2. BẮT BUỘC mọi DB runtime dùng SQLite schema `PRAGMA user_version=1`, `foreign_keys=ON`, WAL, `busy_timeout=5000`, `synchronous=FULL`.
3. BẮT BUỘC dừng process ghi trước migration/restore/swap database.
4. BẮT BUỘC giữ bản database lỗi/failed rollout để điều tra; CẤM overwrite hoặc delete âm thầm.
5. BẮT BUỘC verify backup/restore bằng SHA-256 + `integrity_check` + `foreign_key_check` + manifest counts.
6. CẤM downgrade DDL destructive. Sau khi `1.1.0` đã nhận mutation mới, rollback code/data cần quyết định người; mặc định ưu tiên forward-fix.
7. CẤM ghi token/PIN/cookie/Authorization/Idempotency-Key vào command transcript hoặc evidence.
8. CẤM dùng dữ liệu local thật trong acceptance; rehearsal dùng database disposable.

## 2. CLI vận hành bắt buộc

WP01/WP07 phải hiện thực `python -m src.cyber_ops.manage ...`. Stdout của các lệnh có `--json` là **một JSON object UTF-8 duy nhất**; diagnostic ra stderr.

### 2.1. Contract command

```text
python -m src.cyber_ops.manage inspect
  --db <PATH> --json

python -m src.cyber_ops.manage migrate
  --db <PATH> [--legacy-json <PATH>] --json

python -m src.cyber_ops.manage backup
  --db <PATH> --out-dir <DIR> --json

python -m src.cyber_ops.manage verify-backup
  --backup-dir <DIR> --json

python -m src.cyber_ops.manage restore
  --backup-dir <DIR> --target <PATH> --json

python -m src.cyber_ops.manage member-pin
  --db <PATH> --member <MemberId>
```

`member-pin` đọc PIN hai lần bằng `getpass`; **CẤM** tham số `--pin`, env PIN hoặc stdout chứa PIN/hash/salt.

Exit code:
- `0`: thành công, output schema hợp lệ.
- `2`: usage/config/input không hợp lệ.
- `3`: schema/migration safety failure.
- `4`: backup/restore verification failure.
- `5`: integrity/health/smoke failure.

Không dùng exit `0` kèm `"status":"ERROR"`.

### 2.2. DatabaseManifest

`inspect`, `backup`, `verify-backup`, `restore` dùng cùng projection:

```text
DatabaseManifest(
  schema_version: int,
  file_sha256: str,
  file_bytes: int,
  integrity: Literal["ok"],
  foreign_key_errors: int,
  counts: {
    members:int, machines:int, bookings:int, active_bookings:int,
    booking_seats:int, active_seats:int, menu_items:int, food_orders:int,
    sessions:int, idempotency_records:int, outbox_events:int
  },
  max_outbox_seq: int
)
```

Manifest không chứa row business, token, owner, PIN hoặc trace.

### 2.3. Backup contract

`backup --db DB --out-dir DIR`:
- Từ chối nếu `DIR` đã tồn tại hoặc DB không pass `integrity_check`.
- Dùng SQLite backup API hoặc cơ chế snapshot nhất quán; CẤM copy file `.db` trần khi WAL còn hoạt động.
- Tạo đúng:
  - `DIR/database.sqlite3`
  - `DIR/manifest.json`
- `manifest.json.file_sha256` là SHA-256 của `database.sqlite3`.
- `verify-backup` mở **file backup**, kiểm `integrity_check=ok`, `foreign_key_errors=0`, counts và SHA.
- Backup verify fail ⇒ `BACKUP_VERIFY_FAILED`, exit `4`, **không migrate/restore**.

### 2.4. Restore contract

`restore --backup-dir DIR --target PATH`:
- BẮT BUỘC backup pass `verify-backup`.
- `PATH` phải **chưa tồn tại**. CẤM `--force`/overwrite trong `1.1.0`.
- Restore ra file tạm cùng filesystem, fsync, verify manifest, rồi atomic rename tới `PATH`.
- Sau restore, `inspect --db PATH` phải có SHA/count/schema bằng backup manifest.
- Target tồn tại ⇒ `RESTORE_TARGET_EXISTS`, exit `4`.

## 3. Tiền kiểm rollout

Runbook chỉ đi tiếp khi toàn bộ điều kiện sau đạt:

```powershell
git rev-parse HEAD
git status --short
python --version
python -m compileall -q src
python -m ruff check src tests
python -m mypy src
python -m pytest -q --strict-markers
```

BẮT BUỘC:
- HEAD là commit/handoff đã được duyệt cho WP07.
- Không có tracked deletion hoặc tracked diff ngoài phạm vi handoff.
- Python thuộc matrix đã duyệt `3.11` hoặc `3.13`.
- Test bắt buộc fail=0, error=0, skip=0, xfail/xpass=0.
- `TESTING-ACCEPTANCE` G00–G11 và G13 phải đạt trước rollout rehearsal.
- Không cần API key/provider thật để pass gate.

Nếu thiếu dependency/browser ⇒ fail setup; không skip.

## 4. Hai loại rollout hợp lệ

### 4.1. Fresh rollout từ v1.0 không có SQLite DB

Đây là đường mặc định của repo base: v1.0 dùng dictionary process-local, **không có persistent DB để backup**.

1. Dừng mọi process v1.0.
2. Xác nhận target DB chưa tồn tại.
3. Nếu người vận hành có một snapshot legacy **đã được cung cấp từ bên ngoài và đã xác thực**, truyền `--legacy-json`; nếu không, migration dùng tracked seed.
4. Chạy:

```powershell
python -m src.cyber_ops.manage migrate --db data/cyber_ops.db --json
python -m src.cyber_ops.manage inspect --db data/cyber_ops.db --json
```

5. Kỳ vọng tối thiểu seed:
   - `schema_version=1`
   - machines=32, members=2, menu_items=8
   - bookings=3, active_bookings=3
   - booking_seats=3, active_seats=3
   - integrity=`ok`, foreign_key_errors=0
6. Provision PIN local cho member cần demo bằng `member-pin`.
7. Start web:
   `python src/web_server.py 8080`
8. Smoke `/api/v1/health`, login, read pcs/menu; mutation smoke dùng DB disposable hoặc tài khoản/test data theo acceptance, không dùng production-like local data.

**Không tuyên bố bảo toàn mutation in-memory v1.0.** Mutation của process cũ vốn không durable; hồ sơ này chỉ migrate tracked seed hoặc snapshot legacy đã có nguồn gốc/định dạng hợp lệ.

### 4.2. Rollout khi đã có SQLite schema v1

Áp dụng cho rehearsal, rerun hoặc máy đã chạy pre-release 1.1.0:

1. Stop writers.
2. `inspect --db DB --json`; schema phải =1 và checksum migration khớp.
3. `backup --db DB --out-dir BACKUP --json`.
4. `verify-backup --backup-dir BACKUP --json`.
5. Chỉ sau verify mới chạy `migrate` (kỳ vọng no-op `applied=[]` nếu schema đã đúng).
6. Start app và chạy smoke.
7. Giữ backup đến khi G12/G14 sign-off.

Schema `>1`, table lạ ở v0 hoặc checksum sai ⇒ dừng; không sửa `user_version` bằng tay.

## 5. Start/stop local

### 5.1. Web

```text
python src/web_server.py 8080
```

BẮT BUỘC:
- host mặc định `127.0.0.1`;
- health báo app `1.1.0`, schema `1`, database `ok`;
- CORS/Origin/Host theo P02;
- một Uvicorn worker trong hồ sơ này.

Shutdown phải ngừng nhận request mới, đóng WebSocket, dispatcher/outbox loop, repository connection và provider client nếu có.

### 5.2. MCP stdio

Launcher lấy token session hợp lệ từ môi trường process:

```text
CYBER_SESSION_TOKEN=<secret-in-process-environment>
python -m src.mcp_server --stdio
```

CẤM echo token vào transcript/evidence. Read tools có thể chạy không token; mutation thiếu token trả structured `UNAUTHENTICATED`.

### 5.3. PIN/session

Seed member có PIN `NULL`; login chỉ dùng được sau khi người vận hành provision PIN. Không có PIN mặc định. Session tuyệt đối 8 giờ; restart không được tự phát sinh session “admin”.

## 6. Rollback matrix

| Thời điểm lỗi | Hành động bắt buộc | CẤM |
| :-- | :-- | :-- |
| Trước tạo DB fresh | Sửa code/config, chưa có data action | Tạo file DB giả để “đủ backup” |
| Fresh migrate lỗi | Giữ/quarantine file lỗi nếu có; sửa nguyên nhân; target mới phải migrate lại sạch | Sửa DDL/user_version tay |
| Có DB cũ và migrate/smoke lỗi trước mutation mới | Stop app; giữ DB failed dưới tên quarantine; restore verified backup vào target trống; verify manifest | Overwrite target trực tiếp |
| Sau khi 1.1.0 đã commit mutation mới | Stop writes; snapshot DB hiện tại; thu evidence; ưu tiên forward-fix hoặc quyết định người | Restore backup cũ làm mất mutation mới |
| Chỉ web/MCP adapter lỗi, domain/data đúng | Có thể revert adapter code tương thích sau test, giữ DB | Downgrade schema để chữa adapter |
| Checksum/schema mismatch | Dừng startup/rollout và chuyển architect | “Fix” bằng PRAGMA user_version thủ công |

### 6.1. Quarantine failed DB

Không delete. Đổi tên:
`data/cyber_ops.db.failed-<UTC timestamp>-<shortsha>` sau khi stop writers.

Ghi SHA + manifest của file failed vào evidence; không commit database binary.

### 6.2. Rehearsal G12

G12 không giả định v1.0 có DB. Rehearsal phải chứng minh **cả hai nhánh**:

- **R12-A existing DB:** tạo disposable schema-v1 DB có ít nhất một booking/order ngoài seed → backup → thay đổi disposable DB → quarantine → restore backup → manifest/SHA/count khớp.
- **R12-B fresh migration:** target absent → migrate → fault-injection trước COMMIT → không có schema nửa vời; rerun sạch ạn lạn trạo đúng seed/count.
- Sau khi chứng minh R12-A/B, output machine evidence mới cho phép G12 chuyển ✅.

## 7. Sự cố và error taxonomy vận hành

| Code | Điều kiện | Hành vi bắt buộc |
| :-- | :-- | :-- |
| `MIGRATION_CHECKSUM_MISMATCH` | schema version đúng nhưng SQL checksum khác | Dừng, không chạy app/migration tiếp |
| `UNSUPPORTED_SCHEMA` | user_version >1 hoặc v0 có table lạ | Dừng, giữ file, chuyển architect |
| `LEGACY_IMPORT_INVALID` | snapshot legacy sai schema/owner/count | Giữ target không đổi; sửa snapshot có nguồn gốc |
| `BACKUP_VERIFY_FAILED` | hash/integrity/FK/count sai | Không migrate/restore từ backup đó |
| `RESTORE_TARGET_EXISTS` | target restore đã tồn tại | Dừng; quarantine/đổi target bằng bước tường minh |
| `POST_UPGRADE_DATA_PRESENT` | rollback yêu cầu restore backup nhưng DB hiện có mutation mới | Dừng destructive rollback; cần quyết định người |
| `LOCAL_SMOKE_FAILED` | health/auth/read/realtime lỗi | Stop rollout; chọn rollback branch phù hợp thời điểm data |
| `DB_BUSY` | writer không dừng hoặc lock >5s | Dừng writer, retry hữu hạn; không kill/replace DB mù |

## 8. Evidence vận hành

Machine output, không sửa tay:

```text
planning/01_2026-09-15_cyber-ops-v2/evidence/operations/
├── preflight.txt
├── fresh-migrate.json
├── fresh-manifest.json
├── existing-pre-manifest.json
├── backup-result.json
├── backup-verify.json
├── rollback-existing.json
├── rollback-restored-manifest.json
├── rollback-fresh-fault.txt
├── smoke.json
└── sha256.txt
```

Evidence không chứa DB binary, PIN, token, cookie, Authorization, raw prompt hoặc raw thought.

## 9. Vùng cấm

- CẤM production deploy trong Plan 01.
- CẤM `0.0.0.0`, CORS `*`, debug server public.
- CẤM copy SQLite `.db` trần khi WAL writer còn chạy.
- CẤM xóa/quá ghi database lỗi hoặc backup.
- CẤM restore backup cũ sau mutation mới mà không có quyết định người.
- CẤM “backup” giả khi fresh v1.0 không có DB.
- CẤM hứa migrate mutation in-memory v1.0 không có snapshot nguồn.
- CẤM commit runtime DB, backup binary, token hoặc PIN.
