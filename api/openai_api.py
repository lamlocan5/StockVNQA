import os
import json
import streamlit as st
import openai
import pandas as pd

from config import OPENAI_MODEL, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from models.schemas import get_function_schemas

def validate_api_key():
    """Xác thực OpenAI API key"""
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        
    if not openai_api_key:
        openai_api_key = st.text_input("Nhập OpenAI API key của bạn:", type="password")
        if not openai_api_key:
            st.warning("Vui lòng nhập OpenAI API key để tiếp tục.")
            return None
    
    openai.api_key = openai_api_key
    return openai_api_key

def get_function_call(query, chat_context=None):
    """Sử dụng OpenAI để xác định hàm cần gọi dựa trên truy vấn"""
    try:
        # Lấy các schemas của hàm
        functions = get_function_schemas()
        
        # previous_query = next(msg["content"] for msg in chat_context if msg["role"] == "user") if chat_context else "Không có câu hỏi trước đó"
        # print(f"Previous query: {previous_query}")

        # Gọi OpenAI API với function calling
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý phân tích thị trường chứng khoán giúp người dùng lấy thông tin về chứng khoán Việt Nam sử dụng thư viện vnstock. Xác định hàm phù hợp và các tham số dựa trên yêu cầu của người dùng. Nhớ xác định ĐÚNG và ĐỦ các tham số cần thiết để hàm hoạt động."},
                {"role": "user", "content": query + f"\n\n Sử dụng lịch sử trò chuyện để hiểu rõ hơn về ngữ cảnh và sở thích của tôi, CÓ THỂ sử dụng thông tin từ các câu hỏi trước để hỗ trợ trả lời cho câu hỏi này (ĐỪNG DÙNG NẾU KHÔNG CẦN THIẾT, ƯU TIÊN CÁC CÂU HỎI GẦN NHẤT, VỚI THÔNG TIN LIÊN QUAN ĐẾN CỔ PHIẾU, CÔNG TY CHỈ SỬ DỤNG THÔNG TIN TRONG PHIÊN CỦA MÌNH, CÒN CÁC YÊU CẦU CÁ NHÂN HÓA THÌ KHÔNG GIỚI HẠN TRONG PHIÊN, BẠN CẦN GHI NHỚ TẤT CẢ VÀ THỰC HIỆN CHO ĐÚNG). Câu hỏi trước đó: {chat_context}."}
            ],
            tools=functions,
            tool_choice="auto"
        )
        
        # Trích xuất function call
        message = response.choices[0].message
        if message.tool_calls:
            # Trích xuất thông tin hàm được gọi
            function_call = message.tool_calls[0].function
            function_name = function_call.name
            arguments = json.loads(function_call.arguments)
            
            # Trả về thông tin hàm
            return {
                "function": function_name,
                "arguments": arguments,
                "explanation": message.content
            }
        else:
            # Không có function call nào được thực hiện
            return {
                "function": None,
                "arguments": None,
                "explanation": message.content
            }
    except Exception as e:
        return {
            "function": None,
            "arguments": None,
            "explanation": f"Lỗi khi xử lý yêu cầu: {str(e)}"
        }

def generate_response(query, data, chat_context=None):
    """Tạo câu trả lời dựa trên truy vấn, dữ liệu và lịch sử trò chuyện"""
    try:
        # Chuyển đổi dữ liệu thành chuỗi
        if isinstance(data, pd.DataFrame):
            data_str = data.to_string(index=True)
        elif isinstance(data, dict) and "data" in data and "chart" in data:
            data_str = data["data"].to_string(index=True)
        elif isinstance(data, dict) and "prediction_data" in data:
            data_str = f"Historical data:\n{data['historical_data'].tail(10).to_string()}\n\nPrediction data:\n{data['prediction_data'].to_string()}"
            if "metrics" in data:
                data_str += f"\n\nModel evaluation metrics:\nRMSE: {data['metrics']['rmse']}\nMAE: {data['metrics']['mae']}"
        else:
            data_str = str(data)

        # Giới hạn kích thước dữ liệu nếu cần
        if len(data_str) > 8000:
            data_str = data_str[:8000] + "... [dữ liệu bị cắt ngắn]"
        
        # Chuẩn bị prompt dựa trên templatey
        user_prompt = USER_PROMPT_TEMPLATE.format(query=query, data=data_str)
        
        # Chuẩn bị messages với lịch sử trò chuyện
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Thêm lịch sử trò chuyện vào context nếu có
        if chat_context:
            messages.extend(chat_context)
        
        # Thêm prompt hiện tại
        messages.append({"role": "user", "content": user_prompt})
        
        # Gọi OpenAI API để tạo phản hồi
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Xin lỗi, tôi gặp lỗi khi tạo phản hồi: {str(e)}"
