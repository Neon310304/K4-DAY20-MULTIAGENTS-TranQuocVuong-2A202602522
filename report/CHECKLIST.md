# Checklist kiểm tra bài Day20

Đối chiếu README, GUIDE và RUBRIC; mọi dấu hoàn thành có artifact hoặc output thật. Đã xuất bản GitHub theo yêu cầu người dùng ngày 2026-10-06; chưa xác nhận nộp VLearn.

- [x] Repo đúng tên cá nhân; đã đọc hướng dẫn và tạo IMPLEMENTATION_PROMPT.md.
- [x] Môi trường Linux/Python >= 3.11 và Deep Agents 0.7.21; Docker hỗ trợ chạy trên Windows.
- [x] Cài TODO trong bốn module; giữ nguyên file được cung cấp, prompt, tasks, scripts và tests.
- [x] 29 test offline pass; backend không kế thừa API key, đường dẫn file/shell thống nhất.
- [x] Tour Deep Agents đã chạy và lưu report/tour.txt.
- [x] Baseline và subagents có run.json/trace.md hợp lệ cho sáu tác vụ mỗi điều kiện.
- [x] Phân loại toàn bộ 16 failed check baseline học, có evidence; tách pilot CRLF khỏi lỗi agent.
- [x] Curator sinh hai skill hợp lệ từ tập học; đánh giá cả ba lượt sinh, raw output lưu riêng, không sửa tay skill.
- [x] Có bản sao skills-auto-dev của ba tác vụ học trước freeze, cùng hash bộ skill cuối.
- [x] Commit hypotheses 1046d17 chứa H1–H3 trước freeze 19722e5; skill không đổi sau tag.
- [x] Skills-auto có sáu kết quả chính thức đúng hash, skills_modified=false và timestamp sau freeze.
- [x] verify_freeze: checked 6 runs of skill conditions: OK; table.md có ba condition/sáu task và tổng hợp.
- [x] REPORT.md đủ 10 mục; tách token/quy ước/kỹ thuật, hạn chế body không đọc, overfitting/leakage/nhiễu có số thật.
- [x] Audit Git/artifacts/history không phát hiện key; .env không được track, protected files/AST giữ nguyên.
- [x] Tự kiểm cuối pass; người dùng yêu cầu push sau khi nhận báo cáo, đã xuất bản GitHub; chưa xác nhận nộp VLearn.

Mở rộng +5 của scaffold chính là tùy chọn, chưa chọn. Checklist gửi bổ sung có bonus 6c trong extension, đo/test riêng, không tự nhận điểm bonus hoặc trộn vào điều kiện chính. Không lấy các run CRLF thử nghiệm làm kết quả chính; không thay failed check bằng số đẹp hơn.

## Evidence nhanh

- `offline-tests.txt`: 29 passed; `offline-tests-final.txt`: 29 passed in 8.64s sau Phần 5.
- `offline-tests-part6.txt`: 29 passed in 7.62s; `freeze-check-part6.txt`: checked 6 runs of skill conditions: OK.
- `freeze-check.txt`: OK; `pip-check.txt`: No broken requirements found.
- `final-audit.json`: 18 official + 3 development; error=null, skills_modified=false; hash/bytes, score/token, secret scan đều hợp lệ.
- `table.md`, `check-breakdown.txt`, `statistics.json`: sinh trực tiếp từ results, không chọn lại score.
- `REPORT.md`: kết quả evaluation baseline 0.4306, subagents 0.2121, skills-auto 0.5973; không task nào hoàn hảo, rules đều fail và không body skill được đọc.

Việc **xuất bản** đã thực hiện: commit `09b6e16` chứa kết quả/báo cáo/extension đã push tới `origin/main`, tag `freeze` giữ nguyên `19722e573b8d3ea8dcfd9c7968d068fdbba01b42`. Đã đối chiếu hash bằng `git ls-remote`. Repo: https://github.com/Neon310304/K4-DAY20-MULTIAGENTS-TranQuocVuong-2A202602522. Người dùng còn cần nộp link VLearn; chưa xác nhận bước này.

## Đối chiếu riêng Phần 0

- [x] GitHub xác nhận repo cá nhân là fork của VinUni-AI20k/K4-L3L4-Track3-Day20-AdvanceMultiAgents; origin đúng URL.
- [x] Repo có trên máy đúng tên và chứa đủ src/tasks/tests/guides/report.
- [ ] Mở thư mục repo trong VS Code: CLI có sẵn, chưa xác nhận cửa sổ của người dùng đang mở đúng workspace.
- [x] Môi trường Python Linux/Docker đã cài package editable và dependency; dùng thay venv Windows theo README thật.
- [x] .env cục bộ có cấu hình YesScale tương thích OpenAI; Git bỏ qua, không được track hoặc chứa trong báo cáo.
- [x] tests/test_01_provided.py: 12 passed, lưu setup-provided-tests.txt.
- [x] make_model().invoke('Reply with OK'): OK, lưu setup-model-check.json (11 token).
- [x] REPORT.md dựa trên REPORT_TEMPLATE.md, đã đọc README.md và GUIDE.md (không có LAB_GUIDE.md).
- [x] Mục 3 báo cáo có đủ ba câu về agent, delegation và shared tools, dựa trên code thật thay vì ví dụ giả định.
- [x] Agent definitions, tools, backend và config được kiểm tra; freeze vẫn OK, chưa push.
- [x] Mục 3 có bảng tám thuật ngữ kiến trúc và sơ đồ luồng thật; phân biệt delegation/shared workspace với handoff/toàn bộ shared state.

Native .venv/requirements.txt/OPENAI_API_KEY đơn lẻ trong checklist chung không phải cách chạy của scaffold này; không tạo file hoặc sửa module được cung cấp chỉ để giống ví dụ. Trên Windows mở repo bằng `code D:\Python\K4-DAY20-MULTIAGENTS-TranQuocVuong-2A202602522` nếu chưa mở.

## Tài liệu Coordinator được gửi bổ sung

- [x] Đối chiếu từng trách nhiệm/API với scaffold thật, lưu COORDINATOR_REVIEW.md; không nhận API hoặc test chưa tồn tại là hoàn thành.
- [x] Test agent/runner liên quan: 15 passed, lưu coordinator-harness-tests.txt; verify_freeze vẫn kiểm 6 run OK.
- [x] Coordinator class/parser/async executor/aggregator/retry độc lập đã triển khai trong extensions/multiagents/ khi nhận yêu cầu Phần 3; không sửa harness đã freeze.
- [x] Test Coordinator trong extension pass; standalone 3/3 (mock workers, không API), evidence ở extensions/multiagents/evidence/.

Phần bổ sung này không được tính là benchmark hoặc bonus đã hoàn thành; code/skills/results đã freeze giữ nguyên.

Nhận xét này áp dụng Coordinator Phần 2/3; bonus 6c riêng được bổ sung ở Phần 6 dưới đây, không là bonus thí nghiệm self-evolving chính.

## Phần 3: Worker Agents & Communication (mở rộng riêng)

- [x] Đọc yêu cầu BaseWorker/worker tools/queue; triển khai package day20_multiagents riêng, không nhận nhầm là module được cung cấp trong scaffold.
- [x] BaseWorker có process/process_async/_build_prompt/_execute_tool, đầy đủ message history/tool-call IDs, giới hạn iterations/calls và structured errors.
- [x] DataAgent có prompt chuyên môn, CSV parser/validation, pandas aggregates không eval, SQLite read-only với query/result limits.
- [x] CodeAgent có prompt chuyên môn, create/edit/run_script/Python subprocess, kiểm workspace paths, env tối thiểu và Linux resource limits; chỉ dùng trusted code, không coi là security sandbox.
- [x] EvaluatorAgent có prompt chuyên môn, scoring 30/30/20/20, validation/quality/feedback và kiểm schema JSON kết quả.
- [x] MessageQueue có async send/receive, UUID/UTC timestamp, JSON/size validation, bounded queue/log và bản sao dữ liệu.
- [x] Coordinator tích hợp queue, correlation run_id/task_id/sender, song song giữa workers, tuần tự cùng worker, deadline/cancel/partial failure và bounded idempotent retry.
- [x] Bốn test worker checkpoint pass (4 passed, 4 deselected); snapshot extension 57 passed sau Phần 5, hiện 68 sau Phần 6, bao gồm communication và integration với tools/artifact thật.
- [x] Evidence thật ở extensions/multiagents/evidence/; fake model không dùng key, không chứng minh chất lượng LLM thật.
- [x] Commit/push phần mở rộng theo yêu cầu người dùng; không thay tag freeze hoặc lịch sử thí nghiệm.

Hướng dẫn chạy và các giới hạn concurrency/security ở extensions/multiagents/README.md. Bộ 57 test extension tách khỏi 29 test harness chính; không cộng test hoặc thành tích extension vào bảng thí nghiệm chính.

## Phần 4: Tools & Hợp tác Agent (mở rộng riêng)

- [x] Đọc và đối chiếu tool architecture: BaseTool với validate_input/invoke/ainvoke/model_schema; toolkits riêng, không sửa root src/tools hoặc harness đã freeze.
- [x] QueryDatabaseTool có connect/close, cached readonly SQLite connection khóa theo thread, authorizer, progress/deadline và fetch limit 1–1000; test LIMIT có sẵn và recovery sau query lỗi.
- [x] DataAgent giữ CSV/pandas/validation và thêm AggregationTool finite numeric allowlist, không eval code.
- [x] PythonREPLTool/CreateFileTool/EditFileTool/RunScriptTool bind vào CodeAgent; validate paths/UTF-8 size, timeout, memory/CPU/file-size/FD limits, env tối thiểu, output truncation; trusted code only.
- [x] ScoringTool có trọng số 30/30/20/20 và grade A–F; ValidationTool dùng function adapter cũ, thêm ComparisonTool/ReportGeneratorTool để kiểm reference và ghi report.
- [x] Test database 50 sales 2026 + bản ghi 2025; demo chuyển SQL result sang Code Agent, sinh PNG thật, so SQL/code total cùng 1275 rồi ghi evaluation.md và queue trace.
- [x] Checkpoint tests/test_04_tools.py: 4/4 pass; tool integration standalone 3/3; toàn bộ extension 43 pass, không gọi API.
- [x] Tool log start/end/status/duration/error type không chứa query/code/content/key; demo evidence và artifacts riêng trong extensions/multiagents/evidence/.
- [x] Dependency bổ sung chạy trong venv riêng của container, không thay Python/packages của runtime thí nghiệm chính; hướng dẫn ở README extension và REPRODUCE.md.
- [x] Commit/push phần mở rộng theo yêu cầu người dùng; giữ nguyên tag freeze và kết quả benchmark chính.

Điểm demo 85.5/B là phép tính từ ratings cung cấp, không là benchmark chất lượng LLM. Python subprocess có resource limits nhưng không cách ly filesystem/network trước mã độc; không chạy input không tin cậy.

## Phần 5: Test, Debug & Performance (mở rộng riêng)

- [x] Unit/integration/E2E/edge/stress tests: 57/57 pass; tests/test_05_integration.py 14/14, ten concurrent requests, deadline/cancellation/reuse và independent artifact checks.
- [x] pytest -v --durations=10 và coverage: 92.2535% statements package; output thật ở extensions/multiagents/evidence/part5-tests-final.txt và coverage-final.json.
- [x] Có debug_system.py/debug_agent.py, JSON event logs, measured model/tool spans và queue correlation; không ghi key/raw arguments vào logger.
- [x] cProfile chạy năm request, profile.pstats/profile.txt/requests.json ở part5-profile-final/; phân biệt async waits với CPU/model service.
- [x] Ba cases benchmark, mỗi case ba iterations từ fixture sạch; offline và live riêng, thêm mười concurrent data requests với bốn slots.
- [x] Lưu min/max/avg/median/P50/P99, actual tokens hoặc null khi thiếu, throughput/error rate/worker occupancy và raw records/artifacts; không bịa USD hoặc 150k token.
- [x] Debug Docker quoted env, schema/assignment errors; regression tests và evidence lỗi cũ giữ nguyên, không chỉnh nguồn/checker để làm đẹp số liệu.
- [x] Live cuối simple 3/3, code 2/3, complex 2/3, load 10/10 = 17/19; 45316 token metadata. Báo cáo hai lỗi còn lại và target latency/error chưa đạt.
- [x] Mục 5–6 bổ sung ở extensions/multiagents/report/REPORT.md, liên kết từ REPORT.md chính; core 29 tests/18 runs/freeze không đổi.
- [ ] Production SLO: chưa đạt error <1%, code/complex latency/throughput; không tuyên bố ổn định mọi workload từ mẫu nhỏ.
- [x] Commit/push theo yêu cầu người dùng, không thay history/tag freeze.

## Phần 6: Final report và bonus độc lập

Báo cáo đủ 10 mục tại [extensions/multiagents/report/FINAL_REPORT.md](../extensions/multiagents/report/FINAL_REPORT.md); [REPORT.md](REPORT.md) chính dẫn tới báo cáo này, không đổi template self-evolving/benchmark đã freeze.

- [x] Mục 1: bài toán/goals/scope, phân biệt fixture extension với scaffold chính; bốn roles nhưng ba LLM workers.
- [x] Mục 2: architecture và message-flow diagrams, components, protocol/correlation và queue bounds.
- [x] Mục 3: implementation decisions, trade-offs/challenges, SQL reuse/subprocess/isolation/verification; không gọi Python limits là security sandbox.
- [x] Mục 4: 68/68 tests pass, 92.6650% statements (1137/1227), unit/integration/E2E/error coverage; snapshot 57 tests cũ giữ nguyên.
- [x] Mục 5: actual live/offline P50/P99/throughput/token; resource probe offline Linux 13/13 với parent RSS/CPU/children deltas và giới hạn đo.
- [x] Mục 6: evidence setup/schema/REPL errors, bounded retries/cancellation/partial results, không che hai live failures hoặc bịa fallback.
- [x] Mục 7: design-vs-implementation table; live error 10.53% và latency targets chưa đạt, không nhận production SLO pass.
- [x] Mục 8: local slots/workers/data limits, distributed broker/persistence/capability/invalidation considerations.
- [x] Mục 9: security/privacy/gateway pricing/sampling/scope/data/cache limitations.
- [x] Mục 10: kết luận/next steps, actual success counts, bàn giao dừng để review.
- [x] Bonus chọn 6c: opt-in readonly verified result cache, trusted scope/revision/namespace, TTL/LRU/payload limits, provenance/zero work hit; 11 tests mới pass.
- [x] Bonus evidence: cached/uncached 20/20 mỗi nhánh, 19 hits, mean 17.998→0.942ms, scripted calls 40→2; không nhận live API/token/USD savings hoặc điểm +5 đã chấm.
- [x] Commands/docs/evidence liên kết rõ, không ghi đè paid benchmarks; protected files/skills/freeze và secret audit kiểm riêng.
- [x] Commit báo cáo/kết quả/extension: `09b6e16`, sau yêu cầu push của người dùng.
- [x] Push các commit kết quả cuối và tag freeze lên GitHub; hash remote đã đối chiếu đúng.
- [ ] Dán link repo lên VLearn: người dùng thực hiện sau khi duyệt; chưa xác nhận nộp.

## Tổng hợp checklist Phần 0–6

| Phần | Hạng mục | Trạng thái/evidence |
| --- | --- | --- |
| 0 | Fork/clone, Linux môi trường, dependencies, ignored env/model smoke, đọc docs | Đã kiểm; setup-provided-tests.txt 12 pass, setup-model-check.json OK. Cửa sổ VS Code/activate native venv chưa xác nhận; Docker thay native theo README |
| 1 | Architecture, roles, protocol, ba câu trả lời | REPORT.md mục 3 và FINAL_REPORT.md mục 2; không lấy ví dụ agents/tools chưa tồn tại |
| 2 | Parse/route/execute/aggregate, timeout/retry, mock tests | extension Coordinator 10 tests, standalone 3/3; core không đổi |
| 3 | BaseWorker, Data/Code/Evaluator, queue, integration | Worker 8 tests, queue 4, integration/handoffs có tools/artifacts thật |
| 4 | SQL/Python/file/scoring/validation/tools E2E | Checkpoint 4/4, demo 3/3; trusted subprocess có limits, không adversarial sandbox |
| 5 | 23+ tests, benchmarks, bottlenecks, metrics/errors | Snapshot 57/57; offline 19/19/live 17/19; SLO chưa đạt nhưng phân tích/evidence đủ |
| 6 | Báo cáo 10 mục, bonus có code/tests/measurement | 68/68, coverage 92.6650%; FINAL_REPORT.md + part6-cache/part6-resources/ |
| Nộp | Commit/push GitHub và submit VLearn | **Đã push GitHub/tag freeze; VLearn chưa xác nhận** |

Evidence tự kiểm mới: `extensions/multiagents/evidence/part6-tests.txt`, `part6-coverage.json`, `part6-cache/cache_results.json`, `part6-resources/resource_results.json`, `report/offline-tests-part6.txt`, `report/freeze-check-part6.txt`, `report/final-audit.json`. Không cộng test extension vào số provided core hoặc thành tích cache vào bảng thí nghiệm chính.
