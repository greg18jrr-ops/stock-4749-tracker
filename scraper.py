import json
import random
from datetime import datetime, timedelta
import os

# 模擬資料結構 (之後會換成 requests 去爬證交所或 Goodinfo)
def fetch_stock_data(stock_id="4749"):
    # 這裡先產生假資料測試流程
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 讀取現有資料
    data_file = "data.json"
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    # 模擬今天的法人買賣超 (單位：張)
    new_record = {
        "date": today,
        "stock_id": stock_id,
        "foreign_investors": random.randint(-500, 500), # 外資
        "investment_trust": random.randint(-200, 200),  # 投信
        "dealer": random.randint(-100, 100)             # 自營商
    }
    
    # 避免重複加入同一天
    if not any(d['date'] == today for d in history):
        history.append(new_record)
        print(f"Added data for {today}")
    else:
        print(f"Data for {today} already exists")

    # 只保留最近 30 筆
    history = history[-30:]

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

if __name__ == "__main__":
    fetch_stock_data()
