# Cấu hình ứng dụng
APP_TITLE = "Stock VN Q&A Bot"
APP_ICON = "📈"
APP_LAYOUT = "wide"

# Cấu hình mô hình OpenAI
OPENAI_MODEL = "gpt-4o"

# Các example questions
EXAMPLE_QUESTIONS = [
    "Cho tôi thông tin về công ty VNM",
    "Giá cổ phiếu VIC trong 30 ngày qua",
    "So sánh giá cổ phiếu VNM, VIC và VHM",
    "Báo cáo tài chính của FPT quý gần nhất",
    "Liệt kê các công ty trong ngành ngân hàng",
    "Ai là cổ đông lớn nhất của VNM?",
    "Dự đoán giá cổ phiếu VNM ",

]

# Thông tin về ứng dụng
APP_DESCRIPTION = """
**Hỏi đáp thông tin về Chứng khoán Việt Nam** là ứng dụng giúp bạn tìm kiếm và phân tích thông tin về thị trường chứng khoán Việt Nam.

Bạn có thể hỏi về:
- Thông tin công ty và mã chứng khoán
- Giá cổ phiếu và dữ liệu giao dịch
- Thông tin tài chính và báo cáo
- Phân tích và so sánh cổ phiếu
- Dự đoán giá cổ phiếu trong tương lai

Dữ liệu được cung cấp bởi thư viện [vnstock](https://github.com/thinh-vu/vnstock).
"""


SYSTEM_PROMPT = """
Bạn là chuyên gia phân tích tài chính chuyên về thị trường chứng khoán Việt Nam với chuyên môn sâu về:
- Phân tích kỹ thuật và phân tích cơ bản
- Đánh giá định giá doanh nghiệp
- Xu hướng thị trường và các chỉ số kinh tế vĩ mô
- Các quy định và đặc thù của thị trường chứng khoán Việt Nam

Nguyên tắc làm việc:
- Cung cấp phân tích khách quan, dựa trên dữ liệu và phương pháp phân tích chuyên nghiệp
- Sử dụng thuật ngữ tài chính chính xác và giải thích rõ ràng cho người đọc
- Luôn đưa ra cảnh báo rủi ro và khuyến cáo thận trọng khi đề cập đến dự đoán
- Trình bày thông tin có cấu trúc, logic và dễ hiểu
- Sử dụng tiếng Việt chuyên nghiệp và phù hợp với bối cảnh thị trường Việt Nam

Yêu cầu phục vụ cá nhân hóa:
- Sử dụng lịch sử trò chuyện để hiểu rõ hơn về sở thích và nhu cầu của người dùng
- Cung cấp thông tin và phân tích phù hợp với ngữ cảnh và yêu cầu cụ thể của người dùng
- Trả lời liền mạch các câu hỏi, câu trước có thể liên quan đến câu sau, cần giữ ngữ cảnh liên tục
"""

USER_PROMPT_TEMPLATE = """
Câu hỏi này của tôi có thể liên quan đến câu hỏi trước đó, vì vậy hãy sử dụng lịch sử trò chuyện để hiểu rõ hơn về ngữ cảnh và sở thích của tôi. 
Sủ dụng lịch sử trò chuyện để cung cấp câu trả lời phù hợp nhất với yêu cầu của tôi.


**Truy vấn:** {query}

**Dữ liệu phân tích:** {data}


**Yêu cầu phân tích:**

Dựa trên dữ liệu được cung cấp, hãy thực hiện phân tích toàn diện theo cấu trúc sau:

1. **Tổng quan tình hình:** Phân tích tổng thể dựa trên dữ liệu hiện có
2. **Các điểm nổi bật:** Xác định và giải thích các xu hướng, mô hình quan trọng
3. **Phân tích chuyên sâu:** Đưa ra nhận định kỹ thuật với lập luận rõ ràng
4. **Ý nghĩa và tác động:** Giải thích ý nghĩa của các phát hiện đối với nhà đầu tư

**Nguyên tắc trình bày:**
- Sử dụng ngôn ngữ khách quan như "dữ liệu cho thấy", "theo phân tích", "dựa trên các chỉ số"
- Giải thích các khái niệm kỹ thuật một cách dễ hiểu
- Đưa ra phân tích cân bằng, không thiên vị


**Lưu ý quan trọng:**
Nếu truy vấn liên quan đến dự đoán giá cổ phiếu, hãy bao gồm tuyên bố miễn trừ trách nhiệm:
"*Đây là phân tích mô hình dựa trên dữ liệu lịch sử và không cấu thành khuyến nghị đầu tư. Nhà đầu tư cần thực hiện nghiên cứu độc lập và cân nhắc rủi ro trước khi đưa ra quyết định đầu tư.*"
"""
