# Quy trình bốn PR theo thứ tự

Nhóm dự kiến chuẩn bị đúng bốn PR tuần tự. Mỗi PR được tạo trên shared
repository thật sau khi PR trước được merge. Không dùng các thư mục snapshot như
repo Git hoặc lịch sử đóng góp đã hoàn thành.

| PR | Thành viên phụ trách | Phần việc dự kiến | Nhánh bắt đầu từ |
|---|---|---|---|
| 1 | NGUYỄN VŨ QUANG ANH — 2A202602805 | Phase A Tasks 1–4, m4 evaluator provenance, `ragas_50q.json` và report A | main hiện tại |
| 2 | VŨ ĐỨC MINH — 2A202602895 | Phase B Tasks 5–8, `judge_results.json`, calibration và bias report | main sau khi PR1 merge |
| 3 | NGUYỄN NGỌC VĨNH — 2A202602833 | Phase C Tasks 9a–12, `guard_results.json`, guardrails và latency | main sau khi PR2 merge |
| 4 | MAI PHAN ANH TÙNG — 2A202602980 | TEAM, blueprint, tích hợp và checker | main sau khi PR3 merge |

Để chuẩn bị từng PR, thành viên tạo branch trên repo nhóm thật, chép nội dung
của snapshot tương ứng lên branch hiện tại, xem lại toàn bộ diff, tự thực hiện
hoặc giải thích được đóng góp của mình, chạy kiểm tra rồi tạo commit và PR của
mình. Người tiếp theo dùng snapshot kế tiếp sau khi PR trước đã merge. Nếu có
xung đột với thay đổi nhóm khác, giải quyết trên branch PR hiện tại và ghi rõ
trong review.

Snapshot là bản sao working tree lũy tiến, không có `.git`, `.env`, virtualenv
hoặc cache. Vì vậy chúng không thể chứng minh ai đã commit/PR. Chỉ ghi tên người
thực hiện, link PR, commit SHA và ngày merge vào `doc/TEAM.md` sau khi bằng chứng
thật tồn tại.

Tình trạng bản local ngày 2026-10-12: source, báo cáo và artifact A/B/C live đã
được kiểm tra bằng `scripts/check_lab.py --with-tests`; checker pass, 116 offline
tests pass và 3 integration tests được bỏ qua. Kết quả Phase C đạt 20/20 attacks,
8/8 clean, 4/4 output cases; input guard P95 đo được là 878.623 ms, cao hơn target
500 ms. Các snapshot là working trees để tạo đúng bốn PR tuần tự; không thay thế
commit/PR và bằng chứng đóng góp thật của từng thành viên.
