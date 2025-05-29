import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json

from api.openai_api import get_function_call, generate_response
from api.vnstock_api import (
    get_listing_data, get_quote_data, get_company_data, 
    get_finance_data, get_trading_data, get_screener_data
)
from services.prediction_service import execute_prediction_function


def process_query(query, openai_api_key, thinking_placeholder):
    """Xử lý truy vấn của người dùng và trả về kết quả"""
    from services.chat_history_service import get_chat_context
    
    # Lấy lịch sử trò chuyện để sử dụng làm context
    chat_context = get_chat_context(max_messages=100)  
    
    # Xác định hàm cần gọi dựa trên truy vấn
    thinking_placeholder.markdown("⏳ Đang xác định loại dữ liệu cần truy vấn...")
    function_info = get_function_call(query, chat_context = chat_context)
    
    # Thực thi hàm phù hợp
    if function_info.get("function"):
        thinking_placeholder.markdown("⏳ Đang truy xuất dữ liệu từ vnstock...")
        data, error = execute_vnstock_function(function_info)
        
        if error:
            thinking_placeholder.markdown(f"❌ Lỗi: {error}")
            response_content = f"Tôi xin lỗi, tôi gặp vấn đề khi truy xuất dữ liệu: {error}. Vui lòng thử lại với câu hỏi khác hoặc điều chỉnh yêu cầu của bạn."
            return response_content, None
        else:
            # Xử lý dữ liệu để hiển thị tốt hơn
            processed_data = process_data_for_display(data, function_info.get("function"))
            
            # Tạo câu trả lời tự nhiên sử dụng lịch sử chat làm context
            thinking_placeholder.markdown("⏳ Đang phân tích dữ liệu và tạo câu trả lời...")
            response_content = generate_response(query, processed_data, chat_context)
            
            return response_content, processed_data
    else:
        # Xử lý trường hợp không có hàm nào được gọi
        response_content = function_info.get("explanation", "Tôi không thể xác định chính xác thông tin bạn cần. Vui lòng cung cấp thêm chi tiết về mã chứng khoán hoặc loại thông tin bạn đang tìm kiếm.")
        return response_content, None

def execute_vnstock_function(function_info):
    """Thực thi hàm vnstock phù hợp dựa trên thông tin hàm"""
    function_type = function_info.get("function")
    arguments = function_info.get("arguments", {})
    
    if not function_type or not arguments:
        return None, "Không thể xác định hàm phù hợp để gọi."
    
    try:
        if function_type == "query_listing":
            function_name = arguments.pop("function_name", None)
            return get_listing_data(function_name, **arguments)
        
        elif function_type == "query_quote":
            function_name = arguments.pop("function_name", None)
            symbol = arguments.pop("symbol", None)
            return get_quote_data(symbol, function_name, **arguments)
        
        elif function_type == "query_company":
            function_name = arguments.pop("function_name", None)
            symbol = arguments.pop("symbol", None)
            return get_company_data(symbol, function_name, **arguments)
        
        elif function_type == "query_finance":
            function_name = arguments.pop("function_name", None)
            symbol = arguments.pop("symbol", None)
            period = arguments.pop("period", "quarter")
            return get_finance_data(symbol, function_name, period, **arguments)
        
        elif function_type == "query_trading":
            function_name = arguments.pop("function_name", None)
            symbols = arguments.pop("symbols", [])
            return get_trading_data(function_name, symbols, **arguments)
        
        elif function_type == "query_screener":
            function_name = arguments.pop("function_name", None)
            return get_screener_data(function_name, **arguments)
        
        elif function_type == "predict_stock_price":
            return execute_prediction_function(arguments)
        
        else:
            return None, f"Loại hàm không xác định: {function_type}"
    except Exception as e:
        return None, f"Lỗi khi thực thi hàm: {str(e)}"

def process_data_for_display(data, function_name):
    """Xử lý dữ liệu trả về từ vnstock để hiển thị tốt hơn trong Streamlit"""
    if data is None:
        return None
    
    # Trả về nguyên dạng nếu đã là dự đoán (đã được xử lý)
    if isinstance(data, dict) and "prediction_data" in data:
        return data
    
    # Chuyển thành DataFrame nếu chưa phải
    if not isinstance(data, pd.DataFrame):
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        else:
            try:
                data = pd.DataFrame(data)
            except:
                return data  # Trả về nguyên dạng nếu không thể chuyển đổi
    
    # Áp dụng xử lý cụ thể dựa trên loại hàm
    if function_name == "query_quote" and data.shape[0] > 0:
        # Với dữ liệu giá lịch sử, có thể tạo biểu đồ
        if 'time' in data.columns and 'close' in data.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(data['time'], data['close'])
            ax.set_title(f"Lịch Sử Giá Cổ Phiếu")
            ax.set_xlabel("Ngày")
            ax.set_ylabel("Giá")
            ax.tick_params(axis='x', rotation=45)
            plt.tight_layout()
            return {"data": data, "chart": fig}
    
    return data


