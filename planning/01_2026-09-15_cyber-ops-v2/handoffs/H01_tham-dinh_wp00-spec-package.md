1. Bạn là worker của repo này. Vai + luật hành xử: đọc `.agents/skills/vai-thi-cong/SKILL.md` (chưa có ⇒ bước 2 sẽ sinh ra). Loại handoff: THẨM ĐỊNH.
2. Bước 0 (worker ở REPO HẠ NGUỒN, đường kênh phát hành — `#24`): `node ../brain4agent.release/.agents/skills/.xay-dung-nao-bo/scripts/init_brain.js --check`. Worker ở TRONG CHÍNH hub (dogfood, Đ6 `#24`) thay bằng `node .agents/skills/.xay-dung-nao-bo/scripts/init_brain.js --check` — KHÔNG có `../brain4agent.release/`. **THẨM ĐỊNH: DỪNG ở `--check`** — ghi mã thoát vào report rồi đi tiếp; **CẤM chạy chế độ GHI**. Mã 2 ⇒ dừng, báo.
3. Đọc theo thứ tự: `planning/01_2026-09-15_cyber-ops-v2/plan.md` §2 → `specs/00-ARCHITECTURE.md` → `specs/01-CONTRACTS.md` → toàn bộ SPEC được nêu ở mục 3 dưới đây. Không đọc gì khác trước khi ghi dòng "hiểu việc".

1. BỐI CẢNH: Repo `tuanank2112-crypto/K4B-Day03-LeNhuY-2A202602715`, Plan 01 target 1.1.0. Tự đo `Base` bằng `git rev-parse HEAD` ngay trước phép đo đầu; CẤM dùng SHA ghim sẵn làm Base report.
2. PHẠM VI: CHỈ ĐỌC + chạy lệnh đo. Được ghi đúng `reports/R01_tham-dinh_wp00-spec-package.md` và `evidence/wp00-spec-audit/*.txt`. CẤM sửa plan/spec/source/brain; được tạo bản sao tạm ngoài repo để phá thử.
3. VIỆC PHẢI LÀM:
   - Chạy `python tools/brain_dossier_check.py planning/01_2026-09-15_cyber-ops-v2 --phase dispatch > planning/01_2026-09-15_cyber-ops-v2/evidence/wp00-spec-audit/dossier.txt`; xong khi exit 0 và stdout có `ok:true`.
   - So `git diff --stat` với phạm vi; xong khi không có file mã/app ngoài phạm vi do chính auditor tạo.
   - Tự thiết kế ≥3 cách phá KHÁC nhau trên bản sao tạm: tối thiểu broken router, evidence extension khác `.txt`, và trạng thái ready/G00 xanh khi thiếu approved R/evidence. Xong khi mỗi mutant làm checker đỏ; redirect kết quả vào `attacks.txt`.
   - Rà logic không-thể-đạt: mọi gate WP00 phải chạy được trước WP01; không helper thuộc WP06. Xong khi số circular dependency = 0, ghi vào `circular-gates.txt`.
   - Nộp report theo HANDOFF_PROTOCOL §7/§14; dòng cuối khi worker nộp là `⏳ Chờ người duyệt.`.
4. LUẬT: không `git add -A` · không push · không sửa plan/spec/source · không tự phán `✅` · evidence chỉ `.txt` và là output máy · lệnh dài chạy foreground · Base tự đo · SPEC mâu thuẫn ⇒ báo, không tự chọn nghĩa.
5. BẢNG GÓI VIỆC → TẦNG:
   | Gói | Tầng | Vì sao |
   | :-- | :--: | :-- |
   | WP00 dossier/spec audit | 🔴 | Cổng kiến trúc + contract trước khi cho phép thi công |
6. REPORT PHẢI CÓ: dòng 1 khai vai; dòng 2 `Handoff:`; dòng 3 `Base:`; dòng 4 `Head:`; lệnh+exit; test/count; diff-stat; bảng phân công; việc không làm; câu hỏi mở; link tới mọi evidence; dòng cuối `⏳ Chờ người duyệt.`.
7. DÒNG CUỐI: Report: `planning/01_2026-09-15_cyber-ops-v2/reports/R01_tham-dinh_wp00-spec-package.md` · Evidence: `planning/01_2026-09-15_cyber-ops-v2/evidence/wp00-spec-audit/dossier.txt`
