import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

from models.predictors import train_with_XGBoost, train_LSTM

def execute_prediction_function(arguments):
    """Thực hiện dự đoán giá cổ phiếu"""
    symbol = arguments.get("symbol")
    prediction_type = arguments.get("prediction_type", "price")
    
    print(f"hàm dự đoán được gọi với các tham số: {arguments}")
    if not symbol:
        return None, "Cần cung cấp mã cổ phiếu để dự đoán."
    
    try:
        
        rlt1 = []
        rlt2 = []
        rlt1 = train_with_XGBoost(ticker=symbol)
        rlt2 = train_LSTM(ticker=symbol)
        result1_df = pd.DataFrame([rlt1]) if not isinstance(rlt1, dict) else pd.DataFrame(rlt1, index=[0])
        result2_df = pd.DataFrame([rlt2]) if not isinstance(rlt2, dict) else pd.DataFrame(rlt2, index=[0])

        if prediction_type == "price":
            if(result1_df["r2"].iloc[0] >= result2_df["r2"].iloc[0]):
                print(f"XGBoost có độ chính xác cao hơn LSTM với r2 = {result1_df["r2"].iloc[0]} còn LSTM là {result2_df["r2"].iloc[0]}") 
                return {
                    "model": "XGBoost",
                    "r2": result1_df["r2"].iloc[0],
                    "rmse": result1_df["rmse"].iloc[0],
                    "mae": result1_df["mae"].iloc[0],
                    "predicted_price": result1_df["predicted_price"].iloc[0],
                }, None
            else:
                print(f"LSTM có độ chính xác cao hơn XGBoost với r2 = {result2_df["r2"].iloc[0]} còn XGBoost là {result1_df["r2"].iloc[0]}")
                return {
                    "model": "LSTM",
                    "r2": result2_df["r2"].iloc[0],
                    "rmse": result2_df["rmse"].iloc[0],
                    "mae": result2_df["mae"].iloc[0],
                    "predicted_price": result2_df["predicted_price"].iloc[0],
                }, None
        else:
            if(result1_df["direction_accuracy"].iloc[0] >= result2_df["direction_accuracy"].iloc[0]):
                print(f"XGBoost có độ chính xác cao hơn LSTM với độ chính xác = {result1_df["direction_accuracy"].iloc[0]} còn LSTM là {result2_df["direction_accuracy"].iloc[0]}")
                return {
                    "model": "XGBoost",
                    "r2": result1_df["r2"].iloc[0],
                    "rmse": result1_df["rmse"].iloc[0],
                    "mae": result1_df["mae"].iloc[0],
                    "direction_accuracy": result1_df["direction_accuracy"].iloc[0],
                    "predicted_trend": result1_df["trend"].iloc[0],
                }, None
            else:
                print(f"LSTM có độ chính xác cao hơn XGBoost với độ chính xác = {result2_df["direction_accuracy"].iloc[0]} còn XGBoost là {result1_df["direction_accuracy"].iloc[0]}")
                return {
                    "model": "LSTM",
                    "r2": result2_df["r2"].iloc[0],
                    "rmse": result2_df["rmse"].iloc[0],
                    "mae": result2_df["mae"].iloc[0],
                    "direction_accuracy": result2_df["direction_accuracy"].iloc[0],
                    "predicted_trend": result2_df["trend"].iloc[0],
                }, None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"Lỗi khi dự đoán giá cổ phiếu: {str(e)}"
