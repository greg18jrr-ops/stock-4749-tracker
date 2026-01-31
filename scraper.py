import json
import requests
import os
from datetime import datetime, timedelta
import time

# 設定目標股票
STOCK_ID = "4749"
DATA_FILE = "data.json"

def get_roc_date(date_obj):
    """ 將西元日期轉為民國日期字串 (例如: 115/01/30) """
    year = date_obj.year - 1911
    return f"{year}/{date_obj.strftime('%m/%d')}"

def fetch_tpex_data(date_obj):
    """ 從櫃買中心抓取三大法人數據 """
    roc_date = get_roc_date(date_obj)
    print(f"Fetching data for {roc_date}...")
    
    url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=&t=D&d={roc_date}"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers)
        raw_data = res.json()
        
        # 解析新版 JSON 結構
        # 結構: {'tables': [{'data': [[row1], [row2]...], 'fields': [...]}]}
        rows = []
        if 'tables' in raw_data and len(raw_data['tables']) > 0:
            rows = raw_data['tables'][0].get('data', [])
        elif 'aaData' in raw_data: # 舊版相容
            rows = raw_data['aaData']
            
        if rows:
            for row in rows:
                # row[0] 是代號
                if row[0] == STOCK_ID:
                    # 根據 2026/01/30 的 header 結構:
                    # 0:代號, 1:名稱
                    # 外資及陸資(不含外資自營商): 2:買進, 3:賣出, 4:買賣超
                    # 外資自營商: 5:買進, 6:賣出, 7:買賣超
                    # 外資及陸資合計: 8:買進, 9:賣出, 10:買賣超 <--- 通常看這個當外資
                    # 投信: 11:買進, 12:賣出, 13:買賣超
                    # 自營商(自行買賣): 14:買進, 15:賣出, 16:買賣超
                    # 自營商(避險): 17:買進, 18:賣出, 19:買賣超
                    # 自營商合計: 20:買進, 21:賣出, 22:買賣超
                    # 三大法人合計: 23
                    
                    # 為了保險，我們讀取對應欄位 (假設順序固定，因為 JSON 沒有 key)
                    # 這裡取主要欄位
                    
                    def parse_num(s):
                        return int(s.replace(',', ''))

                    # 欄位索引可能會有微調，這裡取比較安全的推測值
                    # 根據觀察:
                    # 外資(Total) -> index 10 (or around)
                    # 投信 -> index 13
                    # 自營商(Total) -> index 22
                    
                    # 若欄位數不夠，可能結構不同，做個保護
                    if len(row) < 20:
                        continue

                    # 嘗試抓取
                    foreign = parse_num(row[10]) # 外資合計
                    trust = parse_num(row[13])   # 投信
                    dealer = parse_num(row[22])  # 自營商合計
                    
                    return {
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "stock_id": STOCK_ID,
                        "foreign_investors": foreign,
                        "investment_trust": trust,
                        "dealer": dealer
                    }
            print(f"Stock {STOCK_ID} not found in data for {roc_date}.")
        else:
            print(f"No data returned for {roc_date} (Holiday?)")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
    
    return None

def main():
    history = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    existing_dates = {d['date'] for d in history}
    
    # 回推 5 天補齊資料
    # 注意：如果原本是空陣列，會抓最近 5 天
    has_update = False
    for i in range(4, -1, -1):
        target_date = datetime.now() - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        
        # 簡單排除週末 (雖然 API 也會回傳無資料，但先跳過省請求)
        if target_date.weekday() >= 5: # 5=Sat, 6=Sun
            continue

        if date_str in existing_dates:
            print(f"Data for {date_str} already exists. Skipping.")
            continue
            
        data = fetch_tpex_data(target_date)
        if data:
            history.append(data)
            has_update = True
            time.sleep(1)

    if has_update:
        history.sort(key=lambda x: x['date'])
        history = history[-90:] # 保留 90 天
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        print(f"Updated {DATA_FILE} with new records.")
    else:
        print("No new data found.")

if __name__ == "__main__":
    main()
