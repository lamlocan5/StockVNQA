import streamlit as st
from dotenv import load_dotenv
import os
import json

# to run the app, use the command: python.exe -m streamlit run app.py

# Nhập các modules cần thiết
from config import APP_TITLE, APP_ICON, APP_LAYOUT
from api.openai_api import validate_api_key
from ui.components import display_user_message, display_assistant_response, render_sidebar, display_chat_history
from services.data_service import process_query
from services.chat_history_service import save_chat_history, load_chat_history

# Load biến môi trường
load_dotenv()
def set_theme(theme):
    config_path = ".streamlit/config.toml"
    if theme == "Sáng":
        config = """
[theme]
primaryColor="#1a2980"
backgroundColor="#ffffff"
secondaryBackgroundColor="#f0f2f6"
textColor="#262730"
font="sans serif"
"""
    else:
        config = """
[theme]
primaryColor="#26d0ce"
backgroundColor="#18191A"
secondaryBackgroundColor="#222"
textColor="#FAFAFA"
font="sans serif"
"""
    os.makedirs(".streamlit", exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config)
def main():
    # Thiết lập cấu hình trang
    st.set_page_config(
        page_title=APP_TITLE, 
        page_icon=APP_ICON, 
        layout=APP_LAYOUT,
        initial_sidebar_state="expanded"
    )
    

    # App Header
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
             VIETNAM STOCK MARKET Q&A 📈
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
    
    # Xác thực API key
    openai_api_key = validate_api_key()
    if not openai_api_key:
        return
    ls = load_chat_history()
    forget_messages = {
        "role": "system",
        "content": "Đã hết phiên trò chuyện, vui lòng nhập câu hỏi mới.VỚI THÔNG TIN LIÊN QUAN ĐẾN CỔ PHIẾU, CÔNG TY CHỈ SỬ DỤNG THÔNG TIN TRONG PHIÊN CỦA MÌNH (KHÔNG SỬ DỤNG CỦA PHIÊN TRƯỚC), CÒN CÁC YÊU CẦU CÁ NHÂN HÓA THÌ KHÔNG GIỚI HẠN TRONG PHIÊN, BẠN CẦN GHI NHỚ TẤT CẢ VÀ THỰC HIỆN CHO ĐÚNG"
    }
    ls.append(forget_messages)  # Thêm tin nhắn quên lịch sử vào lịch sử chat
    save_chat_history(ls)  # Lưu tin nhắn quên lịch sử vào file

    # Tải lịch sử trò chuyện từ file
    if 'messages' not in st.session_state:
        st.session_state.messages = load_chat_history()

    
    # Khởi tạo session state cho phiên hiện tại
    if 'current_message' not in st.session_state:
        st.session_state.current_message = None
    theme = st.sidebar.selectbox("Chọn giao diện", ["Sáng", "Tối"], key="theme_select")
    if "last_theme" not in st.session_state:
        st.session_state.last_theme = theme
    if theme != st.session_state.last_theme:
        set_theme(theme)
        st.session_state.last_theme = theme
        st.rerun()
    # Hiển thị sidebar
    render_sidebar()
    
    # KHÔNG hiển thị lịch sử chat, chỉ hiển thị tin nhắn hiện tại
    # if st.session_state.current_message:
    #     if st.session_state.current_message["role"] == "user":
    #         display_user_message(st.session_state.current_message["content"])
    #     else:
    #         with st.chat_message("assistant"):
    #             display_assistant_response(
    #                 st.session_state.current_message["content"],
    #                 st.session_state.current_message.get("data")
    #             )
    # Hiển thị lịch sử trò chuyện CHỈ TRONG PHIÊN HIỆN TẠI
    if 'messages' in st.session_state and st.session_state.messages:
        # Tìm index của tin nhắn "Đã hết phiên trò chuyện" cuối cùng
        last_session_end_idx = -1
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "system" and "Đã hết phiên trò chuyện" in msg["content"]:
                last_session_end_idx = i
        
        # Lấy chỉ các tin nhắn sau tin nhắn "Đã hết phiên trò chuyện" cuối cùng
        current_session_msgs = st.session_state.messages[last_session_end_idx+1:]
        
        # Lọc bỏ tin nhắn hệ thống
        current_session_msgs = [msg for msg in current_session_msgs 
                            if msg["role"] in ["user", "assistant"]]
        
        # Hiển thị tin nhắn trong phiên hiện tại
        display_chat_history(current_session_msgs)
    # Xử lý đầu vào từ người dùng
    query = st.chat_input("Hỏi thông tin về chứng khoán...")
    if query:
        # Hiển thị tin nhắn người dùng
        display_user_message(query)
        
        # Cập nhật tin nhắn hiện tại
        st.session_state.current_message = {"role": "user", "content": query}
        
        # Thêm vào lịch sử chat (không hiển thị)
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Xử lý truy vấn
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("⏳ Đang tìm kiếm thông tin...")
            
            # Xử lý truy vấn và lấy kết quả
            response_content, data = process_query(query, openai_api_key, thinking_placeholder)
            
            # Hiển thị phản hồi
            display_assistant_response(response_content, data)
        
        # Cập nhật tin nhắn hiện tại
        st.session_state.current_message = {
            "role": "assistant", 
            "content": response_content,
            "data": data
        }
        
        # Thêm vào lịch sử chat (không hiển thị)
        assistant_message = {
            "role": "assistant", 
            "content": response_content
        }

        st.session_state.messages.append(assistant_message)
        
        # Lưu lịch sử trò chuyện vào file
        save_chat_history(st.session_state.messages)
    
if __name__ == "__main__":
    main()

# to run the app, use the command: python.exe -m streamlit run app.py