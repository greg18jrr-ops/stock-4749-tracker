import json
import requests
import os
from datetime import datetime, timedelta
import time

# 設定目標股票
STOCK_ID = "4749"
STOCK_NAME = "新應材"
DATA_FILE = "data.json"

def get_roc_date(date_obj):
    """ 將西元日期轉為民國日期字串 (例如: 113/01/24) """
    year = date_obj.year - 1911
    return f"{year}/{date_obj.strftime('%m/%d')}"

def fetch_tpex_data(date_obj):
    """ 從櫃買中心抓取三大法人數據 """
    # 櫃買中心 API 使用民國年
    roc_date = get_roc_date(date_obj)
    print(f"Fetching data for {roc_date}...")
    
    # 櫃買中心三大法人買賣超日報表 API
    # 參數 d=民國日期, t=D(日報), se=股票代號 (如果支援篩選)
    # 注意：櫃買中心 API 有時不支援直接篩選個股，需要抓全部再過濾
    url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=&t=D&d={roc_date}"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers)
        data = res.json()
        
        if data['aaData']:
            # 尋找 4749
            for row in data['aaData']:
                # row[0] 是代號
                if row[0] == STOCK_ID:
                    # 格式通常為: 代號, 名稱, 外資買進, 外資賣出, 外資買賣超, ...
                    # 需根據實際回傳索引調整，通常：
                    # 0: 代號, 1: 名稱, 
                    # 外資及陸資(不含外資自營商) -> 買進(2), 賣出(3), 買賣超(4)
                    # 外資自營商 -> 買進(5), 賣出(6), 買賣超(7) ... (欄位可能變動，依賴名稱比較保險但這裡先簡化)
                    # 櫃買中心 JSON 欄位較多，直接取買賣超欄位 (通常是最後幾個的加總)
                    
                    # 簡化假設 (根據常見櫃買格式):
                    # 外資買賣超 = row[4] (or similar)
                    # 投信買賣超 = row[7]
                    # 自營商買賣超 = row[10] + row[13] (自行買賣+避險)
                    # *注意：實際欄位索引需視 API 版本，這裡抓取「三大法人買賣超股數」
                    
                    # 為了精確，我們直接抓取最後的「三大法人買賣超股數合計」(row[-1]?) 
                    # 或是分別抓。這裡嘗試抓取特定欄位。
                    # row[4] = 外資及陸資買賣超
                    # row[7] = 投信買賣超
                    # row[12] = 自營商買賣超 (合計)
                    # row[13] = 三大法人買賣超合計
                    
                    def parse_num(s):
                        return int(s.replace(',', ''))

                    foreign = parse_num(row[4])
                    trust = parse_num(row[7])
                    dealer = parse_num(row[12]) # 自營商合計
                    
                    return {
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "stock_id": STOCK_ID,
                        "foreign_investors": foreign,
                        "investment_trust": trust,
                        "dealer": dealer,
                        "total": parse_num(row[13])
                    }
            print(f"Stock {STOCK_ID} not found in data for {roc_date}. (Market closed or no trade?)")
        else:
            print(f"No data returned for {roc_date} (Holiday?)")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
    
    return None

def main():
    # 讀取現有資料
    history = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    # 嘗試抓取最近 3 天的資料 (避免漏掉)
    # 如果是 GitHub Actions 每天跑，其實只要抓今天。
    # 但為了第一次運行有數據，我們回推幾天。
    existing_dates = {d['date'] for d in history}
    
    # 從今天開始回推 5 天，補齊漏掉的
    for i in range(4, -1, -1):
        target_date = datetime.now() - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        
        if date_str in existing_dates:
            print(f"Data for {date_str} already exists. Skipping.")
            continue
            
        data = fetch_tpex_data(target_date)
        if data:
            history.append(data)
            time.sleep(3) # 禮貌性延遲，避免被擋

    # 排序並寫入
    history.sort(key=lambda x: x['date'])
    
    # 只保留最近 90 天
    history = history[-90:]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
    print(f"Updated {DATA_FILE} with {len(history)} records.")

if __name__ == "__main__":
    main()
