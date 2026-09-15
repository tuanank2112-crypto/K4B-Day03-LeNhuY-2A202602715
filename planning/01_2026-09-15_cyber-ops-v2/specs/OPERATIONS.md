# OPERATIONS — Local Rollout, Backup, Rollback and Runbook

## 1. Phạm vi và bất biến

Tệp này sở hữu contract vận hành cho Plan 01 / target `1.1.0`. Chỉ áp dụng cho **local rollout** theo Đ10; production deploy, TLS public, reverse proxy, multi-node và production secrets nằm ngoài scope.

Nguồn contract theo thứ tự: `00-ARCHITECTURE.md` → `01-CONTRACTS.md` → P01/P02/P03/P04 → tệp này → `TESTING-ACCEPTANCE.md`.

BẮT BUỘC:
1. HTTP/WebSocket mặc định bind `127.0.0.1:8080`; cấm `0.0.0.0` trong Plan 01.
2. SQLite runtime dùng schema `PRAGMA user_version=1`, FK ON, WAL, `busy_timeout=5000`, `synchronous=FULL`.
3. Stop writers trước migration, restore hoặc database swap.
4. Không delete/overwrite database lỗi; quarantine để điều tra.
5. Backup/restore chỉ hợp lệ sau SHA-256 + `integrity_check` + `foreign_key_check` + manifest counts.
6. Không destructive downgrade. Sau mutation mới của 1.1.0, restore backup cũ cần quyết định người; mặc định ưu tiên forward-fix.
7. Evidence không chứa PIN/token/cookie/Authorization/Idempotency-Key/raw prompt/raw thought.
8. Acceptance rehearsal dùng database disposable, không chạm dữ liệu local của người dùng.

## 2. CLI vận hành bắt buộc

WP01/WP07 phải hiện thực:

```text
python -m src.cyber_ops.manage inspect --db <PATH> --json
python -m src.cyber_ops.manage migrate --db <PATH> [--legacy-json <PATH>] --json
python -m src.cyber_ops.manage backup --db <PATH> --out-dir <DIR> --json
python -m src.cyber_ops.manage verify-backup --backup-dir <DIR> --json
python -m src.cyber_ops.manage restore --backup-dir <DIR> --target <PATH> --json
python -m src.cyber_ops.manage member-pin --db <PATH> --member <MemberId>
```

Stdout của lệnh có `--json` là đúng một JSON object UTF-8; diagnostic ra stderr. `member-pin` đọc PIN hai lần bằng `getpass`; cấm `--pin`, env PIN hoặc ghi PIN/hash/salt ra stdout.

Exit code:
- `0`: thành công.
- `2`: usage/config/input không hợp lệ.
- `3`: schema/migration safety failure.
- `4`: backup/restore verification failure.
- `5`: integrity/health/smoke failure.

Cấm exit `0` kèm `status=ERROR`.

### 2.1. DatabaseManifest

```text
DatabaseManifest(
  schema_version:int,
  file_sha256:str,
  file_bytes:int,
  integrity:Literal["ok"],
  foreign_key_errors:int,
  counts:{
    members:int,machines:int,bookings:int,active_bookings:int,
    booking_seats:int,active_seats:int,menu_items:int,food_orders:int,
    sessions:int,idempotency_records:int,outbox_events:int
  },
  max_outbox_seq:int
)
```

Manifest không chứa row business, owner, token, PIN hoặc trace.

## 3. Backup và restore contract

### 3.1. Backup

`backup --db DB --out-dir DIR`:
- Từ chối nếu `DIR` đã tồn tại hoặc DB không pass integrity.
- Dùng SQLite backup API hoặc snapshot nhất quán; cấm copy file `.db` trần khi WAL writer còn hoạt động.
- Tạo đúng `DIR/database.sqlite3` và `DIR/manifest.json`.
- Manifest chứa SHA-256 của file backup.
- `verify-backup` mở chính file backup, kiểm SHA/integrity/FK/counts.
- Verify fail → `BACKUP_VERIFY_FAILED`, exit 4; không migrate/restore từ backup đó.

### 3.2. Restore

`restore --backup-dir DIR --target PATH`:
- Backup phải pass `verify-backup`.
- `PATH` phải chưa tồn tại; cấm `--force`/overwrite trong 1.1.0.
- Restore ra file tạm cùng filesystem, fsync, verify manifest, rồi atomic rename.
- Sau restore, `inspect --db PATH` phải khớp schema/count/SHA của backup manifest.
- Target đã tồn tại → `RESTORE_TARGET_EXISTS`, exit 4.

## 4. Tiền kiểm rollout

```powershell
git rev-parse HEAD
git status --short
python --version
python -m compileall -q src
python -m ruff check src tests
python -m mypy src
python -m pytest -q --strict-markers
```

Chỉ đi tiếp khi:
- HEAD là commit/handoff đã duyệt.
- Không có tracked deletion/diff ngoài phạm vi.
- Python thuộc matrix 3.11 hoặc 3.13.
- fail/error/skip/xfail/xpass = 0.
- G00–G11 và G13 đã đạt trước rollout rehearsal.
- CI không cần live provider/API key.

Thiếu dependency/browser là setup failure, không skip.

## 5. Hai loại rollout hợp lệ

### 5.1. Fresh rollout từ v1.0

Đây là đường mặc định của repo base: v1.0 dùng dictionary process-local và **không có persistent DB để backup**.

1. Stop toàn bộ process v1.0.
2. Xác nhận target DB chưa tồn tại.
3. Nếu operator có snapshot legacy ngoài tiến trình đã được xác thực theo P04 thì truyền `--legacy-json`; nếu không, dùng tracked seed.
4. Chạy:

```powershell
python -m src.cyber_ops.manage migrate --db data/cyber_ops.db --json
python -m src.cyber_ops.manage inspect --db data/cyber_ops.db --json
```

5. Seed tối thiểu phải cho schema 1, machines=32, members=2, menu_items=8, bookings=3, active_seats=3, integrity=`ok`, FK errors=0.
6. Provision PIN local bằng `member-pin` cho member dùng demo.
7. Start web: `python src/web_server.py 8080`.
8. Smoke health/login/read; mutation smoke dùng DB disposable/test data.

**Không tuyên bố bảo toàn mutation in-memory v1.0.** Không có snapshot hợp lệ thì chỉ có tracked seed.

### 5.2. Rollout khi đã có SQLite schema v1

1. Stop writers.
2. `inspect --db DB --json`; schema phải =1 và migration checksum khớp.
3. `backup --db DB --out-dir BACKUP --json`.
4. `verify-backup --backup-dir BACKUP --json`.
5. Chỉ sau verify mới chạy `migrate`; schema đúng thì kỳ vọng no-op `applied=[]`.
6. Start app và chạy smoke.
7. Giữ backup đến G12/G14 sign-off.

Schema >1, v0 có table lạ hoặc checksum mismatch → dừng; cấm sửa `user_version` bằng tay.

## 6. Start/stop local

### Web

```text
python src/web_server.py 8080
```

Bắt buộc host local, health báo app `1.1.0` + schema 1 + database `ok`, CORS/Origin/Host theo P02, một Uvicorn worker. Shutdown phải đóng request intake, WebSocket, outbox dispatcher và repository/provider resources sạch.

### MCP stdio

```text
CYBER_SESSION_TOKEN=<secret-in-process-environment>
python -m src.mcp_server --stdio
```

Cấm echo token vào transcript/evidence. Read tools có thể chạy không token; mutation thiếu token trả structured `UNAUTHENTICATED`.

### PIN/session

Seed member có PIN `NULL`; không có PIN mặc định. Session tuyệt đối 8 giờ. Restart không tự sinh session admin.

## 7. Rollback matrix

| Thời điểm | Hành động bắt buộc | CẤM |
| :-- | :-- | :-- |
| Trước fresh DB | Sửa code/config; chưa có data action. | Tạo DB giả để “backup”. |
| Fresh migration lỗi | Quarantine file lỗi nếu có; sửa nguyên nhân; rerun vào target sạch. | Sửa DDL/user_version tay. |
| Existing DB rollout lỗi trước mutation mới | Stop app; quarantine failed DB; restore verified backup vào target trống; verify manifest. | Overwrite target trực tiếp. |
| Sau khi 1.1.0 đã commit mutation mới | Stop writes; snapshot DB hiện tại; thu evidence; forward-fix hoặc cần quyết định người. | Restore backup cũ làm mất mutation mới. |
| Chỉ adapter web/MCP lỗi, domain/data đúng | Có thể revert adapter code tương thích sau test; giữ DB. | Downgrade schema để chữa adapter. |
| Checksum/schema mismatch | Dừng startup/rollout và chuyển architect. | “Fix” bằng PRAGMA thủ công. |

Failed DB không delete; quarantine dạng `data/cyber_ops.db.failed-<UTC>-<shortsha>` sau khi stop writers. Ghi SHA + manifest vào evidence, không commit DB binary.

## 8. Rehearsal G12

G12 phải chứng minh cả hai nhánh:

- **R12-A existing DB:** tạo disposable schema-v1 DB có ít nhất một booking/order ngoài seed → backup → thay đổi DB → quarantine → restore backup → manifest/SHA/count khớp.
- **R12-B fresh migration:** target absent → fault injection trước COMMIT → không có schema nửa vời → rerun sạch tạo đúng seed/count.

Chỉ khi R12-A và R12-B đều có machine evidence mới chuyển G12 ✅.

## 9. Error taxonomy vận hành

| Code | Điều kiện | Hành vi |
| :-- | :-- | :-- |
| `MIGRATION_CHECKSUM_MISMATCH` | Version đúng nhưng SQL checksum khác. | Dừng; không migrate/start app. |
| `UNSUPPORTED_SCHEMA` | `user_version>1` hoặc v0 có table lạ. | Dừng, giữ file, chuyển architect. |
| `LEGACY_IMPORT_INVALID` | Snapshot legacy sai schema/owner/count. | Target không đổi; sửa snapshot có nguồn gốc. |
| `BACKUP_VERIFY_FAILED` | SHA/integrity/FK/count sai. | Không migrate/restore từ backup. |
| `RESTORE_TARGET_EXISTS` | Restore target đã tồn tại. | Dừng; quarantine/đổi target bằng bước tường minh. |
| `POST_UPGRADE_DATA_PRESENT` | Muốn restore backup cũ nhưng DB có mutation mới. | Dừng destructive rollback; cần quyết định người. |
| `LOCAL_SMOKE_FAILED` | Health/auth/read/realtime lỗi. | Stop rollout; chọn rollback branch theo thời điểm data. |
| `DB_BUSY` | Writer chưa dừng hoặc lock >5s. | Stop writer, retry hữu hạn; không kill/replace DB mù. |

## 10. Evidence

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

Evidence là output máy, không sửa tay; không chứa DB binary hoặc secret.

## 11. Vùng cấm

- CẤM production deploy trong Plan 01.
- CẤM `0.0.0.0`, CORS `*`, public debug server.
- CẤM copy SQLite `.db` trần khi WAL writer đang chạy.
- CẤM xóa/overwrite failed DB hoặc backup.
- CẤM restore backup cũ sau mutation mới nếu chưa có quyết định người.
- CẤM tạo “backup” giả khi fresh v1.0 không có DB.
- CẤM hứa migrate mutation in-memory v1.0 không có snapshot nguồn.
- CẤM commit runtime DB, backup binary, PIN hoặc token.
