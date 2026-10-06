# Đối chiếu Phần 2 — Coordinator Agent

## Phạm vi

Tài liệu Phần 2 được gửi bổ sung mô tả một scaffold Coordinator riêng. Repo Day20 hiện tại là Deep Agents harness: không có `src/coordinator.py`, `src/base_agent.py`, `tests/test_02_coordinator.py` hoặc `scripts/test_coordinator_standalone.py`. README/GUIDE/RUBRIC trong repo yêu cầu hoàn thiện bốn module `src/lab/`, không sửa bộ test/task/script được cung cấp. Không thể nhận “5/5 Coordinator tests pass” khi những test đó chưa tồn tại.

Benchmark đã freeze tại `19722e5`. Đối chiếu dưới đây mô tả harness chính, không thay main prompt, skill hoặc số liệu đã đo. Sau khi nhận tiếp yêu cầu Worker/Communication, Coordinator độc lập đã được triển khai **ngoài harness** tại `extensions/multiagents/src/day20_multiagents/coordinator.py`, cùng worker/queue/test riêng. Bảng bên dưới vẫn là đối chiếu scaffold gốc, không phải trạng thái của phần mở rộng.

## Yêu cầu và implementation hiện có

| Yêu cầu bổ sung | Implementation / evidence | Đánh giá chính xác |
| --- | --- | --- |
| Khởi tạo coordinator, workers, queue, logger | `build_agent()` tạo graph với backend/model và các custom worker từ `get_subagents()` | Có factory main agent và worker definitions; không có class Coordinator, MessageQueue hay active_tasks registry riêng |
| Nhận request | `run_task()` gửi task instruction bằng user message vào `agent.invoke()` | Nhận text qua messages; không có parser cho structured request riêng |
| parse_request: type, params, priority | Main LLM quyết định bước tiếp qua agent loop | Không có hàm parse_request, schema task_type/parameters/priority hoặc regex fast-path |
| route_task | Main gọi tool task với description và subagent_type | Routing theo tool/model, không có routing_map cố định data_agent/code_agent/evaluator_agent |
| execute_tasks song song, chờ 60 giây | Framework xử lý tool calls; runner đặt recursion_limit=60; timeout shell/model mỗi lệnh/request là 120 giây | Không có asyncio executor do bài làm tự xây, deadline 60 giây cho cả nhóm worker, hay chứng minh các worker đã chạy song song |
| aggregate_results và verification | Báo cáo worker về main bằng tool result; main có thể đọc artifact/chạy test rồi trả lời cuối | Không có schema aggregate status/data/code/evaluation/timestamp hoặc validator bắt buộc. Trace benchmark cho thấy main có lúc chưa kiểm chứng đủ |
| Worker error | runner bắt exception, ghi error, vẫn grade và lưu artifact, dọn sandbox | Có xử lý lỗi ở cấp run; không phải per-worker result registry/fallback |
| Timeout / resource exhaustion | Giới hạn graph steps và timeout mỗi lệnh/request; error được lưu | Không có admission limit theo số task, deadline toàn run, hoặc cancellation policy tự cài |
| Retry | Có thể có retry kỹ thuật của SDK/framework | Không cài execute_tasks_with_retry, số lần retry/fallback nghiệp vụ; không nhận có retry idempotent được test |
| Logging | run.json chứa token/seconds/counts/checks/error; trace.md chứa messages/tool calls main | Không có log start/end/duration riêng từng worker; trace không thấy tool bên trong worker |

## Kiểm chứng ngoại tuyến

Chạy trên runtime Linux/Docker bằng fake model, không gọi API trả phí:

```text
python -m pytest tests/test_02_agent.py tests/test_03_runner.py -o "addopts=-p no:cacheprovider" -q
15 passed in 2.84s
python scripts/verify_freeze.py
checked 6 runs of skill conditions: OK
```

Output test lưu ở `coordinator-harness-tests.txt`. Chín test agent kiểm factory/backend/tools/subagent/skill; sáu test runner kiểm record, workspace isolation, error capture, skill hash và counts. Chúng không kiểm parser/aggregator/async timeout/retry của class Coordinator giả định; không đổi tên chúng thành test Coordinator standalone. Bộ đầy đủ gần nhất vẫn là 29 test harness pass, lưu `offline-tests-final.txt`.

## Coordinator độc lập đã bổ sung

Code/test/evidence của phần mở rộng được tách khỏi `src/lab/`, `tests/`, `tasks/`, `scripts/`, `skills/auto/` và results chính. Dùng worker giả và model giả để kiểm request/schema, routing, aggregation, timeout/cancellation, partial failure và retry có giới hạn, không cần API key. API execute/handle_request là async; một collector ghép run_id/task_id/sender, deadline hủy pending và giữ partial results, retry chỉ task idempotent. Bộ extension hiện 57 test pass sau Phần 5, Coordinator standalone 3/3. Benchmark live extension tách riêng và ghi nhận lỗi, không gán hiệu quả vào bảng benchmark cũ hoặc nhận bonus.

Xem `extensions/multiagents/README.md` và `extensions/multiagents/evidence/` để chạy Coordinator mới và đọc kết quả offline. Không nhận test mở rộng là test được giảng viên cung cấp hoặc gán hiệu quả vào benchmark gốc; chưa push GitHub.
