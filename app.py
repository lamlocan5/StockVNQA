import streamlit as st
from dotenv import load_dotenv
import os
import json

# to run the app, use the command: python.exe -m streamlit run app.py

# Nhập các modules cần thiết
from config import APP_TITLE, APP_ICON, APP_LAYOUT
from api.openai_api import validate_api_key
from ui.components import display_user_message, display_assistant_response, render_sidebar
from services.data_service import process_query
from services.chat_history_service import save_chat_history, load_chat_history

# Load biến môi trường
load_dotenv()

def main():
    # Thiết lập cấu hình trang
    st.set_page_config(
        page_title=APP_TITLE, 
        page_icon=APP_ICON, 
        layout=APP_LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    # Hiển thị tiêu đề
    st.title("🇻🇳 Vietnam Stock Market Q&A Bot")
    st.markdown("Hỏi đáp thông tin về chứng khoán Việt Nam")
    
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
    
    # Hiển thị sidebar
    render_sidebar()
    
    # KHÔNG hiển thị lịch sử chat, chỉ hiển thị tin nhắn hiện tại
    if st.session_state.current_message:
        if st.session_state.current_message["role"] == "user":
            display_user_message(st.session_state.current_message["content"])
        else:
            with st.chat_message("assistant"):
                display_assistant_response(
                    st.session_state.current_message["content"],
                    st.session_state.current_message.get("data")
                )
    
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