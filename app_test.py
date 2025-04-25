import os
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import openai
import numpy as np
from dotenv import load_dotenv
from vnstock import Listing, Quote, Company, Finance, Trading, Screener

# Load environment variables from .env file
load_dotenv()

# Tạo lớp encoder tùy chỉnh để xử lý các kiểu dữ liệu không được hỗ trợ trong JSON
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return super(CustomJSONEncoder, self).default(obj)

# Set page title and configuration
st.set_page_config(
    page_title="Stock VN Q&A Bot", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check for OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    
if not openai_api_key:
    openai_api_key = st.text_input("Enter your OpenAI API key:", type="password")
    if not openai_api_key:
        st.warning("Please enter your OpenAI API key to continue.")
        st.stop()

openai.api_key = openai_api_key

# Define function to handle function calling with OpenAI
def get_vnstock_function_call(query):
    """
    Use OpenAI's function calling to determine which vnstock function to use based on query.
    Returns the function name, parameters, and any extracted context.
    """
    functions = [
        {
            "type": "function",
            "function": {
                "name": "query_listing",
                "description": "Get information about stock listings, symbols, exchanges, and industries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": [
                                "all_symbols", "symbols_by_exchange", "symbols_by_group", 
                                "symbols_by_industries", "industries_icb"
                            ],
                            "description": "The specific function to call from Listing class"
                        },
                        "exchange": {
                            "type": "string",
                            "enum": ["HOSE", "HNX", "UPCOM"],
                            "description": "Stock exchange to query (if relevant)"
                        },
                        "group": {
                            "type": "string",
                            "enum": ["VN30", "VN100", "VNMID", "VNSML", "VNX50", "VNALL", "HNX30"],
                            "description": "Stock group to query (if relevant)" 
                        }
                    },
                    "required": ["function_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_quote",
                "description": "Get stock price information and historical data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["history", "intraday", "price_depth"],
                            "description": "The specific function to call from Quote class"
                        },
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol to query"
                        },
                        "resolution": {
                            "type": "string",
                            "enum": ["1", "5", "15", "30", "60", "D", "W", "M"],
                            "description": "Time resolution for historical data"
                        },
                        "from_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format"
                        },
                        "to_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["function_name", "symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_company",
                "description": "Get company information, profile, events, and news",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["profile", "officers", "shareholders", "subsidiaries", "overview", "events", "dividends", "news", "insider_deals"],
                            "description": "The specific function to call from Company class"
                        },
                        "symbol": {
                            "type": "string", 
                            "description": "Stock symbol to query"
                        }
                    },
                    "required": ["function_name", "symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_finance",
                "description": "Get financial information like income statements, balance sheets, and financial ratios",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["income_statement", "balance_sheet", "cash_flow", "ratio"],
                            "description": "The specific function to call from Finance class" 
                        },
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol to query"
                        },
                        "period": {
                            "type": "string",
                            "enum": ["quarter", "year"],
                            "description": "Financial report period"
                        }
                    },
                    "required": ["function_name", "symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_trading",
                "description": "Get stock trading information and price board data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["price_board"],
                            "description": "The specific function to call from Trading class"
                        },
                        "symbols": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of stock symbols to query"
                        }
                    },
                    "required": ["function_name", "symbols"]
                }
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "query_screener",
                "description": "Screen stocks based on various criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["stock"],
                            "description": "The specific function to call from Screener class"
                        }
                    },
                    "required": ["function_name"]
                }
            }
        }
    ]

    # Call OpenAI API with function calling
    response = openai.chat.completions.create(
        model="gpt-4o",  # Using latest model with function calling
        messages=[
            {"role": "system", "content": "You are a stock market analyst assistant that helps users get information about Vietnamese stocks using the vnstock library. Identify the appropriate function to call and parameters based on the user's query."},
            {"role": "user", "content": query}
        ],
        tools=functions,
        tool_choice="auto"
    )
    
    # Extract the function call
    message = response.choices[0].message
    if message.tool_calls:
        # Extract the function call
        function_call = message.tool_calls[0].function
        function_name = function_call.name
        arguments = json.loads(function_call.arguments)
        
        # Return the extracted information
        return {
            "function": function_name,
            "arguments": arguments,
            "explanation": message.content
        }
    else:
        # No function call was made
        return {
            "function": None,
            "arguments": None,
            "explanation": message.content
        }

# Define functions to call appropriate vnstock functions
def execute_vnstock_function(function_info):
    """Execute the appropriate vnstock function based on the function call info"""
    function_type = function_info.get("function")
    arguments = function_info.get("arguments", {})
    
    if not function_type or not arguments:
        return None, "Could not determine the appropriate function to call."
    
    try:
        if function_type == "query_listing":
            return execute_listing_function(arguments)
        elif function_type == "query_quote":
            return execute_quote_function(arguments)
        elif function_type == "query_company":
            return execute_company_function(arguments)
        elif function_type == "query_finance":
            return execute_finance_function(arguments)
        elif function_type == "query_trading":
            return execute_trading_function(arguments)
        elif function_type == "query_screener":
            return execute_screener_function(arguments)
        else:
            return None, f"Unknown function type: {function_type}"
    except Exception as e:
        return None, f"Error executing function: {str(e)}"

def execute_listing_function(arguments):
    """Execute functions from the Listing class"""
    function_name = arguments.get("function_name")
    listing = Listing()
    
    if not hasattr(listing, function_name):
        return None, f"Function {function_name} not found in Listing class."
    
    func = getattr(listing, function_name)
    
    # Extract additional parameters
    kwargs = {k: v for k, v in arguments.items() if k != "function_name" and v is not None}
    
    # Call the function with parameters
    try:
        result = func(**kwargs)
        return result, None
    except Exception as e:
        return None, f"Error calling {function_name}: {str(e)}"

def execute_quote_function(arguments):
    """Execute functions from the Quote class"""
    function_name = arguments.get("function_name")
    symbol = arguments.get("symbol")
    
    if not symbol:
        return None, "Symbol is required for Quote functions."
    
    # Chuẩn hóa mã chứng khoán (loại bỏ khoảng trắng, viết hoa)
    symbol = symbol.strip().upper()
    
    try:
        # Tạo đối tượng Quote cho mã chứng khoán
        quote = Quote(symbol)
    except Exception as e:
        return None, f"Không thể tạo đối tượng Quote cho mã '{symbol}': {str(e)}"
    
    if not hasattr(quote, function_name):
        return None, f"Function {function_name} not found in Quote class."
    
    func = getattr(quote, function_name)
    
    # Extract additional parameters
    kwargs = {k: v for k, v in arguments.items() if k not in ["function_name", "symbol"] and v is not None}
    
    # Nếu là hàm lấy lịch sử giá
    if function_name == "history":
        try:
            if "from_date" not in kwargs or "to_date" not in kwargs:
                end_date = datetime.today()
                # Thử với khoảng thời gian ngắn hơn (7 ngày thay vì 30)
                start_date = end_date - timedelta(days=7)
                kwargs["from_date"] = start_date.strftime("%Y-%m-%d")
                kwargs["to_date"] = end_date.strftime("%Y-%m-%d")
            
            if "resolution" not in kwargs:
                kwargs["resolution"] = "D"  # Mặc định là ngày
        except Exception as e:
            return None, f"Lỗi khi thiết lập tham số ngày tháng: {str(e)}"
    
    # Gọi hàm với tham số và xử lý lỗi tốt hơn
    try:
        result = func(**kwargs)
        # Kiểm tra kết quả trống
        if result is None or (isinstance(result, pd.DataFrame) and result.empty):
            return None, f"Không tìm thấy dữ liệu cho mã chứng khoán {symbol}. Vui lòng kiểm tra lại mã cổ phiếu."
        return result, None
    except Exception as e:
        error_msg = f"Error calling {function_name}: {str(e)}"
        print(f"Chi tiết lỗi: {error_msg}")  # Ghi log lỗi
        
        # Nếu lấy lịch sử thất bại, thử với tham số khác
        if function_name == "history":
            try:
                print("Đang thử lại với khoảng thời gian ngắn hơn...")
                end_date = datetime.today()
                start_date = end_date - timedelta(days=1)  # Chỉ thử 1 ngày
                kwargs["from_date"] = start_date.strftime("%Y-%m-%d")
                kwargs["to_date"] = end_date.strftime("%Y-%m-%d")
                result = func(**kwargs)
                if result is not None and not result.empty:
                    return result, None
                return None, "Không có dữ liệu giao dịch gần đây cho mã chứng khoán này."
            except Exception as retry_e:
                return None, f"Không thể lấy dữ liệu cho mã chứng khoán {symbol}. Vui lòng kiểm tra lại mã cổ phiếu."
        
        return None, error_msg

def execute_company_function(arguments):
    """Execute functions from the Company class"""
    function_name = arguments.get("function_name")
    symbol = arguments.get("symbol")
    
    if not symbol:
        return None, "Symbol is required for Company functions."
    
    company = Company(symbol)
    
    if not hasattr(company, function_name):
        return None, f"Function {function_name} not found in Company class."
    
    func = getattr(company, function_name)
    
    # Extract additional parameters
    kwargs = {k: v for k, v in arguments.items() if k not in ["function_name", "symbol"] and v is not None}
    
    # Call the function with parameters
    try:
        result = func(**kwargs)
        return result, None
    except Exception as e:
        return None, f"Error calling {function_name}: {str(e)}"

def execute_finance_function(arguments):
    """Execute functions from the Finance class"""
    function_name = arguments.get("function_name")
    symbol = arguments.get("symbol")
    period = arguments.get("period", "quarter")
    
    if not symbol:
        return None, "Symbol is required for Finance functions."
    
    finance = Finance(symbol=symbol, period=period)
    
    if not hasattr(finance, function_name):
        return None, f"Function {function_name} not found in Finance class."
    
    func = getattr(finance, function_name)
    
    # Extract additional parameters
    kwargs = {k: v for k, v in arguments.items() if k not in ["function_name", "symbol", "period"] and v is not None}
    
    # Call the function with parameters
    try:
        result = func(**kwargs)
        return result, None
    except Exception as e:
        return None, f"Error calling {function_name}: {str(e)}"

def execute_trading_function(arguments):
    """Execute functions from the Trading class"""
    function_name = arguments.get("function_name")
    symbols = arguments.get("symbols", [])
    
    if not symbols:
        return None, "Symbols list is required for Trading functions."
    
    trading = Trading()
    
    if not hasattr(trading, function_name):
        return None, f"Function {function_name} not found in Trading class."
    
    func = getattr(trading, function_name)
    
    # Extract additional parameters
    kwargs = {k: v for k, v in arguments.items() if k not in ["function_name", "symbols"] and v is not None}
    
    # Call the function with parameters
    try:
        result = func(symbols_list=symbols, **kwargs)
        return result, None
    except Exception as e:
        return None, f"Error calling {function_name}: {str(e)}"

def execute_screener_function(arguments):
    """Execute functions from the Screener class"""
    function_name = arguments.get("function_name")
    
    screener = Screener()
    
    if not hasattr(screener, function_name):
        return None, f"Function {function_name} not found in Screener class."
    
    func = getattr(screener, function_name)
    
    # Extract additional parameters
    kwargs = {k: v for k, v in arguments.items() if k != "function_name" and v is not None}
    
    # Call the function with parameters
    try:
        result = func(**kwargs)
        return result, None
    except Exception as e:
        return None, f"Error calling {function_name}: {str(e)}"

def process_data_for_display(data, function_name):
    """Process the data returned by vnstock for better display in Streamlit"""
    if data is None:
        return None
    
    # Convert to DataFrame if it's not already
    if not isinstance(data, pd.DataFrame):
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        else:
            try:
                data = pd.DataFrame(data)
            except:
                return data  # Return as is if we can't convert
    
    # Apply specific processing based on the function type
    if function_name == "query_quote" and data.shape[0] > 0:
        # For historical price data, we might want to create a chart
        if 'time' in data.columns and 'close' in data.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(data['time'], data['close'])
            ax.set_title(f"Stock Price History")
            ax.set_xlabel("Date")
            ax.set_ylabel("Price")
            ax.tick_params(axis='x', rotation=45)
            plt.tight_layout()
            return {"data": data, "chart": fig}
    
    # For company profile, we might want to format it nicely
    if function_name == "query_company":
        # Special formatting for company profile
        pass
    
    # For financial statements, we might want to highlight important metrics
    if function_name == "query_finance":
        # Special formatting for financial data
        pass
    
    return data

def generate_response(query, data, explanation):
    """
    Generate a comprehensive response based on the query and data.
    Uses OpenAI to create a natural language answer.
    """
    # Convert data to a string representation for the OpenAI API
    if isinstance(data, pd.DataFrame):
        data_str = data.to_string(index=True)
    elif isinstance(data, dict) and "data" in data and "chart" in data:
        # Handle the case with DataFrame and chart
        data_str = data["data"].to_string(index=True)
        # We don't include the chart in the string, as it's visual
    else:
        data_str = str(data)
    
    # Limit data string size if needed
    if len(data_str) > 8000:  # Truncate if too large
        data_str = data_str[:8000] + "... [truncated]"
    
    # Call OpenAI API to generate a natural language response
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a financial analyst expert specializing in Vietnamese stock market. Provide clear, accurate, and insightful analysis based on the data provided. Use Vietnamese language in your response since this is for Vietnamese users."},
            {"role": "user", "content": f"Query: {query}\n\nData: {data_str}\n\nBased on this data, provide a comprehensive analysis and answer to the query. Explain key insights, trends, and implications in a way that's easy to understand."}
        ]
    )
    
    return response.choices[0].message.content

# Hàm để xóa lịch sử - di chuyển định nghĩa lên đầu để có thể gọi sau này
def clear_history():
    """Xóa nội dung lịch sử trong file history.json và xóa lịch sử trò chuyện đang lưu trong session"""
    # 1. Xóa nội dung file history.json
    history_file = "history.json"
    if os.path.exists(history_file):
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
    else:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
    
    # 2. Xóa lịch sử trò chuyện trong session_state
    if 'messages' in st.session_state:
        st.session_state.messages = []
    
    # 3. Hiển thị thông báo thành công
    st.success("Đã xóa lịch sử hội thoại.")
    
    # 4. Đặt lại session_state.view_history thành False để đóng phần hiển thị lịch sử
    if 'view_history' in st.session_state:
        st.session_state.view_history = False

def close_history_callback():
    st.session_state.view_history = False
    # Đảm bảo nút không hiển thị sau khi đóng
    st.session_state.close_button_clicked = True

# Thêm hàm này trước khi định nghĩa save_conversation_history()

def sanitize_for_json(obj):
    """Chuyển đổi đối tượng để có thể được lưu thành JSON an toàn"""
    if isinstance(obj, dict):
        return {
            str(key) if not isinstance(key, (str, int, float, bool)) or key is None else key: 
            sanitize_for_json(value)
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return list(sanitize_for_json(item) for item in obj)
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj

# Hàm lưu dữ liệu hội thoại vào file history.json
def save_conversation_history():
    """Tự động lưu cuộc trò chuyện vào file history.json"""
    try:
        if not st.session_state.messages or len(st.session_state.messages) < 2:
            return None
        
        # Đường dẫn tuyệt đối tới file history.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_file = os.path.join(current_dir, "history.json")
        
        # Chuẩn bị dữ liệu theo định dạng yêu cầu
        formatted_history = []
        
        # Xử lý tin nhắn thành cặp (câu hỏi và câu trả lời)
        i = 0
        while i < len(st.session_state.messages):
            # Lấy câu hỏi (tin nhắn từ người dùng)
            if i < len(st.session_state.messages) and st.session_state.messages[i]["role"] == "user":
                question = {
                    "role": st.session_state.messages[i]["role"],
                    "content": st.session_state.messages[i]["content"]
                }
                
                # Lấy câu trả lời tương ứng (tin nhắn từ assistant)
                if i+1 < len(st.session_state.messages) and st.session_state.messages[i+1]["role"] == "assistant":
                    answer = {
                        "role": st.session_state.messages[i+1]["role"],
                        "content": st.session_state.messages[i+1]["content"]
                    }
                    
                    # Thêm dữ liệu nếu có
                    if "data" in st.session_state.messages[i+1]:
                        data_obj = st.session_state.messages[i+1]["data"]
                        
                        # Xử lý DataFrame
                        if isinstance(data_obj, pd.DataFrame):
                            # Tạo bản sao để tránh thay đổi DataFrame gốc
                            df_copy = data_obj.copy()
                            
                            # Chuyển đổi cột timestamp thành chuỗi
                            for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns:
                                df_copy[col] = df_copy[col].astype(str)
                            
                            # Đảm bảo thứ tự cột theo yêu cầu
                            desired_cols = ["price", "volume", "match_type", "id"]
                            available_cols = [col for col in desired_cols if col in df_copy.columns]
                            
                            # Lưu thông tin
                            answer["data_type"] = "dataframe"
                            answer["data"] = df_copy.to_dict(orient="records")
                            answer["columns"] = available_cols
                            answer["column_types"] = {col: str(df_copy[col].dtype) for col in df_copy.columns}
                            answer["index_name"] = df_copy.index.name
                        
                        # Xử lý data có chart
                        elif isinstance(data_obj, dict) and "data" in data_obj and "chart" in data_obj:
                            df_copy = data_obj["data"].copy()
                            
                            # Chuyển đổi cột timestamp thành chuỗi
                            for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64']).columns:
                                df_copy[col] = df_copy[col].astype(str)
                            
                            answer["data_type"] = "chart_with_data"
                            answer["data"] = df_copy.to_dict(orient="records")
                            answer["columns"] = list(df_copy.columns)
                            answer["column_types"] = {col: str(df_copy[col].dtype) for col in df_copy.columns}
                            answer["index_name"] = df_copy.index.name
                            
                            # Lưu dữ liệu để tạo lại biểu đồ
                            if "time" in df_copy.columns and "close" in df_copy.columns:
                                answer["chart_data"] = {
                                    "x_values": df_copy["time"].tolist(),
                                    "y_values": [float(x) for x in df_copy["close"].tolist()],
                                    "title": "Stock Price History"
                                }
                    
                    # Thêm cặp Q&A vào lịch sử
                    formatted_pair = {
                        "question": question,
                        "answer": answer
                    }
                    formatted_history.append(formatted_pair)
                    i += 2  # Chuyển đến cặp tiếp theo
                else:
                    # Nếu không có câu trả lời, chỉ thêm câu hỏi
                    formatted_pair = {
                        "question": question,
                        "answer": None
                    }
                    formatted_history.append(formatted_pair)
                    i += 1
            else:
                # Bỏ qua tin nhắn không phù hợp với mẫu
                i += 1
        
        # Kiểm tra xem file đã tồn tại chưa
        existing_data = []
        if os.path.exists(history_file) and os.path.getsize(history_file) > 0:
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                # Nếu file không phải là JSON hợp lệ, bắt đầu với mảng trống
                existing_data = []
        
        # Thêm cuộc trò chuyện mới vào dữ liệu hiện có
        combined_data = existing_data + formatted_history
        
        # Xử lý dữ liệu trước khi lưu để đảm bảo tất cả các khóa là hợp lệ cho JSON
        sanitized_data = sanitize_for_json(combined_data)
        
        # Lưu vào file sử dụng CustomJSONEncoder
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(sanitized_data, f, ensure_ascii=False, indent=2, cls=CustomJSONEncoder)
        
        return history_file
    
    except Exception as e:
        # Ghi log lỗi nhưng không hiển thị cho người dùng
        print(f"Lỗi khi lưu dữ liệu: {str(e)}")
        return None
    
def view_conversation_history():
    """Xem và quản lý lịch sử hội thoại từ file history.json"""
    history_file = "history.json"
    
    if not os.path.exists(history_file) or os.path.getsize(history_file) == 0:
        st.warning("Không tìm thấy lịch sử hội thoại.")
        return
    
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
        
        if not history_data:
            st.warning("File lịch sử trống.")
            return
        
        # Hiển thị số lượng cuộc hội thoại
        st.success(f"Đã tìm thấy {len(history_data)} cuộc hội thoại.")
        
        # Sử dụng tabs để hiển thị các cuộc trò chuyện
        tabs = st.tabs([f"Hội thoại {i+1}" for i in range(len(history_data))])
        
        # Hiển thị lịch sử trong tabs
        for i, (tab, conversation) in enumerate(zip(tabs, history_data)):
            with tab:
                st.subheader("Câu hỏi:")
                st.write(conversation.get("question", {}).get("content", "Không có nội dung"))
                st.subheader("Câu trả lời:")
                answer = conversation.get("answer", {})
                
                # Hiển thị nội dung câu trả lời
                answer_content = answer.get("content", "Không có câu trả lời")
                st.write(answer_content)
                
                # Hiển thị dữ liệu bổ sung nếu có
                if "data_type" in answer:
                    st.write("---")
                    st.subheader("Dữ liệu giao dịch:")
                    
                    # Xử lý dataframe
                    if answer["data_type"] == "dataframe" and "data" in answer:
                        # Tạo lại DataFrame với các cột đúng thứ tự
                        df = pd.DataFrame.from_records(answer["data"])
                        
                        # Tạo cấu hình cột động dựa trên các cột có sẵn
                        column_config = {}
                        
                        # Kiểm tra từng cột phổ biến và định dạng phù hợp
                        if "price" in df.columns:
                            column_config["price"] = st.column_config.NumberColumn("Giá", format="%d VND")
                        
                        if "volume" in df.columns:
                            column_config["volume"] = st.column_config.NumberColumn("Khối lượng", format="%d")
                        
                        if "match_type" in df.columns:
                            column_config["match_type"] = st.column_config.TextColumn("Loại giao dịch")
                        
                        if "id" in df.columns:
                            column_config["id"] = st.column_config.TextColumn("ID giao dịch")
                        
                        if "time" in df.columns:
                            column_config["time"] = st.column_config.DatetimeColumn("Thời gian", format="YYYY-MM-DD HH:mm:ss")
                        
                        # Xử lý các cột giá khác nhau
                        for price_col in ["close", "open", "high", "low", "last_price", "ref_price", "ceiling_price", "floor_price"]:
                            if price_col in df.columns:
                                column_config[price_col] = st.column_config.NumberColumn(
                                    f"Giá {price_col.replace('_price', '').replace('_', ' ').title()}", 
                                    format="%d VND"
                                )
                        
                        # Xử lý các cột khối lượng khác
                        for vol_col in ["volume", "matched_volume", "total_volume", "buy_volume", "sell_volume", "foreign_buy_volume", "foreign_sell_volume"]:
                            if vol_col in df.columns and vol_col != "volume":  # volume đã xử lý ở trên
                                column_config[vol_col] = st.column_config.NumberColumn(
                                    f"{vol_col.replace('_volume', '').replace('_', ' ').title()} Volume", 
                                    format="%d"
                                )
                        
                        # Thiết lập các cột theo thứ tự yêu cầu
                        if "columns" in answer and answer["columns"]:
                            # Lấy các cột có sẵn theo thứ tự mong muốn
                            available_cols = [col for col in answer["columns"] if col in df.columns]
                            if available_cols:
                                df = df[available_cols]
                        
                        # Hiển thị DataFrame với cấu hình cột động
                        st.dataframe(
                            df,
                            use_container_width=True,
                            column_config=column_config
                        )
                    
                    # Xử lý chart + data
                    elif answer["data_type"] == "chart_with_data" and "data" in answer:
                        if "chart_data" in answer:
                            # Tái tạo biểu đồ từ dữ liệu đã lưu
                            chart_data = answer["chart_data"]
                            fig, ax = plt.subplots(figsize=(10, 6))
                            ax.plot(chart_data["x_values"], chart_data["y_values"])
                            ax.set_title(chart_data.get("title", "Stock Price History"))
                            ax.set_xlabel("Date")
                            ax.set_ylabel("Price")
                            ax.tick_params(axis='x', rotation=45)
                            plt.tight_layout()
                            st.pyplot(fig)
                        
                        # Hiển thị DataFrame
                        df = pd.DataFrame.from_records(answer["data"])
                        if "columns" in answer:
                            available_cols = [col for col in answer["columns"] if col in df.columns]
                            if available_cols:
                                df = df[available_cols]
                        
                        # Tạo cấu hình cột động cho chart data
                        column_config = {}
                        if "time" in df.columns:
                            column_config["time"] = st.column_config.DatetimeColumn("Thời gian", format="YYYY-MM-DD HH:mm:ss")
                        if "close" in df.columns:
                            column_config["close"] = st.column_config.NumberColumn("Giá đóng cửa", format="%d")
                        if "open" in df.columns:
                            column_config["open"] = st.column_config.NumberColumn("Giá mở cửa", format="%d")
                        if "high" in df.columns:
                            column_config["high"] = st.column_config.NumberColumn("Giá cao nhất", format="%d")
                        if "low" in df.columns:
                            column_config["low"] = st.column_config.NumberColumn("Giá thấp nhất", format="%d")
                        if "volume" in df.columns:
                            column_config["volume"] = st.column_config.NumberColumn("Khối lượng", format="%d")
                            
                        with st.expander("Hiển thị bảng dữ liệu"):
                            st.dataframe(
                                df,
                                use_container_width=True,
                                column_config=column_config
                            )
        
    except json.JSONDecodeError:
        st.error("File lịch sử không hợp lệ. Vui lòng kiểm tra định dạng JSON.")
    except Exception as e:
        st.error(f"Lỗi khi đọc lịch sử: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

# Khởi tạo trạng thái xem lịch sử trong session_state nếu chưa có
if 'view_history' not in st.session_state:
    st.session_state.view_history = False

# Streamlit UI
# Thay thế phần tiêu đề dự án hiện tại
st.markdown("""
<div style="
    background: linear-gradient(120deg, #1a2980, #26d0ce); 
    padding: 8px 15px; 
    border-radius: 12px; 
    text-align: center; 
    margin-bottom: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    position: relative;
    overflow: hidden;
">
    <div style="
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(
            to right,
            rgba(255,255,255,0) 0%,
            rgba(255,255,255,0.3) 50%,
            rgba(255,255,255,0) 100%
        );
        transform: rotate(30deg);
        animation: shine 3s infinite;
    "></div>
    <h1 style="
        color: white; 
        font-size: 32px; 
        font-weight: bold; 
        margin: 5px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    ">
        🇻🇳 VIETNAM STOCK MARKET Q&A 📈
    </h1>
    <p style="
        color: rgba(255,255,255,0.9); 
        font-size: 16px; 
        margin: 0px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    ">
        Hỏi đáp thông tin về chứng khoán Việt Nam
    </p>
</div>
<style>
@keyframes shine {
    0% {transform: translateX(-100%) rotate(30deg);}
    100% {transform: translateX(100%) rotate(30deg);}
}
</style>
""", unsafe_allow_html=True)

# Initialize session state for chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "data" in message:
            # Display data if present (for user queries)
            if isinstance(message["data"], pd.DataFrame):
                st.dataframe(
                    message["data"],
                    use_container_width=True,
                    column_config={
                        "price": st.column_config.NumberColumn(
                            "Giá",
                            format="%d VND"
                        ),
                        "volume": st.column_config.NumberColumn(
                            "Khối lượng",
                            format="%d"
                        ),
                        "match_type": st.column_config.TextColumn(
                            "Loại giao dịch"
                        ),
                        "id": st.column_config.TextColumn(
                            "ID giao dịch"
                        ),
                        "time": st.column_config.DatetimeColumn(
                            "Thời gian",
                            format="YYYY-MM-DD HH:mm:ss"
                        )
                    }
                )
            elif isinstance(message["data"], dict) and "chart" in message["data"]:
                # Display both chart and data
                st.pyplot(message["data"]["chart"])
                with st.expander("Show Data"):
                    st.dataframe(message["data"]["data"])
        # Display the message content
        st.markdown(message["content"])

# Chat input
query = st.chat_input("Hỏi thông tin về chứng khoán...")

if query:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": query})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(query)
    
    # Display assistant "thinking" message
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown("⏳ Đang tìm kiếm thông tin...")
        
        # Process the query with OpenAI function calling
        function_info = get_vnstock_function_call(query)
        
        # Log the function info for debugging
        st.session_state.function_info = function_info
        
        # Execute the appropriate vnstock function
        if function_info.get("function"):
            thinking_placeholder.markdown("⏳ Đang truy xuất dữ liệu từ vnstock...")
            data, error = execute_vnstock_function(function_info)
            
            if error:
                thinking_placeholder.markdown(f"❌ Lỗi: {error}")
                response_content = f"Tôi xin lỗi, tôi gặp vấn đề khi truy xuất dữ liệu: {error}. Vui lòng thử lại với câu hỏi khác hoặc điều chỉnh yêu cầu của bạn."
            else:
                # Process the data for better display
                processed_data = process_data_for_display(data, function_info.get("function"))
                
                # Generate natural language response
                thinking_placeholder.markdown("⏳ Đang phân tích dữ liệu và tạo câu trả lời...")
                response_content = generate_response(query, processed_data, function_info.get("explanation"))
                
                # Display the data
                if processed_data is not None:
                    if isinstance(processed_data, pd.DataFrame):
                        st.dataframe(
                            processed_data,
                            use_container_width=True,
                            column_config={
                                "price": st.column_config.NumberColumn(
                                    "Giá",
                                    format="%d VND"
                                ),
                                "volume": st.column_config.NumberColumn(
                                    "Khối lượng", 
                                    format="%d"
                                ),
                                "match_type": st.column_config.TextColumn(
                                    "Loại giao dịch"
                                ),
                                "id": st.column_config.TextColumn(
                                    "ID giao dịch"
                                ),
                                "time": st.column_config.DatetimeColumn(
                                    "Thời gian",
                                    format="YYYY-MM-DD HH:mm:ss"
                                )
                            }
                        )
                    elif isinstance(processed_data, dict) and "chart" in processed_data:
                        st.pyplot(processed_data["chart"])
                        with st.expander("Show Data"):
                            st.dataframe(processed_data["data"])
        else:
            # Handle case where no function was called
            response_content = function_info.get("explanation", "Tôi không thể xác định chính xác thông tin bạn cần. Vui lòng cung cấp thêm chi tiết về mã chứng khoán hoặc loại thông tin bạn đang tìm kiếm.")
        
        # Clear the thinking message and display the final response
        thinking_placeholder.empty()
        st.markdown(response_content)
    
    # Add assistant response to chat history
    assistant_message = {
        "role": "assistant",
        "content": response_content
    }
    
    # Add the data to the message if available
    if function_info.get("function") and 'data' in locals() and data is not None:
        processed_data = locals().get('processed_data')
        if processed_data is not None:
            assistant_message["data"] = processed_data
    
    st.session_state.messages.append(assistant_message)
    
    # Tự động lưu lịch sử sau mỗi cuộc trò chuyện
    save_conversation_history()

# Add a sidebar with information about the app
with st.sidebar:
    st.header("Về ứng dụng")
    st.markdown("""
    **Hỏi đáp thông tin về Chứng khoán Việt Nam** là ứng dụng giúp bạn tìm kiếm và phân tích thông tin về thị trường chứng khoán Việt Nam.
    
    Bạn có thể hỏi về:
    - Thông tin công ty và mã chứng khoán
    - Giá cổ phiếu và dữ liệu giao dịch
    - Thông tin tài chính và báo cáo
    - Phân tích và so sánh cổ phiếu
    
    Dữ liệu được cung cấp bởi thư viện [vnstock](https://github.com/thinh-vu/vnstock).
    """)
    
    st.header("Ví dụ câu hỏi")
    st.markdown("""
    - "Cho tôi thông tin về công ty VNM"
    - "Giá cổ phiếu VIC trong 30 ngày qua"
    - "So sánh giá cổ phiếu VNM, VIC và VHM"
    - "Báo cáo tài chính của FPT quý gần nhất"
    - "Liệt kê các công ty trong ngành ngân hàng"
    - "Ai là cổ đông lớn nhất của VNM?"
    """)
    
    # Phần quản lý lịch sử - đã đơn giản hóa xuống còn 2 nút
    st.divider()
    st.header("Quản lý lịch sử")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Thay đổi nút thành toggle và điều chỉnh nhãn theo trạng thái
        if st.button("Xem lịch sử", key="view_history_btn"):
            # Khi nhấn nút, hiển thị lịch sử
            st.session_state.view_history = True
            # Cần rerun để hiển thị lịch sử ngay lập tức
            st.rerun()
    
    with col2:
        if st.button("Xóa lịch sử", key="clear_history_btn"):
            clear_history()

# Phần hiển thị lịch sử nếu được yêu cầu
if st.session_state.view_history:
    # Tạo phần tiêu đề đẹp và nổi bật hơn
    st.markdown("---")  # Thêm đường kẻ phía trên
    
    # Sử dụng container có nền màu để làm nổi bật tiêu đề
    title_container = st.container()
    with title_container:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.markdown(
                """
                <div style="
                    background: linear-gradient(135deg, #1e3c72, #2a5298); 
                    padding: 8px 12px; 
                    border-radius: 8px; 
                    text-align: center;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    border: 1px solid #4a6ea9;
                    margin-bottom: 10px;
                    margin-top: 5px;
                ">
                    <h2 style="
                        color: white; 
                        font-size: 26px; 
                        margin: 0; 
                        padding: 5px 0;
                        letter-spacing: 1px;
                        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
                        line-height: 1.4;
                    ">
                        📚 LỊCH SỬ HỘI THOẠI 💬
                    </h2>
                </div>
                """, 
                unsafe_allow_html=True
            )
    
    st.markdown("---")  # Thêm đường kẻ phía dưới
    view_conversation_history()
    
    # Sử dụng callback function để đóng lịch sử
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("Đóng lịch sử", 
                  key="close_history_btn", 
                  use_container_width=True,
                  on_click=close_history_callback)