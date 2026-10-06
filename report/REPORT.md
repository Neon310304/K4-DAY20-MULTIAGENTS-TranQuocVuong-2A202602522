# Báo cáo Day20 — Self evolving Agentic

## 1. Thông tin và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
| --- | --- | --- |
| Trần Quốc Vương | 2A202602522 | Cá nhân: harness, subagents, runner, curator, thí nghiệm và phân tích |

Mô hình `gpt-4.1-mini` qua gateway YesScale tương thích OpenAI; nhiệt độ 0, recursion_limit 60 cho mọi điều kiện. Deep Agents 0.7.21, Python 3.12, Linux trong Docker Desktop trên máy Windows. Key chỉ được truyền vào tiến trình model, không chuyển vào shell của agent. Bài làm tuân thủ README/GUIDE/RUBRIC; chưa thực hiện mở rộng tùy chọn.

## 2. Giả thuyết

- H1 (subagents so với baseline): Dự đoán subagents không có điểm evaluation cao hơn baseline một cách ổn định. Tập học giảm 0.3954 → 0.3120, custom roles không được gọi và general-purpose báo hoàn thành không khớp file. Có thể tốn token hơn ở logs dù trung bình học thấp hơn; hướng dẫn 02_subagents cảnh báo isolation và chi phí, không suy con số 15 lần của nghiên cứu sang bài này.
- H2 (skills-auto so với baseline): Dự đoán kỹ thuật tương đương/dao động và không tăng rõ check quy ước trên evaluation; không dự đoán skills-auto sẽ thắng baseline. Development đọc 0 skill ở cả ba tác vụ, code/logs giữ nguyên điểm, data tăng 3/8 → 5/8 dù không có skill data. Hai skill hợp lệ có quy ước tốt nhưng không được đọc thì không có cơ chế truyền lợi ích; token có thể tăng do mô tả skill hoặc thêm vòng suy luận. GUIDE 05 mô tả progressive disclosure; guides/pseudocode/04_curator tóm tắt SkillsBench rằng skill tự sinh trung bình không có lợi (khác skill người viết); đây là căn cứ từ tài liệu lab, không phải bài báo tự kiểm chứng.
- H3 (tác vụ học so với tác vụ đánh giá): Dự đoán không có chuyển giao ổn định, evaluation không vượt learning rõ rệt và quy ước mới dễ thất bại. Development trung bình 0.4787 so với baseline 0.3954 chỉ nhờ data, trong khi rules vẫn 0/9 và skills_read=0; không thể gọi đó là học thành công. Hướng dẫn 04_curator tóm tắt SkillEvolBench về lợi ích learning không chuyển sang task mới; sẽ dùng lần chạy cùng skill sau freeze để tách nhiễu khỏi cải thiện, không xem evaluation trước khi chốt.

Ba giả thuyết ghi trước khi chạy/xem điểm hoặc check riêng evaluation. Chỉ đọc instruction chung trong tour/test có sẵn theo quy trình, không dùng eval trong curator; không chỉnh giả thuyết theo kết quả sau này.

## 3. Làm quen Deep Agents

Tour dùng model giả, không tốn API. Tool được cung cấp gồm `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`, `execute`, `task`; chạy lệnh qua `execute`. Deep Agents mặc định có `general-purpose`, cùng khả năng tool như main agent, nhưng mỗi invocation chỉ nhận prompt giao việc và trả một báo cáo cuối.

Trích tool task: “Each invocation is stateless by default: the agent sees only the prompt you give it and returns a single final report.” Trích execute: “You MUST avoid using search commands like find and grep. Instead use the grep, glob tools to search.” Tour xác nhận system prompt mặc định là chuỗi rỗng; harness này dùng BASE_PROMPT được lab cung cấp, không thay đổi nó.

## 4. Đường cơ sở và phân loại lỗi

Chỉ dùng ba run baseline học đã chuẩn hóa LF; evidence là `results/baseline/<task>/run.json` và `trace.md`. Đây là toàn bộ 16 check thất bại, không phải một mẫu chọn lọc.

| Tác vụ | Check thất bại | Nhóm | Evidence từ detail / trace |
| --- | --- | --- | --- |
| code-learn | rule_type_hints | E | “every public function ... type annotations on all parameters and on the return value” |
| code-learn | rule_regression_tests | E | “add tests/test_regressions.py ... at least 3”; trace chỉ chạy bộ test gốc |
| code-learn | rule_changelog | E | “CHANGELOG.md ... ## Unreleased ... - fix(<function name>): ...” |
| data-learn | north_q1_revenue | D | “wrong value (got 2314.87)”; process_sales.py dùng parser.parse(d), không chỉ định DD/MM/YYYY |
| data-learn | north_q1_orders | D | “wrong value (got 9)”; cùng lỗi chọn ngày/quý khi parser mặc định month-first |
| data-learn | rule_money_in_cents | E | “money values in answer.json are integer cents”; trace xuất doanh thu thập phân |
| data-learn | rule_meta_block | E | “meta ... source ... rows_in ... rows_used”; answer.json không có meta |
| data-learn | rule_clean_csv | E | “header order_id,timestamp_utc,region,amount_cents”; trace chỉ ghi answer.json |
| logs-learn | entry_count | D (B phụ) | “wrong number of entries (got 19)”; đọc log rồi chép JSON bằng write_file, không chạy parser |
| logs-learn | timestamps_utc | D (B phụ) | “8/25 timestamps match”; JSON chép tay không chuyển offset đúng |
| logs-learn | exception_fields | D (B phụ) | “17 wrong exception values”; không kiểm chứng liên kết traceback với entry |
| logs-learn | repeat_counts | D (B phụ) | “17 wrong repeat_count values”; không kiểm chứng dòng lặp với entry trước |
| logs-learn | counts_by_service | D (B phụ) | “wrong values”; tổng theo service dựa trên entries/repeats sai |
| logs-learn | rule_service_names | E | “lower-case with '-' replaced by '_'”; JSON giữ payment-service |
| logs-learn | rule_sorted_errors | E | “sorted by service, then by timestamp_utc, ascending”; giữ thứ tự log |
| logs-learn | rule_schema_header | E | “schema_version: 2 ... generated_by: log-triage”; thiếu header |

Nhóm chính E chiếm 9/16 (56.25%); D chiếm 7/16. Skill có thể truyền quy ước ẩn E nhưng vẫn cần workflow kiểm chứng D/B. Kỹ thuật baseline đạt 11/18: code 7/7, data 3/5, logs 1/6; quy ước đạt 0/9. Code đạt cả other_caller_fixed và hai docstring checks là bằng chứng phủ định cho việc quy toàn bộ lỗi thành A/C. Data đã sửa lỗi datetime aware/naive nhưng không sửa ngày nhập nhằng: chạy lệnh nhiều lần không đồng nghĩa kiểm chứng đúng. Logs không có execute trong trace, nên B là nguyên nhân thứ cấp có evidence; không suy nội dung không xuất hiện trong trace.

Tách hạ tầng: các pilot `*-crlf-pilot` không nằm trong bảng chính hoặc đầu vào curator. Windows CRLF làm hash test khác LF dù test không bị agent sửa; khắc phục bằng runtime Linux lấy bytes từ Git, không đổi checker/hash/task. Pilot subagents logs bị dừng khi chẩn đoán, không có run hoàn tất; không dùng làm lỗi của agent.

## 5. Điều kiện subagents

Định nghĩa explorer đọc đặc tả/dữ liệu nhưng không sửa; implementer thực hiện bước có phạm vi rõ và kiểm chứng; reviewer kiểm tra độc lập nhưng không sửa. Description nêu thời điểm nên giao việc; build_agent thêm PATHS_NOTE cho mỗi subagent. Main agent vẫn tự quyết định có gọi subagent; số liệu sẽ lấy từ trace và subagent_calls.

| Tác vụ học | Baseline token | Subagents token | Calls task | Subagent thực sự gọi | Điểm baseline → subagents |
| --- | ---: | ---: | ---: | --- | --- |
| code-learn | 32826 | 35871 | 0 | Không | 7/10 → 7/10 |
| data-learn | 150119 | 47998 | 1 | general-purpose | 3/8 → 1/8 |
| logs-learn | 24808 | 73216 | 2 | general-purpose | 1/9 → 1/9 |

Không có bằng chứng custom explorer/implementer/reviewer được dùng ở tập học. code-learn tự làm và qua kỹ thuật; lời nhắc delegation không bắt buộc được model làm theo. Data truyền đủ đường dẫn, định dạng ngày, sentinel, khoảng UTC và quy tắc dedup; nhưng câu “Follow Acme reporting conventions” không chứa quy ước ẩn chưa biết. Subagent trả “I will proceed ...” kèm code chứ không chứng minh đã chạy; main đọc answer.json thấy “not found”, rồi tự ghi số mà không execute/đối chiếu. Logs hai lần subagent nói “output has been written”; main đọc lại mỗi lần chỉ thấy `{}`, không phải file mất tích. Đây là bằng chứng F ở báo cáo subagent; main phát hiện nhưng chỉ giao lại cùng yêu cầu rồi chép JSON tay, không xác minh kết quả cuối. Luồng trong subagent không có trong trace nên không khẳng định nó đã chạy lệnh nào.

Token trung bình tập học giảm 69251 → 52361 (-24.39%) nhưng điểm trung bình giảm 0.3954 → 0.3120; logs riêng tăng 2.951 lần token, data giảm còn 0.320 lần nhưng mất 2 check. Thời gian code/data/logs là baseline 40.4/116.8/41.5 giây, subagents 23.7/56.9/54.8 giây. Không gọi đây là cải thiện chi phí có cùng chất lượng, hay hiệu quả của vai trò chuyên biệt.

## 6. Self-evolving

Curator chạy 3 lần (lần đầu và đúng 2 lần chạy lại được phép). Cả ba chỉ đọc baseline role=learn không có error; mỗi prompt gồm failed name/detail và 6000 ký tự cuối trace, không dùng pilot hoặc evaluation. Prompt/reply/usage thật lưu ở `report/curator_01.json` đến `curator_03.json`. Các skill đã ghi của hai lần đầu chuyển nguyên trạng sang `report/curator-rejected-01/` và `curator-rejected-02/`, không sửa nội dung.

- Lần 1: 3 skill hợp lệ nhưng tách annotations/regression làm hai, không có changelog hoặc logs; skill data dùng sentinel cụ thể và dedup row chung chung. Loại cả 3 để curator bao phủ workflow, giữ chính xác quy ước thay vì chi tiết input.
- Lần 2: giữ được 2 skill code; skill data bị validate_skill từ chối vì chuỗi `orders` trùng định danh eval. Không chủ động xem eval: đây là thông báo validator có sẵn, từ khớp một danh từ phổ thông trong feedback học. Lần này vẫn bỏ sót logs và có chỉ dẫn commit/static checker không bảo đảm tồn tại. Loại 2 file đã ghi; sửa prompt tổng quát để gom workflow và tránh tên miền dữ liệu riêng.
- Lần 3: sinh code/data/logs, nhưng data vẫn bị validator loại vì `orders`; giữ 2 skill hợp lệ code/logs. Không chạy lại lần thứ tư và không sửa tay để lách validation. Raw reply lưu cả khối bị từ chối để minh bạch; chỉ 2 file trong skills/auto được nạp. So bytes với block cuối có thêm newline: cả hai exact_model_output=True, validate_skill=[]; hash Linux `9be2711716937db8adb26385ceb3e43c011bfdc7d7e3d243186d420363f20dca`.

| Skill giữ lại | Tổng quát / tình huống description | Đúng và giới hạn | Độ dài |
| --- | --- | --- | --- |
| code-changes-with-testing-and-changelog | Use when modifying code; không nêu tên hàm hoặc input cụ thể | Đúng type hints, tests/test_regressions.py, CHANGELOG.md/Unreleased/format fix; không nhắc minimum 3 và “before committing” không hợp sandbox không có Git; mở rộng fix-format cho feature không được feedback chứng minh | 13 dòng tổng, 9 dòng body |
| structured-log-parsing-and-normalization | Use when parsing raw log files; quy trình xuyên dataset | Đúng UTC, nối multiline, chuẩn hóa service, sort và schema; bước repeat chưa nêu cộng 1, không nêu rõ counts_by_service/level upper-case, “expected values” không nên hiểu là có đáp án tham chiếu. Output errors.json là quy ước được phép | 20 dòng tổng, 16 dòng body |

Hai description có trigger rõ, ngắn hơn 40 dòng; hợp format không có nghĩa đầy đủ hoặc chắc chắn được đọc. Không có skill data hợp lệ là hạn chế thật, không bù bằng skill tự viết.

Development code/data/logs đạt 7/10, 5/8, 1/9 với 85790/37614/58192 token; skills_read=0 cả ba, skills_modified=false, error=null. Trace code bắt đầu ls workspace rồi đọc package chứ không đọc SKILL.md; data tạo và chạy process_sales.py với phân nhánh định dạng ngày, không có skill data; logs giao general-purpose rồi đọc output không đủ, tự ghi JSON. Trung bình điểm 0.4787, token 60532; quy ước 0/9, kỹ thuật 13/18. Giữ nguyên bộ skill và toàn bộ kết quả này ở skills-auto-dev trước freeze; không coi tăng điểm data là tác động của skill chưa đọc.

## 7. Kết quả so sánh

Chưa chạy chính thức sau freeze. Bảng sẽ sinh trực tiếp bằng lab.compare, cùng thống kê từ check_breakdown.

## 8. Phân tích

Chưa kết luận trước số liệu; sau đo sẽ phân tích learning/evaluation, kỹ thuật/quy ước, skill đọc/làm theo, token, quá khớp/rò rỉ và nhiễu trước/sau freeze.

## 9. Hạn chế

Chỉ ba tác vụ mỗi vai trò, một mô hình và một lần chạy chính thức mỗi cấu hình; kết quả không đại diện cho mọi loại công việc. Nhiệt độ 0 không bảo đảm tất định ở gateway/model. Trace chỉ chứa luồng chính; token cộng cả subagent nhưng tool_calls không gồm tool nội bộ của subagent. LocalShellBackend dùng env tối thiểu và container, nhưng không phải sandbox bảo mật chống chương trình độc hại.

## 10. Kết luận

Chưa kết luận hiệu quả trước khi thí nghiệm hoàn thành.

## Phụ lục

29 test offline đã pass; tour và pip check chạy thành công trong Linux. Dockerfile.day20 bổ sung Git cho verify_freeze; Dockerfile gốc và mọi file được cung cấp giữ nguyên. Prompt thực hiện nằm ở IMPLEMENTATION_PROMPT.md. Đây là bản đang làm, chưa nhận đã đủ checklist nộp.
