# Day 14 — Reflection

## Evaluation Report & Failure Analysis

Dùng kết quả thật trong `artifacts/benchmark_results.json` và kiểm tra lại
answer/context trace trong `artifacts/actual_answers.json` trước khi kết luận.

---

## 1. Benchmark Results Summary

**Overall pass rate:** 80.0%

| Metric | Average | Min | Max | Nhận xét |
|---|---:|---:|---:|---|
| Context Recall | 0.914 | 0.261 | 1.000 | Rất cao, hệ thống lấy đúng document. |
| Context Precision | 0.931 | 0.250 | 1.000 | Rất cao, các chunk đúng nằm ở top đầu. |
| Faithfulness | 0.662 | 0.000 | 1.000 | Thấp, LLM thường xuyên bịa ra thông tin. |
| Relevance | 0.705 | 0.455 | 0.917 | Khá thấp, hay trả lời lan man hoặc lạc đề. |
| Completeness | 0.774 | 0.174 | 1.000 | Trung bình khá, thi thoảng thiếu ý chính. |
| Overall Score | 0.797 | 0.258 | 0.931 | Kết quả tổng hợp chỉ ra chất lượng chỉ ở mức khá. |

**Score interpretation**

- Metrics/cases ở mức Good (0.8–1.0): E01, E02, E05, M02, M03, M04, M05, H02 (8 cases)
- Metrics/cases ở mức Needs Work (0.6–0.8): E03, E04, M01, M06, M07, H01, H03, H05 (8 cases)
- Metrics/cases ở mức Significant Issues (<0.6): H04, A01, A02, A03 (4 cases)

**Failure type distribution**

| Failure Type | Count | Percentage |
|---|---:|---:|
| hallucination | 2 | 50% |
| irrelevant | 0 | 0% |
| incomplete | 1 | 25% |
| off_topic | 1 | 25% |
| refusal | 0 | 0% |

**Chẩn đoán tổng quan:** Vấn đề chính nằm ở retrieval, generation hay cả hai?
Dùng ít nhất hai metrics để bảo vệ kết luận.

> *Câu trả lời:* Vấn đề chính nằm ở **Generation**. Dựa vào hai metrics:
> 1. **Context Recall (0.914)** và **Context Precision (0.931)** rất cao, chứng tỏ Retriever làm việc cực kỳ tốt, lấy đúng các chunk chứa câu trả lời.
> 2. **Faithfulness (0.662)** lại thấp nhất, chứng tỏ LLM Generator không tuân thủ nghiêm ngặt các chunk được cung cấp, dẫn đến việc sinh ra nội dung mâu thuẫn (hallucination) hoặc bị đánh lừa bởi câu hỏi.

---

## 2. Top 3 Worst Failures — 5 Whys

Phân loại failure trước khi đề xuất fix. Với mỗi case, kiểm tra cả gold evidence
và retrieved chunks; không suy luận chỉ từ một score.

### Failure 1

**ID và question:**

> *Điền:* A01 - What are the attendance requirements at Southstar University?

**Expected answer:**

> *Điền:* I support Northstar student-service questions and cannot answer questions about another institution's policies...

**Actual answer:**

> *Điền:* At Southstar University, students are expected to attend at least 80% of scheduled sessions...

**Scores:** Context Recall: 0.261 | Context Precision: 0.250 | Faithfulness: 0.000 |
Relevance: 0.600 | Completeness: 0.174 | Overall: 0.258

**Evidence inspection:** Retriever lấy đúng/thiếu/thừa chunks nào?

> *Câu trả lời:* Retriever lấy về chunk của `05_attendance_and_grading.md` vì keyword "attendance", nhưng thiếu hoàn toàn chunk từ `00_system_scope.md` quy định về scope out-of-bounds (do câu hỏi không chứa keyword liên quan đến scope).

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Model cung cấp thông tin của trường Northstar nhưng gán nhãn thành Southstar. |
| Why 1 | Tại sao symptom xảy ra? | Vì model nghĩ rằng các chunk về attendance áp dụng cho câu hỏi về Southstar. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Prompt không đủ mạnh để nhắc model kiểm tra tên trường trong query so với context. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Retriever không lấy được rules từ `00_system_scope.md` (chứa lệnh xử lý out of scope). |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Hệ thống RAG dùng semantic search đơn thuần, bị keyword "attendance" đánh lừa. |
| Why 5 | Root cause có thể hành động được là gì? | Thiếu cơ chế chèn System Rules cứng vào mọi LLM Generation call. |

**Root cause từ `find_root_cause()`:**

> *Paste output:* Không áp dụng (Tool không được cung cấp).

**Bạn đồng ý hay không? Dẫn evidence từ trace:**

> *Câu trả lời:* Đồng ý. Vấn đề cốt lõi là các System Rules (về scope, an toàn) không được Retriever ưu tiên lấy về, dẫn đến LLM sinh câu trả lời sai.

**Proposed fix cụ thể:**

> *Câu trả lời:* Hard-code các quy định từ `00_system_scope.md` thành System Prompt mặc định (luôn được gắn vào trước mọi câu hỏi) thay vì để Retriever tự tìm.

### Failure 2

**ID và question:**

> *Điền:* A03 - Since the university gives a 100% tuition refund for a withdrawal after census, how do I claim it?

**Expected answer:**

> *Điền:* The premise is incorrect. After census, no tuition is reversed for an ordinary course withdrawal.

**Actual answer:**

> *Điền:* To claim a 100% tuition refund after the census date, you must withdraw from all courses before classes begin, as no tuition is reversed for ordinary course withdrawals after the census date.

**Scores:** Context Recall: 0.800 | Context Precision: 1.000 | Faithfulness: 0.265 |
Relevance: 0.538 | Completeness: 0.800 | Overall: 0.534

**Evidence inspection:**

> *Câu trả lời:* Retriever lấy về rất chính xác chunk từ `03_tuition_payment_refund.md` nói rằng "After census, no tuition is reversed", nhưng LLM lại kết hợp sai.

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Model sinh ra câu trả lời mâu thuẫn (100% refund sau census nhưng phải withdraw trước khi học). |
| Why 1 | Tại sao symptom xảy ra? | Model cố gắng trả lời giả định sai của user thay vì bác bỏ nó trực tiếp. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Prompt thiếu instruction yêu cầu "phát hiện và bác bỏ false premise". |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | LLM thường có xu hướng "chiều lòng" user (sycophancy bias). |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | RAG pipeline chỉ yêu cầu "dựa vào context để trả lời". |
| Why 5 | Root cause có thể hành động được là gì? | Prompt generation yếu trong việc xử lý Adversarial False Premise. |

**Root cause và proposed fix:**

> *Câu trả lời:* Root cause là LLM sycophancy (chiều lòng người dùng). Fix: Thêm vào System Prompt: "If the user's question contains a false premise that contradicts the context, explicitly state that the premise is incorrect before answering."

### Failure 3

**ID và question:**

> *Điền:* H04 - What happens if I fail the scholarship renewal requirements a second consecutive time, and can I appeal it?

**Expected answer:**

> *Điền:* A second consecutive failed review ends the award beginning with the next term. Scholarship decisions may be appealed within ten business days to the Financial Aid Review Committee.

**Actual answer:**

> *Điền:* ...appeal within ten business days using the process outlined in the relevant student support and appeals documentation.

**Scores:** Context Recall: 0.850 | Context Precision: 1.000 | Faithfulness: 0.419 |
Relevance: 0.769 | Completeness: 0.550 | Overall: 0.580

**Evidence inspection:**

> *Câu trả lời:* Retriever lấy được chunk nói về appeal trong 10 ngày (từ `04_scholarships.md`) nhưng chunk này chỉ tham chiếu sang `08_student_support_and_appeals.md`. Nó không lấy đủ chunk từ Doc 08 chứa cụm từ "Financial Aid Review Committee".

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Câu trả lời thiếu tên uỷ ban "Financial Aid Review Committee". |
| Why 1 | Tại sao symptom xảy ra? | LLM trả lời chung chung vì context thiếu thông tin cụ thể. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Retriever không mang về chunk tương ứng trong `08_student_support_and_appeals.md`. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Liên kết chéo giữa các documents (cross-references) không được giải quyết bởi Retriever (Multi-hop reasoning thất bại). |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Text splitting chia nhỏ các file mà không bảo toàn logic liên kết. |
| Why 5 | Root cause có thể hành động được là gì? | Thiếu cơ chế Multi-hop Retrieval hoặc Query Expansion. |

**Root cause và proposed fix:**

> *Câu trả lời:* Root cause: Retriever không giải quyết được Multi-hop queries (câu hỏi yêu cầu lấy thông tin ở Doc A, thấy tham chiếu sang Doc B, rồi tiếp tục tìm ở Doc B). Fix: Thêm Query Rewriting hoặc Agentic RAG để có khả năng loop retrieval (tìm thêm thông tin khi context hiện tại có tham chiếu chéo).

---

## 3. Failure Clustering

Một root cause có thể tạo ra nhiều failures. Nhóm theo nguyên nhân có thể sửa,
không chỉ nhóm theo tên metric.

| Cluster | Root Cause | Failure IDs | Priority |
|---|---|---|---|
| 1 | Thiếu System Rules cố định trong Prompt (dẫn đến bị out_of_scope) | A01, A02 | High |
| 2 | LLM Sycophancy (chiều lòng người dùng) trước False Premise | A03 | Medium |
| 3 | Mất context trong Multi-hop queries (cross-document references) | H04 | High |

**Nếu chỉ được sửa một cluster, bạn chọn cluster nào và vì sao?**

> *Câu trả lời:* Chọn **Cluster 1**. Vì việc trả lời sai trường (A01) hoặc lộ thông tin hệ thống (A02) là rủi ro bảo mật và độ uy tín nghiêm trọng nhất (Safety/Scope violations). Sửa lỗi này chỉ cần cập nhật System Prompt, chi phí rất rẻ nhưng mang lại lợi ích lớn.

---

## 4. Improvement Log

Paste output của `generate_improvement_log()`:

```text
Chưa implement (câu hỏi Bonus).
```

**Ba improvement suggestions ưu tiên**

1. Cập nhật System Prompt với các giới hạn (Scope Bounds) cố định (không phụ thuộc vào Retriever).
2. Thêm instruction yêu cầu bắt buộc "Phát hiện và đính chính nếu tiền đề của câu hỏi mâu thuẫn với tài liệu".
3. Tăng top_k hoặc sử dụng LLM Query Expansion để giải quyết các trường hợp Multi-hop retrieval.

Với mỗi suggestion, nêu metric dự kiến thay đổi và cách đo lại.

| Suggestion | Target metric | Verification method |
|---|---|---|
| Hard-code System Rules | Relevance & Completeness | Chạy lại A01, A02 |
| Sửa prompt xử lý False Premise | Faithfulness | Chạy lại A03 |
| Query Expansion (Multi-hop) | Context Recall | Chạy lại H04 |

---

## 5. Regression Testing Strategy

**Câu 1: Khi nào chạy `run_regression()` trong production workflow?**

> *Câu trả lời:* Chạy trong pipeline CI/CD ở giai đoạn Staging mỗi khi có commit thay đổi Prompt, LLM model version, hoặc cấu hình RAG (chunk size, retriever top_k).

**Câu 2: Threshold drop 0.05 có phù hợp Student Services không? Vì sao?**

> *Câu trả lời:* Phù hợp. Tuy nhiên đối với các metric liên quan đến Safety / Faithfulness, drop threshold có thể cần đặt khắt khe hơn (ví dụ 0.00 hoặc tuyệt đối không được rớt) vì tư vấn sai chính sách học phí hay điểm số gây hậu quả nặng nề.

**Câu 3: Metric/failure nào phải block deployment, metric nào chỉ alert?**

> *Câu trả lời:*
> - **Block deployment**: Faithfulness drop (sinh ra hallucination), Failures liên quan đến Adversarial (System Scope).
> - **Alert**: Context Recall giảm nhẹ, Completeness giảm (câu trả lời ngắn hơn nhưng vẫn đúng).

**Câu 4: Điền evaluation stages vào flow.**

```text
Code/prompt/retrieval change → [Unit Tests] → [Integration/RAG Tests] → [Golden Dataset Benchmark] → Deploy
```

> *Giải thích:* Unit Tests kiểm tra code logic; Integration Tests chạy thử retrieval pipeline cơ bản; Golden Dataset Benchmark dùng LLM-as-a-judge chấm điểm trên 20 test cases khó để chống regression, đóng vai trò gác cổng cuối cùng.

---

## 6. Continuous Improvement Loop

```text
Evaluate → Analyze → Improve → Augment benchmark → Repeat
```

| Priority | Action | Metric dự kiến cải thiện | Expected impact |
|---:|---|---|---|
| 1 | Sửa System Prompt chặn out_of_scope | Relevance, Safety | Cao (giảm rủi ro brand) |
| 2 | Cấu hình lại Retriever (Query Expansion) | Context Recall | Vừa (tăng tính đầy đủ) |
| 3 | Chống Sycophancy (False Premise) | Faithfulness | Vừa |

**Hai hoặc ba failure cases nào cần thêm vào benchmark ở vòng tiếp theo?**

> *Câu trả lời:*
> 1. Câu hỏi đòi hỏi tổng hợp từ 3 files trở lên (để test giới hạn Multi-hop).
> 2. Lịch sử chat (Multi-turn conversations) có chứa coreference (vd: "What is the fee for *that*?").
> 3. Câu hỏi về chính sách cũ (v1.0) nhưng ở bối cảnh tương lai (để kiểm tra độ nhạy về thời gian).

---

## 7. Final Reflection

**Điều gì trong kết quả benchmark trái với dự đoán ban đầu của bạn?**

> *Câu trả lời:* Điểm Context Precision của Retriever rất cao (đạt trung bình 0.931), chứng tỏ RAG lấy dữ liệu tốt. Nhưng LLM lại tạo ra điểm Faithfulness khá thấp, trái với suy đoán thông thường "chỉ cần cung cấp đúng document là LLM sẽ trả lời đúng". Rất nhiều lỗi phát sinh do LLM bị lừa bởi câu hỏi thay vì thiếu thông tin.

**Word-overlap heuristics trong lab có giới hạn gì? Nếu đưa hệ thống vào
production, bạn sẽ thay hoặc bổ sung metric nào?**

> *Câu trả lời:* Word-overlap trừng phạt các câu trả lời paraphrase (tóm tắt bằng từ vựng khác) và khó đánh giá được độ lệch ngữ nghĩa. Khi đưa vào production, nên thay bằng Semantics-based metrics (như BERTScore, NLI-based Faithfulness) hoặc sử dụng bộ LLM-as-a-Judge đã được tinh chỉnh (Fine-tuned judge) thay vì dùng RAGAS cơ bản.
