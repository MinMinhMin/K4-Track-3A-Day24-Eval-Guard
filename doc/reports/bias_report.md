# Đánh giá LLM Judge Phase B

Nhóm: The Fellowship of the Ring (K4 Track 3A).

Người phụ trách PR dự kiến: VŨ ĐỨC MINH — 2A202602895.

## Bằng chứng và nguồn dữ liệu

Artifact live `artifacts/judge_results.json` được tạo lúc
`2026-10-12T14:32:40.781218+00:00` UTC, với judge model `gpt-4o-mini` và
generation model của answers `gpt-4o-mini-2024-07-18`. SHA-256 của answers,
test set và human labels khớp các file nguồn. Năm cặp dùng A từ pipeline answer,
B từ supplied `model_answer`, reference từ `ground_truth`; calibration dùng
đúng 10 supplied `model_answer` gốc. Prompt judge không nhận `human_label` hay
`human_note`.

## Pairwise judge: năm cặp, hai thứ tự

| Question ID | Winner lượt 1 | Winner lượt 2 sau map về A/B gốc | Kết quả cuối | Nhận xét |
|---:|---|---|---|---|
| 1 | B | B | B | Đáp án B nêu rõ kỳ nghỉ có lương. |
| 5 | A | A | A | CEO được xác định đúng cho thiết bị 55 triệu. |
| 12 | A | tie | tie | Bất đồng khi đảo thứ tự; hai câu đều đúng, một câu đầy đủ hơn. |
| 21 | B | B | B | Answer A là “Không tìm thấy”, B trả lời đúng hai ý. |
| 41 | A | A | A | Answer A gồm policy 2023 và 2024; B chỉ nêu mức cũ. |

Chỉ cặp 12 đổi quyết định sau khi hoán đổi thứ tự: 1/5 = 20% position
instability. Final winner theo quy tắc là tie ở cặp bất đồng. Lý do của lượt 2
được lưu nguyên theo nhãn trong thứ tự đã swap; winner và scores của lượt đó
được map về danh tính A/B ban đầu. Khi đọc reasoning lượt 2, cần diễn giải theo
thứ tự đã swap.

## Verbosity bias

| Chỉ số | Giá trị |
|---|---:|
| Cặp có kết quả quyết định | 4/5 |
| A thắng và A dài hơn | 2 |
| B thắng và B dài hơn | 2 |
| Winner dài hơn / cặp quyết định | 4/4 = 1.00 |

Theo định nghĩa của lab, cả bốn kết quả quyết định đều nghiêng về đáp án dài
hơn; đây là dấu hiệu verbosity đáng theo dõi, không chứng minh judge chọn sai
trong mọi cặp. Position instability thấp trong mẫu năm cặp, nhưng verbosity
rate cao. Cần review thủ công trên tập lớn hơn và bảo đảm prompt ưu tiên đúng,
đủ ý theo reference thay vì độ dài.

## Calibration với nhãn người

| Question IDs | Judge labels | Human labels | Observed agreement | Chance agreement | Cohen’s κ |
|---|---|---|---:|---:|---:|
| 1, 5, 12, 21, 23, 29, 33, 41, 46, 50 | 1, 0, 1, 1, 1, 0, 1, 0, 1, 0 | 1, 0, 1, 1, 1, 0, 1, 0, 1, 0 | 10/10 = 1.00 | 0.52 | 1.00 |

κ = (1.00 − 0.52) / (1 − 0.52) = 1.00. Điều kiện bonus Phase B (κ > 0.6)
đạt trên mười nhãn được cung cấp (+3). Mẫu nhỏ và kết quả hoàn hảo trên bộ này
không chứng minh độ tin cậy tổng quát; cần đánh giá trên câu mới, giữ nhãn người
ngoài prompt judge và kiểm tra các bất đồng theo từng loại câu.
