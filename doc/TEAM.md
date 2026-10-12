# The Fellowship of the Ring — K4 Track 3A

Tên nhóm chính thức: The Fellowship of the Ring.

Repo chung: thư mục local `K4-Track-3A-Day24-Eval-Guard`; URL remote chưa được
cung cấp.

Trưởng nhóm/người nộp: chưa được chỉ định.

Ngày cập nhật bản local: 2026-10-12, Asia/Ho_Chi_Minh (UTC+07:00). Ngày lab và
deadline chính thức cần đối chiếu thông báo lớp.

Commit dùng để chấm: `0dc21d20ec64c1d2bed1f47e38fb1bc77237392a` (nhánh `main`,
merge từ nhánh `tung`). Commit ghi SHA này vào TEAM được tạo sau đó nên không
nằm trong SHA trên.

## Thành viên và đóng góp (commit / PR thật)

| STT | Họ và tên | MSSV | Vai trò / công việc | Bằng chứng (commit / PR) |
|---|---|---|---|---|
| 1 | NGUYỄN VŨ QUANG ANH | 2A202602805 | PR1: Phase A (RAGAS) và evaluator provenance (`m4_eval.py`, `phase_a_ragas.py`), artifact `ragas_50q.json`, `failure_clusters.md` | Commit `2fa8afa` (nhánh `quanganh`), PR #1, merge `6d6b64a` |
| 2 | VŨ ĐỨC MINH | 2A202602895 | PR2: Phase B judge và calibration (`phase_b_judge.py`), artifact `judge_results.json`, `bias_report.md` | Commit `3afad9f` (nhánh `vuducminh`), PR #2, merge `034edc8` |
| 3 | NGUYỄN NGỌC VĨNH | 2A202602833 | PR3: Phase C guardrails và latency (`phase_c_guard.py`, `guardrails/config.yml`), artifact `guard_results.json` | Commit `4617642` (nhánh `nguyenngocvinh`), PR #3, merge `b39e087` |
| 4 | MAI PHAN ANH TÙNG | 2A202602980 | PR4: TEAM, blueprint và tích hợp (`TEAM.md`, `blueprint.md`, `PR_SEQUENCE.md`) | Commit `9342dca` (nhánh `tung`), merge trực tiếp `0dc21d2` vào `main`, commit ghi SHA `0519d01`; chưa mở PR #4 |

Nguồn: lịch sử Git của repo `MinMinhMin/K4-Track-3A-Day24-Eval-Guard`
(`git log --all`); số PR lấy từ tiêu đề các merge commit. Tên tác giả trên Git
của một số commit là tài khoản GitHub, không trùng họ tên trong bảng. Commit
`0dc21d2` là bản dùng để chấm, được merge từ nhánh `tung` mà không qua PR.

## Môi trường và chuẩn bị

- OS: Linux trong workspace; Python mặc định và `.venv` là 3.12.3. Hướng dẫn
  runtime của lab nhắm Python 3.11, nên khác biệt phiên bản này cần được nhóm
  xác nhận trước khi nộp.
- Virtualenv: `.venv` local đã có dependency; `pip check` đã pass trong kiểm tra
  môi trường trước đó. Không đưa virtualenv vào snapshot.
- Data: `artifacts/answers_50q.json` có sẵn, gồm 50 answers với phân bố 20/20/10;
  giữ nguyên, không chạy tạo lại answers.
- Dịch vụ: Docker không có container đang chạy ở lần kiểm tra môi trường.
- Live: Phase A/B/C đều có artifact live ngày 2026-10-12. A có đủ 50 câu;
  B có 5 cặp, 10 nhãn và κ=1.00. Lượt C cuối đạt 20/20 attacks, 8/8 clean,
  4/4 output cases và điều kiện bonus C; input-layer P95 878.623 ms, vượt target
  500 ms.
- Secrets: giá trị API key không được đưa vào mã, tài liệu hoặc snapshots.

## Hỗ trợ AI và cách kiểm chứng

AI (Codex) chỉ đóng vai trò công cụ hỗ trợ: gợi ý cấu trúc, tham khảo cách viết
code/test, rà soát lỗi và góp ý diễn đạt tài liệu. Mỗi thành viên tự thiết kế,
viết, chỉnh sửa và chịu trách nhiệm cho phần được giao; AI không thay thế việc
hiểu và làm bài của sinh viên.

Cách kiểm chứng đầu ra có sự hỗ trợ của AI:

- Đọc và hiểu từng đoạn code/tài liệu trước khi đưa vào bài; đoạn nào không giải
  thích được thì viết lại hoặc bỏ.
- Chạy unit tests offline (dùng mocks) và `scripts/check_lab.py`; tests offline
  không thay thế các lần chạy API/runtime thật.
- Đối chiếu báo cáo với artifact live (`artifacts/*.json`): input hashes, scores,
  nhãn, κ, bias, percentile latency.
- Lượt C cuối đạt bộ fixture nhưng input-layer P95 vượt target 500 ms; con số này
  được ghi đúng như đo được, không làm đẹp.
- Thành viên khác review chéo qua PR theo `doc/PR_SEQUENCE.md` trước khi merge.

## INDIVIDUAL

Các mục dưới ghi người phụ trách PR và bằng chứng commit/PR thật.
Từng thành viên cần tự bổ sung phần học được trước khi nhóm nộp; trải nghiệm cá nhân phải do chính thành viên viết.

### NGUYENVUQUANGANH-2A202602805

- Phần được giao: PR1, Phase A Tasks 1–4 và m4 evaluator provenance.
- Thực tế đã làm: thành viên tự thực hiện phần được giao; xem commit/PR trong bảng
  đóng góp.
- Bằng chứng: artifact Phase A live có 50 hàng, bốn metric và metadata model;
  report phân tích bottom 10, matrix và bonus theo JSON. Commit `2fa8afa`, PR #1.
- Cách kiểm tra: unit tests offline của Phase A/m4 và đối chiếu input hashes,
  scores, bottom 10 cùng matrix trong artifact.
- Điều đã học: thành viên tự ghi sau khi review và thực hiện phần việc.
- AI hỗ trợ: chỉ gợi ý và rà soát; thành viên tự viết code/tests và kiểm tra kết quả độc lập.

### VUDUCMINH-2A202602895

- Phần được giao: PR2, Phase B pairwise judge, swap-and-average, κ và
  bias report.
- Thực tế đã làm: thành viên tự thực hiện phần được giao; xem commit/PR trong bảng
  đóng góp.
- Bằng chứng: artifact Phase B live có 5 cặp, 10 binary judgments, κ=1.00,
  position instability 20% và verbosity rate 100% trên 4 kết quả quyết định. Commit `3afad9f`, PR #2.
- Cách kiểm tra: unit tests offline với mock, sau đó đối chiếu pair sources,
  label alignment và phép tính κ/bias trong artifact.
- Điều đã học: thành viên tự ghi sau khi review và thực hiện phần việc.
- AI hỗ trợ: chỉ gợi ý và rà soát; thành viên tự viết và xác nhận scoring/mapping.

### NGUYENNGOCVINH-2A202602833

- Phần được giao: PR3, Presidio, NeMo input/output rails, adversarial
  suite và latency.
- Thực tế đã làm: thành viên tự thực hiện phần được giao; xem commit/PR trong bảng
  đóng góp.
- Bằng chứng: artifact C cuối có 20/20 attacks, 8/8 clean controls, 4/4 output
  cases và 20 mẫu latency. Input P95 vượt target 500 ms. Commit `4617642`, PR #3.
- Cách kiểm tra: unit tests offline với fake engines/rails và đối chiếu từng
  fixture, output, warm-up, raw samples cùng percentile trong artifact.
- Điều đã học: thành viên tự ghi sau khi review và thực hiện phần việc.
- AI hỗ trợ: chỉ gợi ý và rà soát; thành viên tự viết và kiểm tra cấu hình/runtimes.

### MAIPHANANHTUNG-2A202602980

- Phần được giao: PR4, TEAM, blueprint, manifest và integration.
- Thực tế đã làm: thành viên tự thực hiện phần được giao; xem commit/PR trong bảng
  đóng góp.
- Bằng chứng: A/B/C artifacts và ba reports live đã có; Phase C đạt fixture. Commit `9342dca`, merge `0dc21d2`; chưa có PR #4.
- Cách kiểm tra: chạy checker cùng offline tests và đối chiếu báo cáo với JSON
  live sau khi các phase được phép chạy.
- Điều đã học: thành viên tự ghi sau khi review và thực hiện phần việc.
- AI hỗ trợ: chỉ gợi ý và góp ý diễn đạt; thành viên tự viết và xác nhận thông tin
  nhóm, đóng góp và kết quả đo thực tế.

## Cập nhật sau khi nộp

Chưa nộp link hoặc chọn commit. Khi có remote, commit, PR và quyết định của coach,
nhóm cần cập nhật phiên bản nộp cùng thời điểm; không khai báo trước một lần nộp
hay đóng góp chưa diễn ra.
