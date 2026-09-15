# Known Gotchas & Bugs

Tổng hợp các lỗi khó, các lưu ý dị biệt hoặc cách workaround đặc thù của dự án này để AI không dẫm lại vết xe đổ.

## Planning / Dossier governance

### Planning-ready bị nhầm với dispatch-ready
- Sự cố 2026-09-16: Plan 01 từng được ghi “SPEC ĐÃ DUYỆT — sẵn sàng thi công WP01” và G00=`✅` dù chưa có handoff thẩm định WP00, report, hoặc machine evidence.
- Nguyên nhân: áp dụng thiếu `brain4agent-release/docs/HANDOFF_PROTOCOL.md` §11–§14; `[📐 lập kế hoạch]` và `[🚀 phóng]` là hai mode khác nhau. WP00 lại là cổng 🔴 nên bắt buộc auditor độc lập trước phán quyết.
- Bẫy thứ hai: G00 từng gọi `tests.acceptance audit-specs`, nhưng helper đó chỉ được tạo ở WP06 ⇒ circular gate, WP00 không thể tự đạt.
- Bẫy thứ ba: protocol dossier chỉ cho evidence file `.txt`; nội dung JSON/JUnit vẫn phải ghi dưới filename `.txt` nếu nằm trong `planning/.../evidence/`.
- Chống tái diễn: trước mọi claim “sẵn sàng thi công”, gate 🔴 xanh hoặc đóng plan, chạy `python tools/brain_dossier_check.py <plan-dir> --phase planning|dispatch|ready|close`. Checker project-local chỉ là guardrail; HANDOFF_PROTOCOL ở hub vẫn là nguồn luật.
- Không tạo `reports/` hoặc `evidence/` giả/placeholder để GitHub hiện folder. Git không track folder rỗng; report/evidence chỉ sinh từ worker/auditor thật.

## Môi trường & Config
- Chưa có gotcha môi trường khác được xác nhận.
