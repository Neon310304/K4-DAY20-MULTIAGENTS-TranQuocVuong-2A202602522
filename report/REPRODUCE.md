# Chạy lại Day20

Trên Windows dùng Docker Desktop; trên Linux có thể dùng venv theo README. Các thao tác sau chạy từ thư mục gốc repo.

## Môi trường Docker

```powershell
docker build -f Dockerfile.day20 -t day20-deepagents:local .
docker run -d --name day20-lab --mount "type=bind,source=$($PWD.Path),target=/lab" -e PYTHONPATH=/lab/src day20-deepagents:local sleep infinity
docker exec day20-lab git config --global --add safe.directory /lab
docker exec day20-lab python -m pytest tests/ -o addopts="-p no:cacheprovider" -q
docker exec day20-lab python scripts/tour.py
docker exec day20-lab python scripts/verify_freeze.py
docker exec day20-lab python -m lab.compare
docker exec day20-lab python scripts/check_breakdown.py
```

Nếu container lab đã tồn tại, dùng `docker start day20-lab` thay vì tạo lại. Dockerfile.day20 giữ dependency của pyproject.toml và thêm Git cho kiểm tra freeze; .dockerignore loại .env khỏi build context. Bộ test không cần API key.

Repo có `.gitattributes` để các bản clone mới checkout text bằng LF. Một checkout Windows cũ dùng CRLF có thể làm checker hash báo `tests_not_modified` sai dù agent không sửa test. Lần đo này tạo runtime Linux bằng `git -c core.autocrlf=false archive HEAD`, giữ nguyên bytes từ Git của các file được cung cấp, sao chép bốn module đã cài đặt và ghi results/report lại repo qua bind mount. Không sửa checker, test, dữ liệu hoặc hash mong đợi để vượt lỗi. Các lượt thử CRLF được lưu riêng và không đi vào bảng chính.

## Model thật và trình tự thí nghiệm

Tạo `.env` từ mẫu và tự điền `AZURE_OPENAI_ENDPOINT` (base URL gateway), `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT_MODEL=gpt-4.1-mini`, `LAB_TEMPERATURE=0`. Không commit .env. Với mỗi lệnh live trong container, dùng `docker exec --env-file .env day20-lab python ...`; backend agent vẫn dùng inherit_env=False và env tối thiểu. Không viết giá trị key vào argument hay tài liệu.

Lần đo nộp bài dùng YesScale, key đã có ở Day19 được truyền riêng qua stdin cho bootstrap, khi đo không lưu .env Day20 hoặc cấu hình startup container. Khi đối chiếu checklist Phần 0 sau đó, tạo thêm .env cục bộ Day20 bằng đúng gateway/model đã dùng; file này được Git bỏ qua và không được đưa vào artifacts. Bootstrap chỉ đồng bộ bốn module TODO và bản skill nguồn, đặt LAB_ROOT/PYTHONPATH cho runtime LF, rồi chạy đúng CLI phía dưới. Khác biệt Windows được xử lý trước tập học chính thức; mọi lượt chính dùng cùng runtime và package versions trong report/environment.txt.

Repo thật không có requirements.txt, LAB_GUIDE.md hoặc report/REPORT.template.md: dùng pip install -e ., GUIDE.md và REPORT_TEMPLATE.md. Với gateway YesScale, chỉ OPENAI_API_KEY không đủ để make_model() chọn gateway; cần ba biến AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_KEY/AZURE_OPENAI_DEPLOYMENT_MODEL theo .env.example. Không đổi model.py được cung cấp để khớp ví dụ chung của checklist. Docker thay môi trường venv Windows vì shell lab cần /bin/sh; không nhận đã kích hoạt .venv native.

Chạy tuần tự:

```text
python -m lab.runner --condition baseline --tasks learn
python -m lab.runner --condition subagents --tasks learn
python -m lab.curator
python -m lab.runner --condition skills-auto --tasks learn
```

Sau khi đánh giá skill và viết H1–H3, sao lưu `results/skills-auto` thành `results/skills-auto-dev`, commit hypotheses, commit freeze skills và tag freeze, rồi:

```text
python -m lab.runner --condition baseline --tasks eval
python -m lab.runner --condition subagents --tasks eval
python -m lab.runner --condition skills-auto --tasks all
python scripts/verify_freeze.py
python -m lab.compare
python scripts/check_breakdown.py
```

Trong container dùng tiền tố `docker exec day20-lab` cho các lệnh Python. Khi kiểm chứng bài đã nộp, không cần chạy lại live hoặc thay tag freeze: tests/verify_freeze/compare/check_breakdown là đủ để đối chiếu artifacts. Muốn thí nghiệm mới, dùng bản sao repo hoặc thư mục results mới; không ghi đè output đã dùng trong báo cáo và không đổi skill đã freeze.

Khi kết thúc dùng `docker stop day20-lab`. Live model có dao động; số liệu lần chạy khác không bắt buộc giống output đã lưu.

## Phần 2/3/4/5 bổ sung: extension độc lập

Không thay package lab hoặc tag freeze để chạy Coordinator/Workers/Communication. Từ repo gốc, sau khi build container như trên:

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

Kỳ vọng 68 test extension pass sau Phần 6 (57 ở Phần 5, 43 ở checkpoint Phần 4), Coordinator standalone 3/3, tool checkpoint 4/4, tool integration 3/3; đây là tests mới viết, không phải tests do giảng viên cung cấp. Không truyền `.env`, không cần API key. Venv riêng dùng packages sẵn có và bổ sung matplotlib, không thay runtime thí nghiệm chính. Demo mặc định dùng workspace tạm; thêm `--output <new-directory>` nếu muốn giữ SQL database/PNG/report/queue trace, directory phải chưa tồn tại. Evidence và bản demo đã giữ ở `extensions/multiagents/evidence/`; kiến trúc, Linux runtime cho code tools và các giới hạn security/concurrency ở `extensions/multiagents/README.md`. Bộ 29 test harness chính vẫn chạy riêng, số liệu benchmark/freeze giữ nguyên.

Phần 5 tăng lên **57 test extension**, cài extras `[test,live]` vào venv riêng khi cần SDK live. Chạy thêm (từ extension directory trong Linux):

```bash
python -m pytest tests/ -v --durations=10 --cov=day20_multiagents --cov-report=term-missing
python scripts/debug_agent.py --agent data_agent
python scripts/debug_system.py --output evidence/replay-debug
python scripts/profile_system.py --output evidence/replay-profile
python scripts/benchmark.py --mode offline --output evidence/replay-offline
```

Trong Docker dùng Python venv với workdir/PYTHONPATH extension như trên. Live paid chỉ khi chủ động chạy `docker exec --env-file .env ... /opt/day20-tools-venv/bin/python scripts/benchmark.py --mode live --output evidence/replay-live`. Dùng **directory mới** cho mỗi lần, không ghi đè `part5-live-final/` đã phân tích; env được chuẩn hóa cặp nháy, key không vào child Python. Kết quả cuối/error/debug/coverage ở extension evidence, báo cáo mục 5–6 ở `extensions/multiagents/report/REPORT.md`. Live 17/19 verified, còn hai lỗi và SLO chưa đạt; không nhận fake tests/0-token offline là kết quả model thật, không thay freeze/run chính.

## Phần 6: Final report, cache và resource probe

Báo cáo cuối đủ 10 mục/bonus tại `extensions/multiagents/report/FINAL_REPORT.md`; báo cáo self-evolving chính vẫn riêng. Không cần paid API hoặc chạy lại benchmark main/Phần 5. Từ repo gốc:

```powershell
docker start day20-lab
docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python -m pytest tests/ -o "addopts=-p no:cacheprovider" -v --durations=10 --cov=day20_multiagents --cov-report=term-missing
docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python scripts/benchmark_cache.py --iterations 20 --output evidence/replay-cache
docker exec -e PYTHONPATH=/lab/extensions/multiagents/src -w /lab/extensions/multiagents day20-lab /opt/day20-tools-venv/bin/python scripts/measure_resources.py --output evidence/replay-resources
docker stop day20-lab
```

Kỳ vọng 68 tests pass; cache comparison cả hai nhánh 20/20, 19 hits/1 cold miss, scripted calls 40→2; resource probe 13/13. Thời gian/RSS khác giữa máy/lần chạy là bình thường. Hai scripts offline; `--output` phải mới, không ghi đè `part6-cache/`/`part6-resources/`. Hit cache giữ provenance và zero work counters; cache chỉ opt-in readonly structured requests, scope/revision/namespace phải do trusted caller quản lý, không security/auth boundary. Không áp cache cho side-effect file/code tasks hoặc sửa kết quả live.

Test evidence/coverage Phần 6 ở `part6-tests.txt`/`part6-coverage.json`; core tự kiểm riêng lưu `report/offline-tests-part6.txt`/`report/freeze-check-part6.txt`. Không cần rerun paid experiments/refreeze hoặc commit trước khi người dùng duyệt checklist. Publishing/submit vẫn chưa thực hiện.

## Mốc Git của bài làm

- `1046d17`: hypotheses, gồm H1–H3 và toàn bộ tập học/development; chưa có run evaluation.
- `19722e573b8d3ea8dcfd9c7968d068fdbba01b42`: freeze skills, tag `freeze`, thời gian commit 2026-10-06T13:05:56+07:00.
- Hash skill trên Linux: `9be2711716937db8adb26385ceb3e43c011bfdc7d7e3d243186d420363f20dca`.

Khi xuất bản sau duyệt bài, giữ cả lịch sử hai commit và tag freeze; không squash hoặc amend chúng. verify_freeze dùng Git nên bản tải ZIP không đủ để kiểm chứng protocol. Chạy kiểm tra trên Linux/Docker: hàm hash có sẵn dùng tên đường dẫn của hệ điều hành, nên Windows native không phải runtime đo này.
