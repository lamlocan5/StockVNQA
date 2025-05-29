import json
import os
from datetime import datetime

# Đường dẫn tới file lưu trữ lịch sử
HISTORY_FILE = "chat_history.json"

def save_chat_history(messages):
    """Lưu lịch sử trò chuyện vào file"""
    try:
        # Chuẩn bị dữ liệu để lưu
        data_to_save = {
            "last_updated": datetime.now().isoformat(),
            "messages": messages
        }
        
        # Đảm bảo chỉ lưu nội dung text, không lưu data
        serializable_messages = []
        for msg in messages:
            serializable_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        data_to_save["messages"] = serializable_messages
        
        # Lưu vào file
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Lỗi khi lưu lịch sử trò chuyện: {str(e)}")
        return False

def load_chat_history():
    """Tải lịch sử trò chuyện từ file"""
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data.get("messages", [])
    except Exception as e:
        print(f"Lỗi khi tải lịch sử trò chuyện: {str(e)}")
        return []

def get_chat_context(max_messages=100):
    """Lấy một số lượng tin nhắn gần đây nhất để sử dụng làm context"""
    messages = load_chat_history()
    
    # Chỉ trả về n tin nhắn gần nhất
    return messages[-max_messages:] if len(messages) > max_messages else messages