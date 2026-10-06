# Checklist kiểm tra bài Day20

Đối chiếu README, GUIDE và RUBRIC; đánh dấu chỉ khi có artifact hoặc output thật. Bản checklist sẽ được chốt sau thí nghiệm.

- [x] Repo đúng tên cá nhân; đã đọc hướng dẫn và tạo IMPLEMENTATION_PROMPT.md.
- [x] Môi trường Linux/Python >= 3.11 và Deep Agents 0.7.21; Docker hỗ trợ chạy trên Windows.
- [x] Cài TODO trong bốn module; giữ nguyên file được cung cấp, prompt, tasks, scripts và tests.
- [x] 29 test offline pass; backend không kế thừa API key, đường dẫn file/shell thống nhất.
- [x] Tour Deep Agents đã chạy và lưu report/tour.txt.
- [ ] Baseline và subagents có run.json/trace.md hợp lệ cho sáu tác vụ mỗi điều kiện.
- [ ] Phân loại ít nhất bốn failed check tập học, có evidence; tách lỗi hạ tầng.
- [ ] Curator sinh skill hợp lệ từ tập học; có đánh giá chất lượng, không sửa tay skill.
- [ ] Có bản sao skills-auto-dev của ba tác vụ học trước freeze.
- [ ] Commit hypotheses chứa H1–H3 trước commit/tag freeze; skill không đổi sau freeze.
- [ ] Skills-auto có sáu kết quả chính thức đúng hash, skills_modified=false và timestamp sau freeze.
- [ ] verify_freeze báo OK; table.md do lab.compare sinh, đủ ba điều kiện/sáu tác vụ.
- [ ] Báo cáo đủ 10 mục, phân tích token/quy ước/kỹ thuật/overfitting/leakage/nhiễu có số thật.
- [ ] Secret scan Git, artifacts và history không phát hiện key; .env không được track.
- [ ] Tự kiểm cuối pass; dừng để người dùng xem bài, chưa push/nộp VLearn.

Mở rộng +5 là tùy chọn, chưa chọn. Không lấy các run CRLF thử nghiệm làm kết quả chính; không thay failed check bằng số đẹp hơn.
