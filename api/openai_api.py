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

def get_function_call(query):
    """Sử dụng OpenAI để xác định hàm cần gọi dựa trên truy vấn"""
    try:
        # Lấy các schemas của hàm
        functions = get_function_schemas()
        
        # Gọi OpenAI API với function calling
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý phân tích thị trường chứng khoán giúp người dùng lấy thông tin về chứng khoán Việt Nam sử dụng thư viện vnstock. Xác định hàm phù hợp và các tham số dựa trên yêu cầu của người dùng. Nhớ xác định ĐÚNG và ĐỦ các tham số cần thiết để hàm hoạt động."},
                {"role": "user", "content": query}
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

def generate_response(query, data):
    """Tạo câu trả lời dựa trên truy vấn và dữ liệu"""
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
        
        # Chuẩn bị prompt dựa trên template
        user_prompt = USER_PROMPT_TEMPLATE.format(query=query, data=data_str)
        
        # Gọi OpenAI API để tạo phản hồi
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Xin lỗi, tôi gặp lỗi khi tạo phản hồi: {str(e)}"
