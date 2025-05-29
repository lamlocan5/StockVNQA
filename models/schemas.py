def get_function_schemas():
    """Trả về schema cho các hàm có thể gọi từ OpenAI"""
    return [
        {
            "type": "function",
            "function": {
                "name": "query_listing",
                "description": "Lấy thông tin về danh sách cổ phiếu, mã, sàn giao dịch và ngành nghề",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": [
                                "all_symbols", "symbols_by_exchange", "symbols_by_group", 
                                "symbols_by_industries", "industries_icb"
                            ],
                            "description": "Hàm cụ thể cần gọi từ lớp Listing"
                        },
                        "exchange": {
                            "type": "string",
                            "enum": ["HOSE", "HNX", "UPCOM"],
                            "description": "Sàn giao dịch cần truy vấn (nếu có)"
                        },
                        "group": {
                            "type": "string",
                            "enum": ["VN30", "VN100", "VNMID", "VNSML", "VNX50", "VNALL", "HNX30"],
                            "description": "Nhóm cổ phiếu cần truy vấn (nếu có)" 
                        },
                        "industry": {
                            "type": "string",
                            "description": "Ngành nghề cần truy vấn (nếu có)"
                        },
                    },
                    "required": ["function_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_quote",
                "description": "Lấy thông tin giá cổ phiếu và dữ liệu lịch sử",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["history", "intraday", "price_depth"],
                            "description": "Hàm cụ thể cần gọi từ lớp Quote, với history là dữ liệu lịch sử, intraday là dữ liệu trong ngày và price_depth là khối lượng giao dịch theo bước giá"
                        },
                        "symbol": {
                            "type": "string",
                            "description": "mã cổ phiếu cần truy vấn, nếu là tên công ty (hoặc bất cứ thông tin gì liên quan) thì tự động truy vấn mã cổ phiếu tương ứng để điền"
                        },
                        "resolution": {
                            "type": "string",
                            "enum": ["1", "5", "15", "30", "60", "1D", "W", "M"],
                            "description": "Độ phân giải thời gian cho dữ liệu lịch sử"
                        },
                        "from_date": {
                            "type": "string",
                            "description": "Ngày bắt đầu định dạng YYYY-MM-DD, nếu không có sẽ lấy 30 ngày trước, tự động tính toán ngày nếu yêu cầu"
                        },
                        "to_date": {
                            "type": "string",
                            "description": "Ngày kết thúc định dạng YYYY-MM-DD, nếu không có sẽ lấy đến hiện tại"
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
                "description": "Lấy thông tin công ty, lãnh đạo, cổ đông và sự kiện",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["officers", "shareholders", "subsidiaries", "overview", "events", "news", "ratio_summary", "trading_stats"],
                            "description": "Hàm cụ thể cần gọi từ lớp Company"
                        },
                        "symbol": {
                            "type": "string", 
                            "description": "Mã công ty hoặc cổ phiếu cần truy vấn"
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
                "description": "Lấy thông tin tài chính như báo cáo thu nhập, bảng cân đối kế toán và tỷ lệ tài chính",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["income_statement", "balance_sheet", "cash_flow", "ratio"],
                            "description": "Hàm cụ thể cần gọi từ lớp Finance" 
                        },
                        "symbol": {
                            "type": "string",
                            "description": "mã cổ phiếu cần truy vấn, nếu điền tên công ty thì tự động truy vấn mã cổ phiếu tương ứng"
                        },
                        "period": {
                            "type": "string",
                            "enum": ["quarter", "year"],
                            "description": "Kỳ báo cáo tài chính, năm gần nhất, hoặc quý gần nhất"
                        }
                    },
                    "required": ["function_name", "symbol", "period"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_trading",
                "description": "Lấy thông tin giao dịch cổ phiếu và dữ liệu bảng giá (price board) của một nhiều cổ phiếu, dùng để so sánh giá cổ phiếu, hoặc để liệt kê",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["price_board"],
                            "description": "Hàm cụ thể cần gọi từ lớp Trading, với price_board là bảng giá của một hoặc nhiều cổ phiếu"
                        },
                        "symbols": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Danh sách mã cổ phiếu cần truy vấn, nếu điền tên công ty thì tự động truy vấn mã cổ phiếu tương ứng, nhớ cẩn thận với hàm price_board vì nó sẽ trả về bảng giá của nhiều cổ phiếu, nhớ trích xuất ĐÚNG và ĐỦ mã cổ phiếu để chạy"
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
                "description": "Lọc cổ phiếu dựa trên các tiêu chí khác nhau",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "enum": ["stock"],
                            "description": "Hàm cụ thể cần gọi từ lớp Screener"
                        }
                    },
                    "required": ["function_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "predict_stock_price",
                "description": "Dự đoán giá cổ phiếu trong tương lai dựa trên các mô hình học máy",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Mã cổ phiếu cần dự đoán"
                        },
                        "prediction_type":{
                            "type": "string",
                            "enum": ["price", "trend"],
                            "description": "Loại dự đoán, có thể là giá hoặc xu hướng"                      
                        }
                    },
                    "required": ["symbol", "prediction_type"]
                }
            }
        }
    ]
