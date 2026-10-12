# Blueprint CI/CD cho RAG và guardrails

Nhóm: The Fellowship of the Ring (K4 Track 3A).

Người phụ trách PR dự kiến: MAI PHAN ANH TÙNG — 2A202602980.

Đây là đề xuất CI/CD, không phải workflow production đã triển khai. Các kết quả
dưới đây lấy từ artifact live và chỉ mô tả bộ fixture lab.

## Kiến trúc và hành động khi lỗi

Luồng đề xuất: input → Presidio PII scan → NeMo input rails → retrieval/rerank
→ generation → NeMo output rails → response. Request dừng nếu phát hiện PII
hoặc input rail kích hoạt; output rail chặn thì thay answer bằng refusal, còn
output an toàn được giữ nguyên. Log nên lưu request id, loại rail, quyết định và
thời lượng; redact PII trước khi lưu văn bản. API key chỉ nằm trong biến môi
trường/secret store, không ghi vào log hoặc artifact.

Nếu Presidio hoặc NeMo không khởi tạo được, đề xuất fail closed cho request
nhạy cảm và phát cảnh báo vận hành, không âm thầm bỏ qua lớp bảo vệ. Fallback
answer cần thiết kế riêng và đánh giá lại. Đây là policy đề xuất, chưa được thử
trong production.

## Kết quả live và phạm vi latency

Phase C live đo `input_layers_sequential`: Presidio và NeMo input chạy tuần tự,
không short-circuit; engines được khởi tạo trước đo; có 2 warm-up thật và 20
timed samples; percentile nội suy tuyến tính. Artifact cuối được tạo lúc
`2026-10-12T14:41:19.218279+00:00` UTC với Presidio entity scope và NeMo
self-check prompt đã cập nhật. Kết quả của lượt này:

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---:|---:|---:|---|
| Presidio | 3.911 | 5.416 | 6.835 | Đo live |
| NeMo input | 797.666 | 875.039 | 994.594 | Đo live |
| Input guard tuần tự | 802.917 | 878.623 | 998.516 | Vượt target P95 500 ms |
| RAG | Chưa đo | Chưa đo | Chưa đo | Ngoài Task 12 |
| NeMo output | Chưa đo | Chưa đo | Chưa đo | Ngoài Task 12 |
| Full guard / request | Chưa đo | Chưa đo | Chưa đo | Không suy từ input_guard_ms |

Không đưa input_guard_ms ra làm latency toàn request. Để đo RAG/output/full
request trong tương lai, thêm timestamp quanh từng stage, giữ riêng cold-start
và warm requests, ghi raw samples cùng số warm-up và báo p50/p95/p99.

### Quan sát quality Phase C và giới hạn lượt chạy

Artifact cuối ghi nhận 20/20 adversarial input bị block (100%), 8/8 clean
control được allow (false-positive rate 0%) và 4/4 output cases đạt. Vì vậy
Task 10 đạt và điều kiện bonus Phase C (≥18/20 attacks cùng 8/8 clean) đạt
(+3). Kết quả này đến sau khi giới hạn Presidio vào entity PII phù hợp và bổ
sung ví dụ rõ trong NeMo self-check cho câu hỏi policy v2.0, thơ và phim.

Lượt trước chỉ đạt 18/20 attacks, 7/8 clean; audit cho thấy recognizer English
`PERSON` gán cụm tiếng Việt thường thành tên người, còn `US_DRIVER_LICENSE` nhận
nhầm chuỗi `v2024`. Chỉnh sửa Presidio và prompt được đánh giá lại trong
artifact cuối ở trên. Không thay số liệu giữa các lượt; giữ artifact cuối làm
bằng chứng cho source/config hiện tại.

## Kết quả Phase A/B làm baseline

| Chỉ số | Kết quả live | Diễn giải |
|---|---:|---|
| RAGAS factual mean | 0.8407 | 20 câu |
| RAGAS multi_hop mean | 0.6834 | Thấp nhất trong ba nhóm |
| RAGAS adversarial mean | 0.7754 | Thấp hơn factual; điều kiện số liệu bonus A đạt |
| Dominant worst metric | answer_relevancy, 22/50 | Matrix từ tất cả câu |
| Judge position instability | 1/5 = 20% | Một cặp đổi kết quả khi swap |
| Judge verbosity rate | 4/4 = 100% | Mọi cặp decisive đều chọn answer dài hơn |
| Cohen’s κ | 1.00 trên 10 nhãn | Bonus B đạt; mẫu nhỏ, không đại diện tổng quát |

## CI gates đề xuất

- Kiểm schema, input hashes, số hàng và model provenance trước khi đọc quality
  score.
- Theo dõi 50 câu cố định với faithfulness ≥0.75 và avg_score ≥0.65; chỉ bật
  gate sau khi baseline ổn định và đã review false failures.
- Yêu cầu tối thiểu 15/20 attacks và 8/8 clean controls theo rubric lab; theo
  dõi riêng mục tiêu bonus ≥18/20 attacks.
- Báo riêng input-layer P95 và chỉ đặt gate sau khi target có căn cứ; đo vượt
  500 ms thì báo đúng kết quả thay vì điều chỉnh số liệu.
- Cảnh báo stale source hashes, missing artifact, regression so với baseline,
  clean request bị chặn và tỷ lệ judge disagreement tăng.

Workflow CI chưa được tạo hoặc chạy. Các ngưỡng trên là đề xuất; runner hiện
kiểm schema và provenance, không tự áp dụng các ngưỡng faithfulness, avg_score
hoặc mục tiêu bonus.

## Monitoring và cải tiến

Theo dõi RAGAS theo distribution, các dòng bottom 10, disagreement sau swap,
κ trên đúng bộ nhãn, attack pass rate, clean false-positive rate, output block
rate và latency mỗi tầng. Cải tiến Phase A bằng việc xử lý câu multi-hop thiếu
answer và giữ đủ mệnh đề. Phase B cần review verbosity bias 100% trên bốn kết
quả quyết định. Phase C đạt bộ fixture sau khi cập nhật entity scope và prompt;
latency vẫn vượt target nên cần profiling NeMo trước khi đặt latency gate. Bộ
lab chỉ có 50/20/8/4 mẫu nên chỉ phát hiện regression rõ, không đại diện traffic
production.
