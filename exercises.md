# Day 14 — Exercises

## AI Evaluation & Benchmarking · Lab Worksheet

**Thời gian làm bài:** 09:15–12:00

**Domain:** Northstar University Student Services

Điền trực tiếp câu trả lời vào file này. Golden dataset 20 QA được viết một lần
duy nhất trong `golden_dataset.json`, không chép lại toàn bộ vào Markdown.

---

Từ 09:15–09:30, cài môi trường và chạy baseline tests theo `guide_lab.md`.

---

## Part 1 — Warm-up (09:30–09:45)

### Exercise 1.1 — RAGAS Metric Thresholds

Theo bài giảng:

- 0.8–1.0: Good — monitor, maintain.
- 0.6–0.8: Needs work — analyze failures, iterate.
- Dưới 0.6: Significant issues — investigate.

Với từng metric, xác định khi nào score thấp có thể chấp nhận và khi nào là
critical.

| Metric | Acceptable Low Score Scenario | Critical Low Score Scenario | Action Required |
|---|---|---|---|
| Faithfulness | Answer đúng nhưng **diễn đạt lại** gold context nên token overlap thấp (context: "USD 420 per registered credit" → answer: "học phí 420 đô mỗi tín chỉ"), hoặc case adversarial mà hành vi đúng là **từ chối + chuyển hướng** nên phần lớn token của answer không nằm trong context. | Answer chứa **số tiền / deadline / điều kiện không có trong corpus**: ví dụ vẫn báo late-add fee USD 25 (Registration Policy v1.0) cho một request sau 2026-08-01, hoặc tự bịa tỷ lệ refund sau census date. Đây là hallucination trên claim tài chính. | **Block release.** Siết grounding guardrail: bắt buộc trích `doc_id` cho mỗi claim, thêm rule "không có trong corpus thì nói không biết + chuyển office", gắn nhãn `hallucination` và đưa case vào regression set. |
| Answer Relevance | Question dài, nhiều câu dẫn dắt nên mẫu số \|question tokens\| lớn và điểm bị pha loãng; hoặc answer đúng là một **refusal ngắn** cho câu out-of-scope (A-cases) nên echo lại rất ít từ của question. | Answer trả lời **sang chủ đề khác**: hỏi refund khi medical withdrawal nhưng answer giải thích điều kiện gia hạn scholarship. Student nhận hướng dẫn sai quy trình. | Sửa **intent routing / prompt** và cách dựng query cho retriever; đối chiếu bằng LLM judge (rubric Relevance) thay vì chỉ tin overlap; gắn nhãn `irrelevant` / `off_topic`. |
| Context Recall | Expected answer chứa token **không tồn tại nguyên văn trong corpus**: giá trị được suy ra (5 tín chỉ × 420 = USD 2,100), tên office viết tắt, hoặc expected answer của case adversarial là một câu từ chối. | Case multi-hop cần evidence từ **≥2 documents** (NU-03 refund + NU-09 policy version) mà retriever chỉ lấy được một document → answer **không thể** đầy đủ dù generator hoàn hảo. Recall là chặn trên của Completeness. | Sửa ở **retriever**: tăng `top_k`, xem lại chunking, query rewriting / multi-query, hybrid (BM25 + embedding). Recall thấp **không** chữa được bằng prompt hay reranking. |
| Context Precision | Recall đã cao, chunk nhiễu chỉ nằm **sau** chunk relevant nên generator vẫn grounded; hoặc chỉ có 1 chunk relevant trong 5 chunk nên AP@K thấp một cách tự nhiên. Lúc này đây là vấn đề **cost/latency và context budget**, không phải correctness. | Chunk relevant bị xếp hạng 4–5 trong khi top-rank là nhiễu, khiến generator ground vào **phiên bản policy sai** (late-add v1.0 thay vì v2.0) hoặc vào tài liệu khác chủ đề. Precision thấp lúc này kéo Faithfulness/Completeness xuống theo. | Reranking (Ex 3.5), đổi embedding / cải thiện query, **metadata filter theo `effective_date` và `status: current`**. Nếu answer metrics vẫn tốt thì chỉ monitor, không block. |
| Completeness | Expected answer viết dài, answer nêu **đủ fact quyết định** nhưng ngắn gọn hơn nên overlap thấp; hoặc partial credit chấp nhận được với case Easy tra cứu một dữ kiện. | Case Hard nhiều điều kiện mà answer **bỏ mất exception làm đổi hành động** của student: không nói "sau census date không hoàn học phí", hoặc không nói "grace period 5 ngày không gia hạn deadline scholarship/registration". Student mất tiền hoặc mất quyền lợi. | Tăng coverage retrieval trước, sau đó buộc generation **liệt kê đủ điều kiện – ngoại lệ – effective date – office phụ trách** theo answer template; gắn nhãn `incomplete`. |

### Exercise 1.2 — Bias trong LLM-as-a-Judge

Ba bias thường gặp:

- Position bias: judge ưu tiên answer xuất hiện trước.
- Verbosity bias: judge ưu tiên answer dài hơn.
- Self-preference: judge ưu tiên output giống chính model đó.

**Câu 1: Thiết kế experiment phát hiện position bias với ít nhất hai conditions.**

> *Câu trả lời:*
>
> **Setup chung:** cùng judge model, cùng rubric, `temperature=0`, cùng seed, N ≥ 30
> cặp answer lấy từ golden dataset (bắt buộc gồm cả 3 case adversarial). Với mỗi
> question ta có cặp (A, B) là hai answer từ hai phiên bản assistant.
>
> | Condition | Thứ tự đưa vào judge prompt | Mục đích |
> |---|---|---|
> | C1 — original | `Answer 1 = A`, `Answer 2 = B` | baseline |
> | C2 — swapped | `Answer 1 = B`, `Answer 2 = A` | cùng nội dung, chỉ đổi vị trí |
> | C3 — control (tùy chọn, mạnh nhất) | `Answer 1 = A`, `Answer 2 = A` (hai bản y hệt) | mọi verdict khác "tie" là position bias thuần |
>
> **Metrics:**
> - *Flip rate* = tỉ lệ cặp mà verdict đổi giữa C1 và C2. Judge không bias → flip
>   rate ≈ 0 (trừ nhiễu).
> - *Position-1 win rate* = tỉ lệ judge chọn answer ở vị trí đầu, tính trên toàn bộ
>   2N lượt chấm. Kỳ vọng 50%; kiểm định binomial hai phía, `p < 0.05` và lệch
>   ≥ 5 điểm phần trăm thì kết luận có position bias.
> - Với scoring 1–5: so sánh mean score theo vị trí bằng paired t-test /
>   Wilcoxon trên cùng answer ở C1 vs C2.
>
> **Cách khắc phục sau khi đo:** randomize thứ tự và chấm cả hai chiều rồi lấy
> trung bình (dual-order averaging), hoặc chuyển sang **pointwise scoring** với
> rubric tuyệt đối thay vì so sánh cặp. Đây cũng chính là ý tưởng của nhánh
> `positional` trong `LLMJudge.detect_bias()`.

**Câu 2: Làm thế nào giảm verbosity bias bằng rubric design?**

> *Câu trả lời:*
>
> Nguyên tắc: **rubric phải neo vào coverage của claim bắt buộc, không neo vào độ dài.**
>
> 1. Với mỗi question, liệt kê trước một **required-claims checklist** (số tiền,
>    deadline, điều kiện, ngoại lệ, effective date, office phụ trách). Score được
>    định nghĩa theo *số claim bắt buộc được nêu đúng*, ví dụ 5 = đủ claim và
>    không có claim sai; 3 = thiếu 1 claim không quyết định hành động.
> 2. Buộc judge **xuất rationale có cấu trúc trước khi ra score**: liệt kê
>    `matched_claims` / `missing_claims` / `unsupported_claims`. Judge phải chứng
>    minh bằng claim, nên không thể "cảm thấy dài hơn thì tốt hơn".
> 3. Thêm **penalty rule tường minh**: nội dung không có evidence trong corpus,
>    hoặc phần lan sang policy khác không được hỏi, làm **giảm** điểm — dài mà loãng
>    bị trừ, không được cộng.
> 4. Đặt **anchor examples ngược chiều**: ví dụ mức 5 là một answer ngắn 3 câu đủ
>    fact; ví dụ mức 2–3 là một answer dài, đúng giọng điệu nhưng thiếu exception.
>    Anchor dạy judge rằng length ≠ quality hiệu quả hơn mọi câu dặn dò.
> 5. Tách **Conciseness/Clarity thành dimension riêng** để độ dài được chấm minh
>    bạch ở một chỗ, thay vì rò rỉ ngầm vào điểm Correctness.

**Câu 3: Tại sao cần calibrate LLM judge với human labels?**

> *Câu trả lời:*
>
> Judge chỉ là **proxy metric**; nếu chưa biết nó khớp ground truth đến đâu thì
> điểm của nó không có đơn vị và không thể dùng làm CI/CD gate.
>
> - **Đo độ tin cậy:** gán nhãn tay một subsample stratified (~25%, gồm toàn bộ
>   adversarial), rồi tính Cohen's kappa (agreement) và Spearman (thứ tự). Kappa
>   thấp ⇒ sửa rubric, không sửa threshold.
> - **Phát hiện offset hệ thống:** leniency (mọi case đều 4–5, không phân biệt được
>   good/bad) và severity — đúng hai nhánh còn lại trong `detect_bias()`. Judge
>   lệch đều thì threshold 0.8 mang nghĩa hoàn toàn khác.
> - **Lỗi domain-specific:** judge dễ bỏ qua sai policy version (late-add v1.0 vs
>   v2.0), sai số tiền, hoặc trả lời thay cho office — human label mới bắt được và
>   mới định giá đúng mức "critical" của các lỗi này.
> - **Chống drift:** mỗi lần đổi judge model / prompt, judge cũng là một hệ thống
>   thay đổi. Human-labeled set là **regression baseline cho chính judge**.
> - **Kết quả phụ có giá trị:** tập human label trở thành gold set để so sánh các
>   framework (Ex 3.4) và để chọn threshold thực sự tương ứng với "chấp nhận được".

### Exercise 1.3 — Evaluation trong CI/CD

**Câu 1: Chọn threshold để block deployment.**

| Metric | Threshold | Lý do |
|---|---:|---|
| Faithfulness | 0.80 | Hallucination về học phí, phí trễ hạn, deadline hoặc tỷ lệ refund là failure đắt nhất của domain này — student hành động theo và mất tiền. Grounding là gate nghiêm nhất, đặt ở mép dưới của vùng "Good" (0.8–1.0). |
| Answer Relevance | 0.70 | Heuristic overlap chấm thấp một cách oan cho refusal đúng và cho answer paraphrase, nên gate cứng 0.8 sẽ tạo nhiều false block. 0.70 = mép trên vùng "Needs work": vẫn bắt được off-topic/routing sai mà không chặn build vì cách diễn đạt. |
| Completeness | 0.70 | Answer thiếu một phần nhưng đã chỉ đúng office phụ trách thì student vẫn đi tiếp được, nên đây là gate mềm hơn Faithfulness. Bù lại chặn theo **regression**: giảm > 0.05 so với baseline là block (đúng ngưỡng trong `run_regression`). |

**Hard rules đi kèm** (threshold trung bình một mình là không đủ, vì trung bình che được failure nặng lẻ):

- Không case nào có `faithfulness < 0.5` — một câu bịa số tiền là đủ để block.
- Cả 3 case adversarial phải pass: out-of-scope thì từ chối, prompt injection thì
  không tiết lộ, false premise thì phải sửa lại tiền đề.
- Bất kỳ metric nào giảm > 0.05 so với baseline ⇒ block, kể cả khi vẫn trên
  threshold tuyệt đối (`BenchmarkRunner.run_regression`).
- Context Recall / Context Precision **không block build** — chúng là tín hiệu
  chẩn đoán retrieval, báo warning và tạo ticket.

**Câu 2: Khi nào dùng offline evaluation, online evaluation và human review?**

> *Câu trả lời:*
>
> | Loại | Khi nào chạy | Trả lời câu hỏi gì | Chi phí / hạn chế |
> |---|---|---|---|
> | **Offline** | Mỗi PR, mỗi lần đổi prompt / model / chunking / `top_k`; chạy trong CI trên golden dataset 20 câu, là gate trước merge và trước deploy | "Thay đổi này có làm hệ thống tệ hơn so với baseline không?" | Rẻ, deterministic, so sánh được — nhưng chỉ đo đúng 20 case ta đã nghĩ ra; không thấy được gì mới |
> | **Online** | Liên tục sau deploy, trên traffic thật; canary 5–10% trước khi mở 100% | Refusal rate, escalation rate, thumbs-down, latency/cost, tỉ lệ câu hỏi không có evidence trong corpus, drift khi policy đổi hiệu lực (ví dụ 2026-08-01) | Có ground truth yếu (không có expected answer), nhiễu, chậm phát hiện; bù lại là nguồn tốt nhất để bổ sung case mới cho golden dataset |
> | **Human review** | (1) Định kỳ hàng tuần trên sample stratified; (2) mỗi lần đổi judge model — calibration; (3) mọi case high-stakes: privacy, tiền, appeal, adversarial; (4) khi judge và heuristic không đồng thuận | "Điểm số của ta có thật sự tương ứng với chất lượng không?" và "case này có gây hại không?" | Đắt và chậm nhất, không scale — nên dùng có chọn lọc, nhưng là gốc chuẩn để calibrate cả hai loại trên |
>
> Vòng lặp thực tế: **offline chặn regression trước khi ra prod → online phát hiện
> vấn đề mà offline không lường tới → human review phân xử các case mơ hồ và
> calibrate judge → case mới quay lại làm giàu golden dataset offline.**

---

## Part 2 — Core Coding (09:45–10:40)

Hoàn thiện các TODO bắt buộc trong `template.py`.

### Task 1 — Data Models

- `QAPair`: question, expected answer, gold context, metadata và retrieved contexts.
- `EvalResult`: answer-side scores, optional retrieval scores, pass/failure fields.
- `overall_score()`: trung bình Faithfulness, Relevance và Completeness.

### Task 2 — RAGASEvaluator

Answer-side:

- `evaluate_faithfulness(answer, context)`
- `evaluate_relevance(answer, question)`
- `evaluate_completeness(answer, expected)`

Retrieval-side:

- `evaluate_context_recall(contexts, expected)`
- `evaluate_context_precision(contexts, expected)`

Full pipeline:

- `run_full_eval(..., contexts=None)` luôn tính ba answer metrics.
- Nếu có `contexts`, tính và lưu thêm Context Recall và Context Precision.
- Retrieval scores không làm thay đổi `overall_score()` và pass rule gốc.

### Task 3 — LLMJudge

- `score_response(question, answer, rubric)`
- `detect_bias(scores_batch)`

### Task 4 — BenchmarkRunner

- `run(qa_pairs, agent_fn, evaluator)`
- `generate_report(results)`
- `run_regression(new_results, baseline_results)`
- `identify_failures(results, threshold)`

`BenchmarkRunner.run()` phải truyền `pair.retrieved_contexts` vào
`run_full_eval()`. Report phải có average của hai retrieval metrics.

### Task 5 — FailureAnalyzer

- `categorize_failures(failures)`
- `find_root_cause(failure)`
- `generate_improvement_suggestions(failures)`
- `generate_improvement_log(failures, suggestions)`

Kiểm tra:

```bash
pytest tests/ -v
```

`rerank_by_overlap()` là TODO bonus của Exercise 3.5. Test tương ứng được skip
nếu bạn chưa làm bonus.

---

## Part 3 — Golden Dataset & Real Benchmark (10:40–11:35)

### Exercise 3.1 — Build the Golden Dataset

Thiết kế và validate dataset theo Mục 5–6 trong `guide_lab.md`. Nội dung 20 QA
được điền trực tiếp trong `golden_dataset.json`; phần dưới chỉ ghi lại kết quả
và quyết định thiết kế, không chép lại toàn bộ QA.

**Kết quả dataset**

| Hạng mục | Kết quả |
|---|---|
| Tổng số records | ____ / 20 |
| Easy | ____ / 5 |
| Medium | ____ / 7 |
| Hard | ____ / 5 |
| Adversarial | ____ / 3 |
| Source documents được sử dụng | ____ / 10 |
| Validator status | PASS / FAIL |

**Ba case đại diện cho quyết định thiết kế**

| ID | Difficulty | Source document(s) | Vì sao case phù hợp với difficulty/attack type? |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

**Điểm khó nhất khi xây dựng expected answer hoặc evidence là gì?**

> *Câu trả lời:*

**Xác nhận:**

- [ ] Mọi claim trong expected answer đều có evidence hỗ trợ.
- [ ] Không có questions trùng ý và không dùng kiến thức ngoài corpus.
- [ ] `python validate_golden_dataset.py` báo `PASS`.

### Exercise 3.2 — Benchmark Run

Chạy:

```bash
python domain_assistant.py
python evaluate_answers.py
```

Copy bảng terminal vào đây hoặc điền từ `artifacts/benchmark_results.json`.

| ID | Question (short) | Ctx Recall | Ctx Precision | Faithfulness | Relevance | Completeness | Overall | Passed? | Failure Type |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| E01 | | | | | | | | | |
| E02 | | | | | | | | | |
| E03 | | | | | | | | | |
| E04 | | | | | | | | | |
| E05 | | | | | | | | | |
| M01 | | | | | | | | | |
| M02 | | | | | | | | | |
| M03 | | | | | | | | | |
| M04 | | | | | | | | | |
| M05 | | | | | | | | | |
| M06 | | | | | | | | | |
| M07 | | | | | | | | | |
| H01 | | | | | | | | | |
| H02 | | | | | | | | | |
| H03 | | | | | | | | | |
| H04 | | | | | | | | | |
| H05 | | | | | | | | | |
| A01 | | | | | | | | | |
| A02 | | | | | | | | | |
| A03 | | | | | | | | | |

**Aggregate Report**

- Overall pass rate: ____%
- Avg Context Recall: ____
- Avg Context Precision: ____
- Avg Faithfulness: ____
- Avg Relevance: ____
- Avg Completeness: ____
- Failure type distribution: ____

**Ba cases có Overall Score thấp nhất**

1. ID: ____ | Score: ____ | Failure type: ____
2. ID: ____ | Score: ____ | Failure type: ____
3. ID: ____ | Score: ____ | Failure type: ____

**Nhận xét ngắn:** Metric nào yếu nhất? Kết quả gợi ý vấn đề nằm ở retrieval
hay generation?

> *Câu trả lời:*

### Exercise 3.3 — LLM-as-a-Judge Rubric Design

Thiết kế rubric domain-specific cho Student Services. Mỗi mức phải đủ cụ thể để
hai người chấm độc lập có thể hiểu giống nhau.

Chọn 3–5 dimensions:

- [ ] Correctness
- [ ] Completeness
- [ ] Relevance
- [ ] Evidence/citation
- [ ] Actionability
- [ ] Safety/privacy
- [ ] Tone/clarity
- [ ] Dimension khác: __________

| Score | Tiêu chí domain-specific | Ví dụ response |
|---:|---|---|
| 5 | | |
| 4 | | |
| 3 | | |
| 2 | | |
| 1 | | |

**Ba edge cases khó chấm**

| Edge Case | Tại sao khó chấm? | Rubric xử lý thế nào? |
|---|---|---|
| | | |
| | | |
| | | |

**Bias controls:** Rubric hoặc evaluation protocol của bạn giảm position bias,
verbosity bias và self-preference bằng cách nào?

> *Câu trả lời:*

### Exercise 3.4 — Framework Comparison (Bonus +10)

Chỉ làm sau khi hoàn thành 3.1–3.3. Chọn hai framework trong RAGAS, DeepEval
và TruLens; chạy hoặc thiết kế một so sánh có cùng input dataset.

| Tiêu chí | Framework 1: ____ | Framework 2: ____ |
|---|---|---|
| Setup complexity | | |
| Metrics available | | |
| CI/CD integration | | |
| Kết quả trên cùng dataset | | |
| Insight rút ra | | |

- Scores có nhất quán không?
- Framework nào strict hơn và vì sao?
- Hai framework có tìm ra cùng failure cases không?

> *Phân tích:*

### Exercise 3.5 — Retrieval Reranking (Bonus +5)

Mục tiêu: kiểm tra việc đổi thứ tự chunks có tăng Context Precision mà không
thay đổi Context Recall hay không.

1. Chọn ít nhất 5 cases từ `artifacts/actual_answers.json`.
2. Tính Context Recall và Context Precision trước rerank.
3. Implement `rerank_by_overlap()` hoặc một reranker khác.
4. Rerank cùng tập chunks, không thêm hoặc xóa chunk.
5. Tính lại hai metrics và giải thích kết quả.

| ID | Recall before | Recall after | Precision before | Precision after | Delta Precision |
|---|---:|---:|---:|---:|---:|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| **Avg** | | | | | |

**Tại sao Recall dự kiến không đổi?**

> *Câu trả lời:*

**Khi nào reranking không đủ và cần sửa retriever/query/chunking?**

> *Câu trả lời:*

---

## Part 4 — Reflection (11:35–11:50)

Hoàn thành `reflection.md` bằng kết quả thật từ Exercise 3.2.

---

## Completion Checklist

Hoàn thành kiểm tra cuối trong khoảng 11:50–12:00.

- [ ] Tất cả required tests pass.
- [ ] `golden_dataset.json` validate thành công.
- [ ] Exercise 3.1 hoàn thành trong file JSON và bảng kết quả phía trên.
- [ ] Exercise 3.2 có năm metrics, aggregate report và ba cases thấp nhất.
- [ ] Exercise 3.3 có rubric 1–5 và bias controls.
- [ ] `reflection.md` có ba failure analyses và regression strategy.
- [ ] Đã copy `template.py` thành `solution/solution.py`.
- [ ] Exercise 3.4 và 3.5 chỉ làm nếu chọn bonus.
