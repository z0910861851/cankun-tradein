#!/usr/bin/env python3
"""
從回收價 Excel 讀取最新一期的價格，自動上傳到 Firebase
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    sys.exit("❌ 請先執行：pip3 install --user pandas openpyxl")

try:
    import requests
except ImportError:
    sys.exit("❌ 請先執行：pip3 install --user requests")

BASE_DIR = Path(__file__).parent.parent
PRICE_DATA_DIR = BASE_DIR / "price-data"

FIREBASE_URL = "https://trade-in-5135c-default-rtdb.asia-southeast1.firebasedatabase.app"
FIREBASE_API_KEY = "AIzaSyCuK7MkMN_ZIUxv0cOA7zq_OMcR-2kaJBY"
# 各通路欄位對應（Excel欄位名 → Firebase key）
VENDOR_COL_MAP = {
    "台哥大":         "台哥大",
    "遠傳":           "遠傳",
    "台北101":        "台北101",
    "STUDIO A":       "STUDIO",
    "STUDIO":         "STUDIO",
    "APPLE BAR":      "APPLE BAR",
    "地標":           "地標",
    "米可":           "米可",
    "神腦\n門市回收價": "神腦",
    "神腦":           "神腦",
    "trade in價":     "trade in價",
    "trade in":       "trade in價",
    "調整後\n門市回收價": "trade in價",
}


def firebase_patch(path, data):
    url = f"{FIREBASE_URL}/{path}.json?key={FIREBASE_API_KEY}"
    return requests.patch(url, json=data)


def firebase_put(path, data):
    url = f"{FIREBASE_URL}/{path}.json?key={FIREBASE_API_KEY}"
    return requests.put(url, json=data)


def find_latest_price_file():
    files = sorted(PRICE_DATA_DIR.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        sys.exit("❌ price-data 目錄沒有 Excel 檔")
    return files[0]


def find_current_sheet(xl):
    """用最後一個 sheet（最新期價格）"""
    return xl.sheet_names[-1]


def safe_path(model):
    return re.sub(r"[/.#$\[\]]", "_", model.strip().upper())


def main():
    price_file = find_latest_price_file()
    print(f"📂 讀取回收價：{price_file.name}")

    xl = pd.ExcelFile(price_file)
    sheet = find_current_sheet(xl)
    print(f"📋 使用 Sheet：{sheet}")

    df = pd.read_excel(price_file, sheet_name=sheet, dtype=str)

    model_col = "機型"
    if model_col not in df.columns:
        sys.exit(f"❌ 找不到「機型」欄位，現有欄位：{list(df.columns)}")

    # 找出 Excel 裡有哪些通路欄位
    active_cols = {col: key for col, key in VENDOR_COL_MAP.items() if col in df.columns}
    print(f"💰 找到通路欄位：{list(active_cols.values())}")

    rows = df.dropna(subset=[model_col])
    rows = rows[rows[model_col].str.strip() != ""]

    print(f"📤 整理 {len(rows)} 筆價格...")
    all_prices = {}
    for _, row in rows.iterrows():
        model = row[model_col].strip().upper()
        path = safe_path(model)
        entry = {"model": model}
        for col, key in active_cols.items():
            try:
                val = int(float(str(row[col]).strip()))
                if val > 0:
                    entry[key] = val
            except (ValueError, KeyError):
                pass
        if len(entry) > 1:  # 至少有一個通路價格
            all_prices[path] = entry

    print(f"🔄 清空舊資料並寫入 {len(all_prices)} 筆...")
    resp = firebase_put("tradein_prices/prices", all_prices)
    if resp.status_code == 200:
        print(f"✅ 上傳完成：{len(all_prices)} 筆成功")
    else:
        print(f"❌ 上傳失敗：{resp.status_code} {resp.text[:120]}")

    # 更新 lastUpdated
    firebase_put("tradein_prices/meta/lastUpdated", datetime.now().isoformat())



if __name__ == "__main__":
    main()
