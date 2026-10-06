# Coordinator, Workers, Communication & Tools — mở rộng riêng

Triển khai yêu cầu Phần 2/3/4/5/6 được gửi bổ sung, **không thay scaffold Deep Agents đã freeze**. Toàn bộ code, test và evidence nằm ở đây; không sửa `src/lab/`, `tests/`, `tasks/`, `scripts/`, skills hoặc bảng benchmark chính. Các test dùng model giả/worker giả, không yêu cầu API key và không gọi API trả phí. Benchmark Phần 5 có cả offline và live YesScale riêng; không nhận thành tích model thật từ fake tests hoặc trộn vào thí nghiệm chính. Báo cáo cuối đủ 10 mục ở [report/FINAL_REPORT.md](report/FINAL_REPORT.md).

## Thành phần

```text
src/day20_multiagents/
  coordinator.py                  # parse, route, execute, aggregate, retry
  agents/base_worker.py            # sync/async model + tool loop
  agents/data_agent.py             # CSV, pandas aggregates, read-only SQLite
  agents/code_agent.py             # create/edit file, Python subprocess, run script
  agents/evaluator_agent.py        # scoring, validation, structured feedback
  communication/message_queue.py  # bounded async queue + immutable log snapshots
  tools.py                        # BaseTool, function adapter, validation, logs, Python limits
  toolkits/database_tools.py      # cached read-only SQLite, numeric aggregation
  toolkits/code_tools.py          # Python REPL, create/edit file, run script
  toolkits/evaluation_tools.py    # weighted scoring, comparison, Markdown report
  system.py                       # request-isolated E2E, admission/deadline, ordered handoffs
  runtime.py                      # deterministic offline driver, opt-in live model factory
  observability.py                # measured model/tools, actual token usage, JSON events
  benchmarking.py                 # percentile, throughput, failures, utilization, repeated cases
  caching.py                      # opt-in verified readonly cache with scope/revision/TTL/LRU
tests/                            # separate from protected root tests/
scripts/test_coordinator_standalone.py
scripts/test_tool_integration.py  # SQL -> PNG chart -> comparison/report, no API
scripts/benchmark.py              # three repeated cases + concurrent load, explicit offline/live
scripts/debug_system.py
scripts/debug_agent.py
scripts/profile_system.py
scripts/benchmark_cache.py        # independent offline bonus comparison, includes cold miss
scripts/measure_resources.py      # Linux offline parent RSS/CPU, child CPU deltas
report/REPORT.md                  # Part 5 sections 5-6, actual metrics and failure analysis
report/FINAL_REPORT.md            # Part 6 final ten sections + bonus appendix
evidence/                         # actual offline command outputs
```

- `BaseWorker.process()` và `process_async()` gửi `SystemMessage`/`HumanMessage`, bind tool schemas, xử lý **mọi** call trong response bằng `args`, giữ đầy đủ history và gửi `ToolMessage` đúng call ID. Counts là biến cục bộ từng request; model/tool/unknown-tool/iteration error trả structured error. Tối đa 12 iterations mặc định, 16 tool calls/response; `CancelledError` được truyền ra để coordinator hủy.
- Ba workers có bộ tool riêng và system prompt riêng. Data tool pandas chỉ nhận operation allowlist, không eval code; aggregation chỉ nhận finite numbers. SQLite mở mode=ro, authorizer chặn writes/DDL/unsafe operation, deadline/progress limit và giới hạn kết quả 500 rows mặc định (cấu hình 1–1000); không nối thêm LIMIT vào SQL đã có LIMIT. Connection cache khóa RLock để dùng với async thread wrappers; owner gọi DataAgent.close()/QueryDatabaseTool.close() khi xong. Evaluator weights 30/30/20/20 và grade A–F, kiểm JSON fields/types/range trước khi trả success; scoring chỉ cân trọng số điểm cung cấp, không suy accuracy từ độ dài câu trả lời.
- BaseTool cung cấp model_schema/validate_input/invoke/ainvoke, kiểm keys/types/ranges/JSON/size trước execution. Tool class là adapter cho CSV/pandas/validation/quality/feedback hiện có; concrete tools mới dùng cùng hợp đồng và bind trực tiếp vào workers. Logs ghi tên tool/start/end/status/error type/duration, không ghi query/code/content/exception message để tránh lộ dữ liệu hoặc key. stdout/stderr được trả giới hạn 8 KiB mỗi stream, có cờ truncated; ToolMessage có cả name và call ID.
- ComparisonTool so sánh scalar fields với reference rõ ràng, có absolute numeric tolerance và phân biệt bool với number; không coi reference rỗng là đạt. ReportGeneratorTool kiểm schema evaluation, ghi Markdown với supplied evidence, chỉ khi EvaluatorAgent được cấp workspace; chặn traversal/symlink escape và overwrite qua CreateFileTool. RunScriptTool giữ __file__/__name__/sys.argv và cho phép import sibling module như script thật, trong cùng subprocess limits.
- Queue gửi bản sao thay vì sửa dict đầu vào, gán UUID và UTC timestamp, kiểm agent đã đăng ký, JSON/size limit, backpressure/send timeout, receive timeout và log bounded 1000 entries mặc định. Re-register không xóa pending messages; log getter trả bản sao, filter theo agent.
- Coordinator dùng regex fast-path hoặc model JSON được validate, kiểm worker tồn tại, task ID duy nhất, tối đa 32 tasks. Có một dispatcher cho mỗi worker: worker khác nhau song song, các task cùng worker nối tiếp để tránh trộn conversation/model state. Một collector ghép theo run_id/task_id và người gửi; kết quả trả theo thứ tự input, không theo completion order. Reply channel riêng từng batch ngăn bắt nhầm kết quả cũ; chỉ cho một batch hoạt động trên coordinator tại một thời điểm.
- `execute_tasks()` là **async**, dùng deadline cả batch, giữ kết quả đã xong, pending trả timeout và coroutine bị cancel/drain. `aggregate_results()` giữ nhiều kết quả cùng type, trả success/partial/error và errors rõ ràng. Retry chỉ với task khai báo `idempotent=True`, tối đa 3 retries cấu hình; không bịa fallback thành công. Parse model trong handle_request chạy off event loop; deadline execute không bao gồm parse.
- Logger ghi worker/task start/end/status/duration, cancellation/timeout; không tự log task content. Queue log chứa payload và có thể chứa dữ liệu nhạy cảm do caller đưa vào: không gửi key/credentials trong content/parameters và không xuất log chưa rà soát.

## Chạy trong Docker đã có của bài

Từ repo gốc trên PowerShell:

```powershell
docker start day20-lab
docker exec day20-lab python -m venv --system-site-packages /opt/day20-tools-venv
docker exec day20-lab /opt/day20-tools-venv/bin/python -m pip install -e "/lab/extensions/multiagents[test]"
docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python -m pytest tests/ -o "addopts=-p no:cacheprovider" -q
docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python scripts/test_coordinator_standalone.py
docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python -m pytest tests/test_04_tools.py -o "addopts=-p no:cacheprovider" -v
docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python scripts/test_tool_integration.py
docker stop day20-lab
```

Image `Dockerfile.day20` đã có langchain-core/pytest/pandas; venv bổ sung matplotlib và extension mà không đổi packages của runtime thí nghiệm chính. Trên Linux venv riêng, dùng `pip install -e "extensions/multiagents[test]"`, sau đó chạy `python -m pytest extensions/multiagents/tests/ -q`. Không cần sửa pyproject.toml gốc. Python execution/file-symlink tests chạy trên Linux/Docker; không coi Windows native là runtime code tool.

Demo mặc định tạo workspace tạm và dọn sau khi chạy. Muốn giữ artifacts, thêm `--output <new-directory>` vào script; directory phải chưa tồn tại, không ghi đè demo cũ. Bản demo đã giữ ở `evidence/tool-demo/`: 50 sales năm 2026 (loại bản ghi 2025), SQL total và code total cùng 1275, PNG thật 11765 bytes, evaluation.md, summary.json và sáu queue messages. Test/checkpoint outputs ở `evidence/tool-checkpoint.txt`, `evidence/tool-integration.txt`, `evidence/extension-tests.txt`. Font cache tự sinh được Git bỏ qua; code mới đặt MPLCONFIGDIR vào thư mục subprocess tạm.

## Kết quả và giới hạn

Evidence offline được sinh từ commands thật, không chép output mẫu. Snapshot Phần 5: **57 test pass**, **92.2535% statement coverage**; sau bonus Phần 6: **68 test pass**, **92.6650% statement coverage** cho package, bốn test tools checkpoint **4/4**, Coordinator standalone **3/3** và tool integration **3/3**. Test coverage gồm bốn hành vi worker chính, năm Coordinator methods, multiple tool calls/history, error/model/input/schema/iteration limits, SQL read-only/cache concurrency/timeout/recovery, path traversal/symlink/overwrite, Python timeout/memory/resource limits/secrets/output truncation/script semantics, payload-free logging, scoring/comparison/report validation, bounded queue, parallel barrier, out-of-order correlation, same-worker serialization, partial failure, cancellation/reuse/stale messages và bounded idempotent retry. E2E mới kiểm request → artifact/independent checks, 10 concurrent requests, whole-request timeout/reuse, quoted environment và missing usage; không gọi network trong tests.

Collaboration chạy tuần tự data → code → evaluator, truyền SQL result thật vào task/code và so tổng từ stdout với SQL trước khi viết report. Biểu đồ dùng matplotlib Agg, được decode/verify bằng Pillow. Các ratings demo 85/90/80/85 cho score 85.5 (B) là **inputs cho phép tính**, không phải độ chính xác đo bằng LLM. Integration model output vẫn scripted: nó chứng minh plumbing và tool outputs, **không** đo chất lượng LLM hoặc evaluator độc lập.

Python REPL không phải security sandbox: subprocess có cwd workspace, env tối thiểu, Linux CPU/memory/file-size/file-descriptor limits, timeout giết process group và output bị truncate. Không dùng exec trong process coordinator hoặc blacklist import dạng chuỗi làm security boundary; mỗi call là subprocess mới, không giữ globals REPL giữa các call. Nhưng Python vẫn có thể truy cập filesystem/network mà user/container cho phép; chỉ chạy **trusted code** trong container hạn quyền, không chạy input thù địch. Direct file tools resolve path và chặn escape/symlink, không loại trừ race với tiến trình khác; không cho worker có quyền tạo symlink adversarial cạnh bên. SQLite readonly không đồng nghĩa an toàn mọi query đối kháng. Query/tool results và queue log có thể chứa dữ liệu nhạy cảm: chỉ xuất evidence đã rà soát, không gửi secrets qua tool/task payload.

Async wrappers cho sync model/tool dùng `asyncio.to_thread`; cancel coroutine không giết thread đang chạy. Python tool còn giới hạn runtime riêng, native model cần request timeout phía SDK và các sync tools khác phải bounded. Queue chỉ dùng trong một event loop/process, không bền vững, không distributed broker, một coordinator sở hữu worker queues; cancellation có thể bỏ pending task của batch cũ, không có delivery guarantee/exactly-once. Retry deadline áp dụng mỗi batch/attempt, không deadline chung toàn bộ retries. Với task phụ thuộc output data để viết report, chạy hai stage theo thứ tự, không gửi song song hai task phụ thuộc.

## Phần 5: Test, Debug và Performance

Từ thư mục extension trong Linux/venv đã cài `pip install -e ".[test]"`:

```bash
python -m pytest tests/ -v --durations=10 --cov=day20_multiagents --cov-report=term-missing
python scripts/debug_agent.py --agent data_agent --task "Calculate Q3 revenue"
python scripts/debug_system.py --output evidence/replay-debug
python scripts/profile_system.py --output evidence/replay-profile
python scripts/benchmark.py --mode offline --output evidence/replay-offline
```

Trong Docker, dùng tiền tố `docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python` thay `python`. `--output` phải là directory mới, giữ nguyên các folder `part5-*` đã dùng trong report. `MultiAgentSystem` là demo có fixture Q3/table sales/CSV schema cố định, không một hệ thống tự hiểu mọi loại database/user request; max_concurrency mặc định 4, resources mới mỗi request. Complex chuyển data_result sang code, actual artifact sang evaluator; deadline gồm admission wait, parse, tất cả stages và kiểm chứng. Caller cancellation vẫn truyền ra. Khi request kết thúc, workspace tạm dọn; benchmark/debug lưu copy bốn output paths cho phép (tối đa 64 KiB/file) với SHA256 trước khi dọn.

Live chỉ chạy khi chủ động chọn và có ngân sách/key; không truyền key qua argument/chat hoặc commit `.env`. Cài optional dependency vào venv riêng và chạy từ repo gốc:

```powershell
docker exec day20-lab /opt/day20-tools-venv/bin/python -m pip install -e "/lab/extensions/multiagents[test,live]"
docker exec --env-file .env -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python scripts/benchmark.py --mode live --output evidence/replay-live
```

Factory đọc `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`/`AZURE_OPENAI_API_KEY`/`OPENAI_API_KEY` và `AZURE_OPENAI_DEPLOYMENT_MODEL`/`LLM_MODEL`, chuẩn hóa cặp nháy Docker env-file. Timeout SDK 30s/max_retries=2; application không retry quanh code/file side effects. Whole-request timeout mặc định 90s. Python subprocess vẫn không kế thừa keys. Official OpenAI documentation về tool loop/retry được tham khảo; không áp biểu giá OpenAI để tính gateway USD.

`evidence/part5-tests-final.txt`, `coverage-final.json`, `part5-profile-final/`, `part5-debug-final/`, `part5-offline-final/`, `part5-live-final/` là outputs cuối. Live **17/19 verified** (simple 3/3, code 2/3, complex 2/3, concurrent data 10/10), **45316 tokens**, không che hai lỗi. Các run `part5-live/` và `part5-live-fixed/` giữ lỗi setup/schema trước sửa, không trộn với final. Phân tích chi tiết và benchmark table ở `report/REPORT.md` của extension: lỗi rows list, REPL không giữ import, model/API bottleneck, latency/error targets chưa đạt. Không nhận 85.5/B là quality judge; đây là scoring-formula input fixture.

Tag freeze, 18 run chính thức và các giả thuyết của bài chính không thay đổi. Không gán benchmark extension vào `report/table.md` của repo gốc; chưa commit/push.

## Phần 6: Báo cáo cuối và bonus 6c

[report/FINAL_REPORT.md](report/FINAL_REPORT.md) đủ 10 mục: scope, architecture/message diagrams, implementation/trade-offs, tests, performance/resources, errors/resilience, design-vs-implementation, scalability, limitations, conclusion. Giữ kết quả live **17/19**, hai lỗi schema/REPL và SLO chưa đạt; không đổi paid benchmark để cải thiện điểm.

`CachedDataSystem` chỉ cache structured readonly `data_analysis` với empty parameters; strings/code/complex/evaluation/debug bypass. Scope/revision/namespace phải do caller tin cậy cấp (không là auth), TTL default 60s, LRU 128 entries, tối đa 64 KiB payload/entry. Chỉ lưu kết quả independent checks thành công, không files/traces; hit UUID mới, zero current model/API/token counts và provenance nguồn. Không single-flight, distributed cache hoặc stale-data guarantee nếu caller cấp sai revision. Không bật mặc định trong system/benchmark Phần 5.

Trong extension Linux/venv, chạy offline với folder mới:

```bash
python -m pytest tests/ -v --cov=day20_multiagents --cov-report=term-missing
python scripts/benchmark_cache.py --iterations 20 --output evidence/replay-cache
python scripts/measure_resources.py --output evidence/replay-resources
```

Evidence `part6-tests.txt`/`part6-coverage.json`: **68 passed in 12.79s**, **1137/1227 statements**. `part6-cache/cache_results.json`: cả hai nhánh **20/20**, 19 hits, mean **17.998 → 0.942ms**, scripted calls **40 → 2**; không là paid API/token savings. `part6-resources/resource_results.json`: **13/13 offline**, parent sampled peak **94272–98932 KiB**, CPU/children deltas và phương pháp/giới hạn đo trong báo cáo. Không cộng thành tích cache vào benchmark main hoặc nhận bonus đã được chấm. Dừng chờ checklist review, chưa commit/push/nộp VLearn.
