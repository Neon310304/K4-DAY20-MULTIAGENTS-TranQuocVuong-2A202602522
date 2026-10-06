# Prompt thực hiện Day20

Hoàn thiện repo `K4-DAY20-MULTIAGENTS-TranQuocVuong-2A202602522` theo README, GUIDE, RUBRIC và REPORT_TEMPLATE. Làm tuần tự tới khi có bài làm kiểm chứng được; dừng để người dùng kiểm tra checklist, chưa push GitHub.

1. Dùng Linux trong Docker vì backend shell cần `/bin/sh`; cài đúng dependency và Deep Agents 0.7.21. Không đưa API key vào shell sandbox, Git hoặc trace.
2. Chỉ cài các TODO trong agent.py, subagents.py, runner.py và curator.py. Giữ nguyên prompt có sẵn, các module cung cấp, tests, scripts và tasks.
3. Backend dùng đường dẫn tương đối thống nhất cho file tools/shell và env tối thiểu. Subagents có phạm vi khác nhau; runner sao chép workspace vào thư mục tạm, cộng token kể cả subagent, ghi score/checks/trace/timestamp và hash skill, dọn sandbox kể cả khi model lỗi.
4. Chạy đủ 29 test offline và tour. Sau đó chạy baseline/subagents trên ba tác vụ học bằng cùng model và tham số, lưu kết quả thật. Chỉ dùng check/trace của tập học để phân loại lỗi và sinh skill.
5. Curator gọi model để tạo skill có frontmatter, quy trình tổng quát và chỉ dẫn có thể kiểm chứng. Validate mọi skill, không sửa tay đầu ra; lưu evidence nguồn curator. Kiểm thử skills-auto trên tập học và sao lưu kết quả phát triển.
6. Viết H1–H3 từ kết quả học trước khi xem điểm hoặc check riêng của tập đánh giá. Commit `hypotheses`, sau đó commit `freeze skills` và tag `freeze`; không đổi skill sau đó.
7. Chạy baseline/subagents trên tập đánh giá, skills-auto trên cả sáu tác vụ. Chạy verify_freeze, compare và check_breakdown; giữ đủ run.json/trace.md cho 18 lần chính thức cùng bản sao ba lần skills-auto phát triển.
8. Điền đủ 10 mục báo cáo: cấu hình, giả thuyết, công cụ Deep Agents, lỗi có evidence, subagent calls/delegation, đánh giá skill, bảng số thật, chi phí/quá khớp/rò rỉ/nhiễu, hạn chế và kết luận. Không tạo số liệu giả hoặc chỉnh kết quả cho đẹp; kết quả âm được giữ và giải thích.
9. Tạo checklist bàn giao dựa trên RUBRIC, xác nhận file có sẵn không bị sửa và không có key trong Git/results. Ghi lệnh tái lập trên Docker, freeze commit và các phần chưa thực hiện. Bonus là tùy chọn, không nhận nếu chưa có evidence.

Đầu ra: bốn module hoàn thiện, skill do model sinh, results thật, report/REPORT.md, report/table.md, freeze tag và validation pass. Việc nộp VLearn do người dùng xác nhận riêng.
