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

Tạo `.env` từ mẫu và tự điền `AZURE_OPENAI_ENDPOINT` (base URL gateway), `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT_MODEL=gpt-4.1-mini`, `LAB_TEMPERATURE=0`. Không commit .env. Có thể tạo container theo lệnh trên với thêm `--env-file .env`; backend agent vẫn dùng inherit_env=False và env tối thiểu.

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
