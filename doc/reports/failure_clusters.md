# Phân tích lỗi Phase A

Nhóm: The Fellowship of the Ring (K4 Track 3A).

Người phụ trách PR dự kiến: NGUYỄN VŨ QUANG ANH — 2A202602805.

## Bằng chứng và provenance

Đã đánh giá 50 câu từ `artifacts/answers_50q.json` hiện có; không tạo lại
answers. Artifact live `artifacts/ragas_50q.json` được tạo lúc
`2026-10-12T14:31:26.668885+00:00` (UTC), có đủ 50 hàng và bốn metric hữu hạn
trong [0,1]. Generation model trong answers là `gpt-4o-mini-2024-07-18`;
RAGAS evaluator ghi nhận `gpt-4o-mini-2024-07-18` và
`text-embedding-3-small`. SHA-256 của answers và test set trong artifact khớp
nguồn hiện tại.

## Điểm trung bình theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---:|---:|---:|
| faithfulness | 0.9000 | 0.4329 | 0.8500 |
| answer_relevancy | 0.6501 | 0.5257 | 0.6516 |
| context_precision | 0.9125 | 0.9542 | 0.9167 |
| context_recall | 0.9000 | 0.8208 | 0.6833 |
| avg_score | 0.8407 | 0.6834 | 0.7754 |

`multi_hop` нь хамгийн сул distribution бөгөөд mean `avg_score` нь 0.6834.
Adversarial mean 0.7754 бага factual mean 0.8407, nên điều kiện số liệu cho
bonus Phase A (+4) đạt. Chênh lệch này chỉ cho thấy bộ adversarial khó hơn;
nó không chứng minh pipeline phát hiện đúng version conflict hoặc phủ định.

## Bottom 10 và chẩn đoán theo câu

Các hàng dưới xếp theo `avg_score` tăng dần; `worst_metric` và diagnosis gốc
được giữ nguyên trong JSON. Đối chiếu nội dung answer/context/reference cho thấy
diagnosis tự động `LLM hallucinating` không đúng với các câu trả lời
`Không tìm thấy.`; các trường hợp đó là bỏ trả lời dù context chứa dữ kiện.

| Rank / ID | Distribution, mean, metric yếu nhất | Answer và bằng chứng | Hướng xử lý |
|---|---|---|---|
| 1 / 21 | multi_hop, 0.2500, faithfulness | `Không tìm thấy.` Context có phép tính 15 ngày cơ bản + 3 ngày thâm niên và dải lương Senior 20–35 triệu; reference là 18 ngày và dải lương đó. | Giữ đúng context theo phiên bản, rồi trả lời đủ cả phép tính phép năm và lương; phân biệt abstention với hallucination trong chẩn đoán. |
| 2 / 33 | multi_hop, 0.3333, faithfulness | `Không tìm thấy.` Context/reference nêu phụ cấp tháng 1.500.000 đồng và 19 ngày phép v2024 cho 12 năm thâm niên. | Tách phép tính phụ cấp và phép năm thành các bước, kiểm tra mỗi phần với nguồn. |
| 3 / 39 | multi_hop, 0.3750, faithfulness | `Không tìm thấy.` Context có policy mật khẩu cũ và v2.0; reference nêu 8/90 ngày/không MFA so với 12/120 ngày/MFA bắt buộc. | Ưu tiên phiên bản hiện hành nhưng giữ dữ kiện cũ để so sánh; nêu rõ thời hạn và phạm vi MFA. |
| 4 / 50 | adversarial, 0.4167, faithfulness | `Không tìm thấy.` Hỏi dùng NordVPN cá nhân; reference nói policy v1.3 cấm VPN cá nhân và yêu cầu WireGuard công ty. | Trả lời rõ “không”, dẫn policy hiện hành và chỉ ra bẫy đề xuất nghe hợp lý nhưng bị cấm. |
| 5 / 6 | factual, 0.4873, faithfulness | Answer nói lương là dữ liệu “Bí mật”; reference bổ sung cấp 3, cấm chia sẻ, mã hóa và need-to-know. | Thêm các hạn chế bắt buộc nếu được hỏi về phân loại dữ liệu; kiểm tra vì sao faithfulness thấp với câu trả lời khớp một phần. |
| 6 / 29 | multi_hop, 0.5000, faithfulness | `Không tìm thấy.` Reference cần cấp phê duyệt khoản tạm ứng 8 triệu và tính phí quá hạn 80.000 đồng; context có công thức 2%/tháng. | Trả lời cả người phê duyệt và phép tính theo số ngày quá hạn; thêm kiểm thử phép tính nhiều nguồn. |
| 7 / 31 | multi_hop, 0.5340, faithfulness | Answer tính đúng mức 2.400.000 đồng cho 2 đêm; reference còn nêu phần vượt 300.000 đồng/đêm do nhân viên tự trả. | Bổ sung điều kiện phần vượt. Điểm thấp dù phép tính chính khớp reference cho thấy cần kiểm tra scoring và context boundary. |
| 8 / 40 | multi_hop, 0.5901, faithfulness | Answer nêu báo cáo trong 1 giờ nhưng bị cắt giữa câu; reference còn phương thức báo cáo và các hành vi không được làm. | Bảo đảm câu trả lời hoàn chỉnh, gồm việc cần làm và điều cấm; kiểm tra giới hạn output. |
| 9 / 38 | multi_hop, 0.5979, faithfulness | Answer tính đúng 200 USD × 3 đêm = 600 USD; reference xác nhận mức tối đa đúng 200 USD/đêm. | Đối chiếu metric với context và lưu ý kết quả thấp chưa đồng nghĩa phép tính sai. |
| 10 / 7 | factual, 0.5990, answer_relevancy | Answer xác định CEO là người duyệt 20 ngày nghỉ không lương; reference khớp và có thêm lưu ý tự đóng bảo hiểm khi nghỉ trên 14 ngày. | Giữ câu trả lời trực tiếp; cân nhắc thêm lưu ý liên quan mà không làm lệch câu hỏi. |

## Matrix worst-metric × distribution

| Metric yếu nhất | factual | multi_hop | adversarial | Tổng |
|---|---:|---:|---:|---:|
| faithfulness | 2 | 15 | 2 | 19 |
| answer_relevancy | 15 | 5 | 2 | 22 |
| context_precision | 2 | 0 | 1 | 3 |
| context_recall | 1 | 0 | 5 | 6 |
| Tổng | 20 | 20 | 10 | 50 |

`answer_relevancy` xuất hiện nhiều nhất là metric thấp nhất của 22 câu; tuy
nhiên `faithfulness` có mean thấp rõ ở multi-hop (0.4329) và là điểm yếu gắn
với phần lớn các câu khó. Ưu tiên cải thiện trả lời câu hỏi nhiều bước và giữ
đủ mệnh đề; sau đó review các câu có điểm thấp nhưng câu trả lời khớp reference
để phân biệt lỗi pipeline với giới hạn metric. Không thay answers hoặc scores
để cải thiện báo cáo.

## Bẫy adversarial và giới hạn

Trong id 50, câu hỏi gợi ý VPN cá nhân để tăng bảo mật nhưng policy v1.3 cấm
NordVPN/ExpressVPN và yêu cầu WireGuard của công ty; pipeline abstain thay vì
nêu mâu thuẫn chính sách. Mean adversarial thấp hơn factual nên điều kiện bonus
đạt về mặt số học, nhưng ví dụ này cho thấy điểm thấp không đồng nghĩa phát
hiện đúng bẫy. Cần đo riêng tỷ lệ trả lời đúng “không” và trích đúng policy ở
một lượt đánh giá tiếp theo.
