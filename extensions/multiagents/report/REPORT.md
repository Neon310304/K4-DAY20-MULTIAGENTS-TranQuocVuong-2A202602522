# Phần 5 — Test, Debug & Performance

**Báo cáo cuối Phần 6:** [FINAL_REPORT.md](FINAL_REPORT.md), đủ 10 mục và phụ lục bonus 6c. File này giữ nguyên số liệu/debug snapshot Phần 5; test snapshot mới có 68 tests và coverage 92.6650%, không ghi đè benchmark live cũ.

Phần bổ sung Coordinator/Workers nằm riêng trong `extensions/multiagents/`, không thay scaffold Deep Agents, H1–H3, tag freeze, 18 run chính thức hoặc bảng `report/table.md`. Các mục 5–6 dưới đây đáp ứng template được gửi bổ sung; không thay mục 5–6 của báo cáo thí nghiệm chính.

## 5. Test Results

| File test trong extension | Kết quả |
| --- | ---: |
| test_02_coordinator.py | 10/10 |
| test_03_workers.py | 8/8 |
| test_04_tools.py | 4/4 |
| test_05_integration.py | 14/14 |
| test_communication.py | 4/4 |
| test_integration.py | 1/1 |
| test_tool_collaboration.py | 1/1 |
| test_tool_guardrails.py | 8/8 |
| test_tools.py | 7/7 |
| **Tổng** | **57/57** |

`evidence/part5-tests-final.txt`: **57 passed in 11.95s**, có `--durations=10`. `evidence/coverage-final.json`: **92.2535% statement coverage** (1048/1136 statements) trên `src/day20_multiagents/`, không phải branch coverage, không bao gồm scripts, mã Python sinh ra hoặc implementation SDK. Test dùng fake model; không gửi API key, không biến test pass thành bằng chứng chất lượng LLM.

E2E mới: request → parse/route → worker → local tool → kiểm dữ kiện/file thật → aggregate response. Complex chạy **data → code → evaluator** với data_result trong parameters, không chạy song song hai bước phụ thuộc. Mỗi request có Coordinator/queue/model/SQLite/workspace riêng; semaphore giới hạn bốn request hoạt động. Test gửi mười request đồng thời trên một system, deadline/cancel/reuse, crash, input rỗng, trả lời sai nhưng trôi chảy, usage thiếu, percentile/median, JSON logs và môi trường có dấu nháy. Offline E2E kiểm nguồn không đổi, Q3 revenue=150 và rows=3, script thực thi, PNG decode, comparison/report; không chỉ kiểm agent tự nói “success”.

Hai benchmark cuối dùng cùng fixture: CSV/SQLite có quarter/amount và bốn sales (Q3: 40,50,60; Q1:900). Không phải dữ liệu benchmark Deep Agents, không sửa tasks hoặc data bài chính. Mỗi case chạy **ba lần** từ workspace sạch; load chạy mười request data với concurrency=4. Lưu toàn bộ records, checks, queue messages, model/tool spans, artifacts/hash và lỗi, không chỉ lượt thành công.

## 6. Performance Analysis

### 6.1. Benchmark live cuối — YesScale/gpt-4.1-mini

Nguồn: `evidence/part5-live-final/benchmark_results.json` và `events.jsonl`, nhiệt độ 0, SDK timeout 30s/max_retries=2, whole-request deadline 90s. Bảng tính cả các lần lỗi, không chạy lại chỉ để lấy điểm đẹp.

| Case | Đạt kiểm chứng | Min (s) | Max (s) | Avg (s) | Median/P50 (s) | P99 (s) | Req/min | Error rate | Token |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Simple data query | 3/3 | 2.795 | 4.120 | 3.465 | 3.482 | 4.107 | 17.31 | 0% | 3231 |
| Code generation | 2/3 | 6.791 | 9.623 | 8.148 | 8.029 | 9.591 | 7.36 | 33.33% | 7386 |
| Complex workflow | 2/3 | 21.854 | 27.718 | 24.752 | 24.685 | 27.657 | 2.42 | 33.33% | 23931 |
| Concurrent data (10 req, 4 slots) | 10/10 | 3.427 | 12.713 | 6.905 | 6.251 | 12.442 | 47.09 | 0% | 10768 |

**17/19 request đạt kiểm chứng**, error rate toàn bộ **10.53%**, **45316 token** và **66 logical model invocations**. Token cộng `AIMessage.usage_metadata` mọi response của main worker loops; không estimator hoặc hard-code 150k. SDK retry nội bộ không tăng logical count, failed/cancelled response có thể không có usage; số đo không là hóa đơn. Lần cuối mọi invocation có usage, nhưng không bảo đảm billing của retry trùng metadata. Không có giá/hóa đơn YesScale được kiểm chứng: USD để **null**, không áp giá OpenAI vào gateway.

`tokens_per_100_requests` là ngoại suy từ mẫu: simple **107700**, code **246200**, complex **797700**, concurrent data **107680**; toàn bộ mix 19 request khoảng **238505/100 request**, không phải thật sự chạy 100 request. Simple đạt P50<5s/P99<15s/throughput>10; code không đạt P50/throughput; complex không đạt P50/P99/throughput. Load data đạt P99/throughput và 10/10, nhưng P50=6.251s không đạt 5s. Error target <1% **chưa đạt**, không kết luận hệ thống sẵn sàng production.

Percentile nội suy tại `(n−1)*fraction`, median đúng cả n chẵn. Ba mẫu/case hoặc mười mẫu/load không đủ ước lượng tail P99/SLO. Throughput = số request hoàn tất / batch wall-time ×60, gồm cả lỗi, closed-loop không có pacing; không là capacity dài hạn hoặc throughput chỉ của câu trả lời hợp lệ. Load latency gồm đợi semaphore, tạo fixture/models, worker/tool/model và kiểm chứng; context/network/cache noise vẫn có.

### 6.2. Offline cuối — local plumbing, không chất lượng LLM

Nguồn: `evidence/part5-offline-final/benchmark_results.json`. Scripted model driver gọi tool thật; **19/19** đạt, token/API=0.

| Case | Avg (s) | Median/P50 (s) | P99 (s) | Req/min |
| --- | ---: | ---: | ---: | ---: |
| Simple data query | 0.026 | 0.026 | 0.030 | 2266.31 |
| Code generation | 0.194 | 0.174 | 0.237 | 308.89 |
| Complex workflow | 1.251 | 1.223 | 1.435 | 47.92 |
| Concurrent data | 0.109 | 0.106 | 0.147 | 2761.11 |

Offline không có thời gian mạng/suy luận. Code stage chiếm **89.74%** wall-time complex offline; trong live complex, model spans tổng **70.308s** so với tool spans **3.617s**, trên **74.258s** batch. Bottleneck chuyển từ Python/matplotlib startup sang API/model waits và nhiều vòng tool call. Không lấy tốc độ offline để tuyên bố live đạt latency target.

Worker utilization = tổng stage wall-time / (batch wall-time × slots), **bao gồm đợi API**, không CPU utilization. Load live data **78.33%** của bốn slots; simple data **88.51%**, code-only **99.06%** (mỗi case tuần tự một slot). Complex live phân bổ data **16.20%**, code **60.27%**, evaluator **23.11%**. Không ép mọi loại worker đạt 70–90% khi thiết kế có dependency và role khác nhau.

### 6.3. Debug bằng evidence; giữ cả run thất bại

1. **Cấu hình Docker khác dotenv.** `part5-live/` có **0/19**, logs `OpenAIConnectionError`; kiểm tra chỉ cờ cấu hình thấy endpoint/key có dấu nháy bao quanh, URL không parse được HTTPS/host. Docker `--env-file` giữ nháy thay vì parse như python-dotenv. Sửa `environment_value()` bỏ đúng một cặp nháy và thêm regression test, không in key hoặc sửa `.env`. Usage thiếu để null, không coi lỗi nhanh 1–4s là latency inference. Run lỗi còn nguyên.
2. **Schema/assignment mơ hồ.** `part5-live-fixed/` chỉ **4/19**, ví dụ data trả nguyên văn `{"revenue":150,"rows":4}`; code `KeyError: 'revenue'`; data `OperationalError: no such column: date`; evaluator `ValueError: Invalid evaluator fields`. Worker đoán cột/chạy nhầm phần việc của worker khác và hiểu rows là full CSV count/list. Sửa delegation kèm table/CSV schema, quarter filter, COUNT(*) và phạm vi vai trò; đưa nested evaluation JSON schema vào ReportGeneratorTool. Không đưa đáp án chuẩn cho Data/Code, không chỉnh nguồn/checker. Run sau fix và run cũ đều lưu, **không là controlled ablation** vì prompts/code khác và model noise.
3. **Lỗi còn lại của code schema.** Run cuối `f291fb4f-22ee-4e71-9ad4-bbc9c14f8fd6`: worker “success”, nhưng answer.json có revenue=150 và **rows là list ba bản ghi**, không integer 3. Checker `code_numbers=false` nên toàn request error; script/answer/hash còn ở artifacts. Đề xuất: output-contract schema cho answer.json trước final success, chỉ nhận int rows, đưa lỗi validation về vòng sửa có giới hạn thay vì tin text/file tồn tại.
4. **REPL không giữ globals.** Run cuối `a291d855-8134-4631-a2f0-03cb89fffc1b`: script/answer/PNG đã sinh nhưng call tiếp lỗi `NameError: name 'os' is not defined`. REPL là subprocess mới mỗi call, model dùng import từ call trước như state lâu dài. Giữ lỗi; không gọi thành công chỉ vì PNG tồn tại. Đề xuất: mỗi snippet tự import hoặc chỉ chạy script hoàn chỉnh, trả lỗi tool vào model repair loop bounded; không mở globals dùng chung hoặc nới sandbox để làm đẹp benchmark.

Lần live-fixed có **29550 token**; cộng final **74866 token metadata** cho hai lần live nhận usage. Run lỗi setup không có usage, không cộng thành 0 hoặc giả là hóa đơn đầy đủ. Đây là chi phí debug riêng, không thêm vào 908894 token của 18 run bài chính.

Common issues đã có test/giới hạn: queue full dùng bounded backpressure + send timeout, worker crash là structured error, whole-request timeout hủy native async/coroutines và trả timeout, SQL authorizer/progress bound, Python giới hạn subprocess. Native model dùng retry hữu hạn của SDK; không thêm retry nghiệp vụ quanh side-effect file tools. Retry rate limit cần backoff/jitter/Retry-After và deadline, không retry quota/authentication vô hạn. Đồng thời nhiều request dùng request-local resources; không cho nhiều batch tranh một Coordinator.

### 6.4. Profiling, logs và đề xuất

`scripts/profile_system.py`: năm request offline luân phiên ba case, file `evidence/part5-profile-final/profile.pstats`, `profile.txt`, `requests.json`; **72198 calls trong 1.588s**, top cumulative có selectors/select **1.417s**, subprocess communicate **1.398s**. Async inclusive times có overlap, không cộng tất cả cumulative times thành tổng và không coi profiler này là phân tích GPU/model service. `scripts/debug_system.py` lưu JSON events/result/artifact; `debug_agent.py` chạy riêng worker trên fixture tạm. Logs có logger/level/time/event; model/tool spans có duration/status và queue messages có run/task correlation. Không log env/header/key hoặc raw tool arguments; communication/artifacts chứa nội dung nên phải scan trước khi xuất bản.

Ưu tiên cải thiện: (1) schema validation/repair cho data và code; (2) giảm vòng gọi model/verification dư, giữ independent checks; (3) đo cache/persistent matplotlib worker trong **thí nghiệm riêng** với isolation rõ, không thay runtime freeze; (4) benchmark lặp lớn hơn, pacing/mixed load, observed rate-limit retries và invoices trước khi đánh giá production/cost. Chưa gọi thử nghiệm cuối là thành công tuyệt đối: live còn hai lỗi và complex latency vượt target.

Official OpenAI documentation tham khảo cho tool loop và retry (gateway không bảo đảm cùng giá/khả năng):
- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/api/docs/guides/rate-limits

## Bàn giao

Evidence mới không ghi đè benchmark cũ. Code live cuối chỉ gọi bằng `--mode live`, cần ignored `.env`; tests/default/debug/profile offline không cần key. Commands trong README extension và `report/REPRODUCE.md`. Bài chính test/freeze được kiểm riêng; chưa commit/push, dừng để người dùng xem checklist.
