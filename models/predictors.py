import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score, mean_absolute_error
from datetime import datetime, timedelta
from vnstock import Vnstock
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.layers import Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping

def train_with_XGBoost(ticker, num_days=350, test_size=0.2, random_state=42):
    """
    Train mô hình XGBoost với số ngày dữ liệu được chỉ định
    
    Args:
        ticker (str): Mã cổ phiếu
        num_days (int): Số ngày dữ liệu muốn sử dụng
        test_size (float): Tỷ lệ dữ liệu test (0-1)
        random_state (int): Seed cho reproducibility
        
    Returns:
        dict: Kết quả train và đánh giá mô hình
    """
    try:
        # Import metrics để tính classification scores
        from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
        
        end_date = datetime.now()
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        from vnstock import Quote
        quote = Quote(symbol=ticker)
        df = quote.history(start = '2000-01-01', end= end_date_str, interval='1D')

        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        df[col] = df[col].str.replace(',', '').astype(float)
                    except Exception as e:
                        return None
        
        df['volatility'] = df['high'] - df['low']
        df['return_1d'] = df['close'].pct_change()
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        
        df['volume_ratio'] = np.where(
            df['volume_ma5'] > 0, 
            df['volume'] / df['volume_ma5'], 
            np.nan
        )

        df['target'] = df['close'].shift(-1)
        
        df = df.replace([np.inf, -np.inf], np.nan)
        df.dropna(inplace=True)

        # total_days = len(df)
        # if total_days < num_days:
        #     num_days = total_days
        
        # df = df.tail(num_days).reset_index(drop=True)
        
        features = ['open', 'high', 'low', 'close', 'volume', 'volatility', 
                   'return_1d', 'ma5', 'ma10', 'volume_ratio']
        
        X = df[features]
        y = df['target']
        
        test_rows = int(len(df) * test_size)
        train_rows = len(df) - test_rows
        
        X_train, X_test = X.iloc[:train_rows], X.iloc[train_rows:]
        y_train, y_test = y.iloc[:train_rows], y.iloc[train_rows:]
        
        # Thêm random_state vào XGBRegressor
        model = xgb.XGBRegressor(
            n_estimators=300, 
            max_depth=2, 
            learning_rate=0.05,
            colsample_bytree=0.8, #giảm overfit
            gamma=0.1, #ngưỡng điều chỉnh độ phức tạp của mô hình
            min_child_weight=3, 
            subsample=0.8,
            random_state=random_state  # Thêm dòng này
        )
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        
        # Regression metrics
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Classification metrics cho direction prediction
        y_direction_true = (y_test.values > X_test['close'].values).astype(int)
        y_direction_pred = (y_pred > X_test['close'].values).astype(int)
        
        # Dự đoán ngày mai
        latest = df.iloc[-1:].copy()
        X_future = latest[features]
        predicted_price_tomorrow = model.predict(X_future)[0]
        current_price = df['close'].iloc[-1]
        change_pct = (predicted_price_tomorrow - current_price) / current_price * 100
        
        if change_pct > 0:
            trend = "🔼 TĂNG"
        else:
            trend = "🔽 GIẢM"

        return {
            'ticker': ticker,
            'data_days': len(df),
            'train_days': len(X_train),
            'test_days': len(X_test),
            'random_state': random_state,  # Track random_state used
            
            # Regression metrics
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            
            
            'current_price': current_price,
            'predicted_price': predicted_price_tomorrow,
            'change_pct': change_pct,
            'trend': 'UP' if change_pct > 0 else 'DOWN'
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None
    
def train_LSTM(ticker, random_state=42):
    """
    Train mô hình LSTM
    
    Args:
        ticker (str): Mã cổ phiếu
        random_state (int): Seed cho reproducibility
    Returns:
        dict: Kết quả train và đánh giá mô hình
    """
    try:
        # Set random seeds cho reproducibility
        import random
        import os
        
        # Set seeds cho tất cả các library
        np.random.seed(random_state)
        random.seed(random_state)
        os.environ['PYTHONHASHSEED'] = str(random_state)
        
        # Set TensorFlow seeds
        try:
            import tensorflow as tf
            tf.random.set_seed(random_state)
            # Để deterministic operations (có thể chậm hơn)
            tf.config.experimental.enable_op_determinism()
        except:
            pass
            
        end_date = datetime.now()
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        from vnstock import Quote
        quote = Quote(symbol=ticker)
        df = quote.history(start = '2000-01-01', end= end_date_str, interval='1D')

        if 'open' not in df.columns:
            # Không có cột 'open', vẫn sử dụng features hiện tại
            features = ['close', 'volume', 'high', 'low']
        else:
            # Có cột 'open', thêm vào features
            features = ['close', 'open', 'volume', 'high', 'low']
        
        # --- PHẦN 1: TÍNH TOÁN CÁC FEATURES MỚI ---
        # Tạo bản sao để không làm ảnh hưởng đến dữ liệu gốc
        df_features = df.copy()
        
        # KIỂM TRA VÀ XỬ LÝ GIÁ TRỊ KHÔNG HỢP LỆ TRONG DỮ LIỆU GỐC
        # Thay thế các giá trị âm hoặc 0 trong volume bằng giá trị nhỏ
        if (df_features['volume'] <= 0).any():
            min_positive_volume = df_features.loc[df_features['volume'] > 0, 'volume'].min()
            df_features.loc[df_features['volume'] <= 0, 'volume'] = min_positive_volume * 0.01
            
        # Đảm bảo giá không có giá trị âm
        for price_col in ['close', 'high', 'low']:
            if (df_features[price_col] <= 0).any():
                print(f"⚠️ {ticker} có giá {price_col} không hợp lệ (âm hoặc bằng 0)")
                return None
        
        # Tính toán các đặc trưng tương đối một cách an toàn
        df_features['daily_return'] = df_features['close'].pct_change().replace([np.inf, -np.inf], np.nan)
        df_features['high_low_range'] = ((df_features['high'] - df_features['low']) / df_features['close']).replace([np.inf, -np.inf], np.nan)
        
        # Nếu có cột open thì tính thêm đặc trưng close_to_open
        if 'open' in df.columns:
            df_features['close_to_open'] = ((df_features['close'] - df_features['open']) / df_features['open']).replace([np.inf, -np.inf], np.nan)
        
        # Tính toán các chỉ báo trung bình động
        df_features['ma5'] = df_features['close'].rolling(window=5).mean()
        df_features['ma20'] = df_features['close'].rolling(window=20).mean()
        
        # Xử lý trường hợp chia cho 0 hoặc NaN
        ma5 = df_features['ma5']
        ma20 = df_features['ma20']
        mask = (ma20 != 0) & ma20.notnull() & ma5.notnull()
        df_features['ma_ratio'] = np.nan
        df_features.loc[mask, 'ma_ratio'] = ma5.loc[mask] / ma20.loc[mask]
        
        # Tính toán độ biến động (volatility) an toàn
        df_features['volatility_5d'] = df_features['daily_return'].rolling(window=5).std().replace([np.inf, -np.inf], np.nan)
        
        # Phân tích khối lượng
        df_features['volume_ma5'] = df_features['volume'].rolling(window=5).mean()
        
        # Xử lý trường hợp chia cho 0 hoặc NaN
        vol = df_features['volume']
        vol_ma5 = df_features['volume_ma5']
        mask = (vol_ma5 != 0) & vol_ma5.notnull() & vol.notnull()
        df_features['volume_ratio'] = np.nan
        df_features.loc[mask, 'volume_ratio'] = vol.loc[mask] / vol_ma5.loc[mask]
        
        # Xử lý giá trị thiếu từ việc tính toán các chỉ báo - sửa warning
        df_features = df_features.ffill()  # Thay vì fillna(method='ffill')
        df_features = df_features.fillna(0)  # Điền 0 cho các giá trị NaN còn lại ở đầu
        
        # --- PHẦN 2: CHUẨN BỊ DỮ LIỆU ĐẦU VÀO ---
        # Danh sách các đặc trưng sẽ sử dụng, bao gồm cả đặc trưng gốc và đặc trưng mới
        extended_features = features.copy()  # Giữ các đặc trưng gốc
        
        # Thêm các đặc trưng mới đã tính toán
        additional_features = [
            'daily_return', 'high_low_range', 'ma_ratio', 
            'volatility_5d', 'volume_ratio'
        ]
        
        # Thêm close_to_open nếu có dữ liệu open
        if 'open' in df.columns:
            additional_features.append('close_to_open')
            
        # Kết hợp tất cả đặc trưng và kiểm tra giá trị không hợp lệ
        for feat in additional_features:
            if feat in df_features.columns:  # Chỉ thêm feature nếu tồn tại
                # Kiểm tra giá trị không hợp lệ
                if df_features[feat].isnull().any() or np.isinf(df_features[feat]).any():
                    print(f"⚠️ {ticker} có giá trị NaN hoặc Inf trong feature {feat}. Thay thế bằng 0.")
                    df_features[feat] = df_features[feat].replace([np.inf, -np.inf], 0).fillna(0)
                extended_features.append(feat)
        
        # KIỂM TRA LẦN CUỐI TRƯỚC KHI CHUẨN HÓA
        # Thay thế bất kỳ giá trị không hợp lệ còn lại
        df_check = df_features[extended_features]
        if df_check.isnull().any().any() or np.isinf(df_check).any().any():
            print(f"⚠️ {ticker} vẫn có giá trị không hợp lệ. Làm sạch dữ liệu...")
            df_check = df_check.replace([np.inf, -np.inf], 0)
            df_check = df_check.fillna(0)
            df_features[extended_features] = df_check
        
        # Chuẩn hóa tất cả đặc trưng - có thể set random_state nếu có shuffle
        scaler = MinMaxScaler()
        try:
            scaled_data = scaler.fit_transform(df_features[extended_features])
        except Exception as scale_error:
            print(f"❌ {ticker} - Lỗi khi chuẩn hóa dữ liệu: {str(scale_error)}")
            # Hiển thị thêm thông tin để debug
            print(f"Kiểm tra giá trị không hợp lệ: {df_features[extended_features].describe()}")
            return None

        # --- PHẦN 3: TẠO CHUỖI DỮ LIỆU CHO LSTM ---
        def create_dataset(data, window_size=30):
            X, y = [], []
            for i in range(len(data) - window_size):
                X.append(data[i:i+window_size])
                y.append(data[i+window_size, 0])  # Vẫn dự đoán close (cột đầu tiên)
            return np.array(X), np.array(y)

        window_size = 30
        X, y = create_dataset(scaled_data, window_size)

        # --- PHẦN 4: CHIA DỮ LIỆU TRAIN/TEST ---
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # --- PHẦN 5: XÂY DỰNG VÀ HUẤN LUYỆN MÔ HÌNH ---
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense
        
        # Set seed cho Keras layer initialization
        tf.keras.utils.set_random_seed(random_state)
        
        model = Sequential()
        model.add(LSTM(64, input_shape=(window_size, X.shape[2])))
        model.add(Dense(1))
        
        # Compile với deterministic optimizer
        optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
        model.compile(optimizer=optimizer, loss='mean_squared_error')
        
        # Train với shuffle=False để đảm bảo reproducibility
        model.fit(X_train, y_train, epochs=50, batch_size=16, verbose=0, shuffle=False)

        # --- PHẦN 6: DỰ ĐOÁN VÀ ĐÁNH GIÁ ---
        y_pred = model.predict(X_test)
        
        # Import metrics để tính classification scores
        from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
        
        # Chuyển đổi giá trị về thang đo gốc
        # Tạo mảng với giá trị dự đoán ở vị trí đầu tiên và 0 ở các vị trí còn lại
        y_pred_full = np.zeros((len(y_pred), len(extended_features)))
        y_pred_full[:, 0] = y_pred.flatten()  # Đặt giá trị dự đoán vào cột đầu tiên (close)
        
        # Tương tự với giá trị thực tế
        y_test_full = np.zeros((len(y_test), len(extended_features)))
        y_test_full[:, 0] = y_test  # Đặt giá trị thực tế vào cột đầu tiên (close)
        
        # Inverse transform để lấy giá trị gốc
        y_pred_inv = scaler.inverse_transform(y_pred_full)[:, 0]
        y_test_inv = scaler.inverse_transform(y_test_full)[:, 0]

        # Tính các regression metrics
        rmse = np.sqrt(mean_squared_error(y_test_inv, y_pred_inv))
        mae = mean_absolute_error(y_test_inv, y_pred_inv)
        r2 = r2_score(y_test_inv, y_pred_inv)
        
        # Tính Direction Accuracy và classification metrics
        start_idx = window_size + split
        actual_current_prices = df['close'].values[start_idx:start_idx+len(y_test_inv)-1]
        
        # Đảm bảo các mảng có cùng kích thước
        min_len = min(len(y_test_inv)-1, len(actual_current_prices))
        
        # Tính hướng giá thực tế và dự đoán, chỉ dùng phần chồng lấp
        actual_direction = (y_test_inv[1:min_len+1] > actual_current_prices[:min_len]).astype(int)
        predicted_direction = (y_pred_inv[1:min_len+1] > actual_current_prices[:min_len]).astype(int)
        
        
        # --- PHẦN 7: DỰ ĐOÁN GIÁ CHO NGÀY TIẾP THEO ---
        last_seq = scaled_data[-window_size:]
        last_seq = last_seq.reshape((1, window_size, len(extended_features)))
        next_day_scaled = model.predict(last_seq)
        
        # Tạo mảng đầy đủ để inverse transform
        next_day_full = np.zeros((1, len(extended_features)))
        next_day_full[0, 0] = next_day_scaled[0, 0]  # Đặt giá trị dự đoán vào cột đầu tiên
        
        next_day_price = scaler.inverse_transform(next_day_full)[0][0]
        
        # Tính % thay đổi
        current_price = df['close'].iloc[-1]
        change_pct = ((next_day_price - current_price) / current_price) * 100
        
        return {
            'ticker': ticker,
            'data_days': len(df),
            'train_days': len(y_train),
            'test_days': len(y_test),
            'random_state': random_state,  # Track random_state used
            
            # Regression metrics
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            
            
            'current_price': current_price,
            'predicted_price': next_day_price,
            'change_pct': change_pct,
            'trend': 'UP' if change_pct > 0 else 'DOWN'
        }
        
    except Exception as e:
        print(f"❌ Lỗi xử lý {ticker} với LSTM: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


