# P04 — Quality, Migration and Release

## 1. Contract migration và cấu hình

```text
Migration(version: int, name: str, sql_path: Path, sha256: str)
migrate(db_path: Path, legacy_json: Path | None = None) -> MigrationReport
MigrationReport(schema_version: int, applied: list[int], seed: SeedReport,
                integrity: Literal['ok'], foreign_key_errors: int, source_sha256: str | None)
inspect_database(db_path: Path) -> DatabaseManifest
verify_manifest(db_path: Path, manifest: DatabaseManifest) -> VerificationResult
```

Schema version0 chỉ nghĩa file chưa tồn tại hoặc database thực sự trống. Version0 có table lạ → `UNSUPPORTED_SCHEMA`, không đoán cách import. Version1 cùng SHA migration001 → no-op; user_version>1 → `UNSUPPORTED_SCHEMA`; cùng version khác SHA → `MIGRATION_CHECKSUM_MISMATCH`. Migration tạo DDL+seed+schema_migration trong cùng transaction; failure rollback. DDL không dùng sqlite3.executescript theo cách implicit commit ngoài transaction: transaction boundaries phải được kiểm thử bằng fault injection.

`legacy_json` là input **optional do người vận hành cung cấp từ ngoài tiến trình v1.0**, chỉ import vào DB trống. Plan 01 không cung cấp hoặc cam kết một `manage export-legacy` có thể đọc mutation trong dictionary của process v1.0 đang chạy. Format chính xác `{format_version:1,source_base_sha:str,captured_at_ms:int,pcs:dict[str,LegacyPc]}`; LegacyPc gồm zone/specs/status/price_per_hour và optional booked_by/duration_hours/booking_id. Status enum4 giá trị cũ; row BOOKED phải có owner thuộc2 member seed, duration1–24 nếu có, thiếu dùng2; không nhận unknown keys. 32 pc IDs phải khớp seed, không lặng lẽ bỏ máy. Member/menu lấy seed tracked; snapshot không thể tái tạo order/history chưa từng được persist từ v1.0.

Import bảo toàn trạng thái/owner/giá/duration **chỉ trong snapshot legacy đã được cung cấp**; legacy booking_id cũ không unique nên tạo UUID5 từ SHA file + pc_id; không cố phục hồi grouping chưa tồn tại. Báo cáo source SHA và counts trong MigrationReport. Sai field/owner/schema → `LEGACY_IMPORT_INVALID`, giữ database đích không đổi. Không tự tạo member giả để thông qua validation. Không có snapshot hợp lệ ⇒ fresh migration dùng tracked seed; CẤM tuyên bố đã bảo toàn mutation in-memory cũ.

Dependency runtime thêm FastAPI/Uvicorn/MCP SDK và giữ provider dependencies còn dùng; resolver khóa versions thực trong `requirements.lock`; dev deps pytest/httpx/ruff/mypy/pytest-playwright trong `requirements-dev.txt` với pinned versions đã resolve. Không ghi số package chưa xác minh. Python hỗ trợ3.11–3.13, CI chạy3.11 và3.13. App version nguồn `src/cyber_ops/__init__.py::__version__='1.1.0'`, web/MCP health import từ đây. Không thêm package manifest không dùng chỉ để bump version.

## 2. Test và CI bắt buộc

BẮT BUỘC tạo `tests/` với unit/contract/integration/browser; `tests/conftest.py` cung cấp temp SQLite/session/clock deterministic; mỗi case riêng database, không dùng data local thật. CI không dùng provider thật hoặc API key; provider fake tái hiện native tool calls đúngTC01–TC05. Không patch CyberService trong test end-to-end/concurrency.

Lệnh contract (được WP06 hiện thực trước đóng gate):

```powershell
python -m compileall -q src
python -m ruff check src tests
python -m mypy src
python -m pytest -q --strict-markers --junitxml=planning/01_2026-09-15_cyber-ops-v2/evidence/quality/pytest-junit.txt
python -m playwright install chromium
python -m pytest -q -m browser --junitxml=planning/01_2026-09-15_cyber-ops-v2/evidence/quality/browser-junit.txt
python -m tests.acceptance verify-junit planning/01_2026-09-15_cyber-ops-v2/evidence/quality/pytest-junit.txt planning/01_2026-09-15_cyber-ops-v2/evidence/quality/browser-junit.txt
```

Pytest default toàn bộ tests bao gồm browser; lệnh browser riêng chỉ dùng evidence/tái hiện và không làm tăng giả tổng unique tests. Có thể CI chia suite bằng marker, nhưng phải union đầy đủ và báo unique collected count. `verify-junit` exit1 nếu failures/errors/skipped>0, count giảm so baseline cùng matrix, xfail/xpass hoặc thiếu report. Missing dependency/browser fail setup; CẤM importorskip/skipif và `continue-on-error` ở gate bắt buộc.

`.github/workflows/ci.yml` local-meaning CI: install khóa deps, compile/lint/typecheck, unit+contract+integration+concurrency+browser, verify evidence, upload artifact kể cả fail. Workflow không push/deploy, không production secrets. Cấu hình mypy/ruff nằm `pyproject.toml`; giới hạn suppressions theo dependency thật với lý do, không exclude module mới chỉ để xanh.

## 3. RED proof và compatibility

Trước sửa lỗi, đo atomicity/negative duration từ tracked base bằng reproducer tại TESTING-ACCEPTANCE §2. Sau khi có suite, bắt buộc chạy mutation harness tạm cố ý hỏng3 ranh giới: bỏ unique guard/serialize book; commit từng seat; bỏ ownership; thêm XSS sink và xóa outbox commit là2 trường hợp phụ bắt buộc ở WP05/WP08. Harness chạy ở copy/temp DB, restore sau mỗi mutant; không commit mutant. Mỗi mutant được nhắm ít nhất1 test phải fail (exit!=0) rồi code đúng cùng test pass; tổng phát hiện5/5.

TC01–TC05 dùng nguyên câu hỏi/ID/type trong config/test_cases.json; provider fake trả chuỗi tool tương ứng, qua coordinator+service thật. TC03 dùng VIP-08/NET2026/3h→54.000VND; TC04 read PRO_GAMING rồi book PRO-01/2h→50.000VND; TC05 VIP-999→NOT_FOUND legacy/PC_NOT_FOUND canonical và0 write. Fixture cấp token, không cần người nhập PIN trong CI. `--all` giữ completed5, không “TODO skip”; thiếu token exit2 là lỗi cấu hình đã công bố.

## 4. Đồng bộ tài liệu và version

| Tệp | Nội dung phải cập nhật tại WP07 |
| :-- | :-- |
| `docs/cyber_ops.md` | Module mới1-1: schema/service/CLI/API/auth/error/backup |
| `docs/trace_eval.md` | Phân biệt nội dung lab lịch sử với runtime mới,5 tools, demo an toàn |
| `README.md` | Setup local, member PIN/session, commands, test và compatibility changes |
| `brain4agent/index.md` | src/cyber_ops, tests, migrations, endpoints, router docs |
| `brain4agent/roadmap.md` | Active→Done chỉ khi mọi gate local đạt |
| `brain4agent/changelog.md` | Release1.1.0, migrations và behavior siết validation |
| `brain4agent/memory/hot/today.md`, `state.json` | Counts/SHA/evidence/path/state, không secret |
| `brain4agent/memory-distill.txt` | Stack thật + SQLite/API/MCP/realtime, dưới100 dòng |
| `brain4agent/project-intro.md`, `-data-architecture.md` | Rà FastAPI, SQLite, tests/data runtime top-level theo structural extension |
| `src/cyber_ops/__init__.py` và mọi config có version app | Đồng bộ1.1.0; không đổi brain_template_version |

Không cập nhật docs thành “đã pass” trước khi có evidence. Artifact runtime `data/`, logs/cache/browser downloads phải gitignore; committed evidence chỉ ở planning/.../evidence theo hồ sơ và mọi evidence file dùng đuôi `.txt` theo HANDOFF_PROTOCOL §14, kể cả nội dung JUnit/JSON. Không tạo tài liệu tạm ở root.

## 5. Error taxonomy và caller

| Lỗi | Caller bắt buộc |
| :-- | :-- |
| MIGRATION_CHECKSUM_MISMATCH / UNSUPPORTED_SCHEMA | Dừng startup, giữ file, không tự sửa user_version |
| LEGACY_IMPORT_INVALID | Trả lỗi field/ID an toàn, sửa snapshot có nguồn gốc; không bỏ row |
| BACKUP_VERIFY_FAILED | Không migrate/restore trên backup hỏng |
| TEST_FAILURE / TEST_SKIPPED / TEST_COUNT_DECREASE | Gate local chưa đạt; sửa hoặc giải trình contract trước tiến tiếp |
| MUTANT_SURVIVED | Sửa phép đo để làm đỏ, không công bố coverage thay bằng chứng |
| VERSION_MISMATCH / DOC_LINK_BROKEN | Sửa tài liệu/config trước sign-off |

## 6. BẮT BUỘC / CẤM và vùng cấm

BẮT BUỘC snapshot/checksum backup trước migration **khi đã có SQLite DB với dữ liệu**; rollback được diễn tập với DB disposable theo OPERATIONS R12-A/R12-B. Fresh rollout từ v1.0 không có DB thì không được tạo “backup” giả; migration dùng tracked seed hoặc snapshot legacy hợp lệ do operator cung cấp. CẤM destructive downgrade DDL; CẤM sửa migration001 đã phát hành; CẤM xóa test cũ hoặc skip live-provider cases để xanh (chuyển sang fake fixture có assertion rõ). CẤM chứng minh conformance bằng class alias nội bộ thay client MCP thật. CẤM đổi text config5 case để làm test dễ hơn. CẤM thêm endpoint/IPC export live state v1.0 trong Plan 01.

## 7. Số đo thật / nghiệm thu local

Base requirements.txt có7 dependency không khóa; src/app.py --all chạy5 case nhưng chỉ đếm completed, không assert nghiệp vụ. Probe atomicity và negative duration hiện thất bại theo TESTING-ACCEPTANCE. Chưa có test suite1.1.0 hoặc số test pass được tuyên bố.

Gate local yêu cầu: migrate32/2/8 và3 booking legacy; migrate lần2 applied=[]; checksum/count unchanged; kill giữa DDL/seed không để schema nửa vời; test fail0/skip0 trên3.11 và3.13; compatibility5/5, mutant killed5/5, docs/version link check exit0. Rollback G12 phải chứng minh riêng existing-DB backup/restore và fresh-migration fault recovery; không giả định v1.0 có persistent DB. Mọi kết quả phải có machine evidence riêng, không thay bằng câu “test xanh”.
