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
PRICE_COL = "調整後\n門市回收價"


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
    """找到今天日期對應的 sheet（格式 MMDD-MMDD）"""
    today = datetime.now()
    today_str = today.strftime("%m%d")  # e.g. "0620"
    for name in xl.sheet_names:
        parts = re.split(r"[-~]", name.strip())
        if len(parts) == 2:
            start, end = parts[0].strip(), parts[1].strip()
            if start <= today_str <= end:
                return name
    # 找不到就用最後一個 sheet
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

    # 找機型欄和價格欄
    model_col = "機型"
    if model_col not in df.columns:
        sys.exit(f"❌ 找不到「機型」欄位，現有欄位：{list(df.columns)}")
    if PRICE_COL not in df.columns:
        sys.exit(f"❌ 找不到「{PRICE_COL}」欄位")

    rows = df[[model_col, PRICE_COL]].dropna(subset=[model_col])
    rows = rows[rows[model_col].str.strip() != ""]

    print(f"📤 上傳 {len(rows)} 筆價格...")
    success = 0
    errors = 0
    for _, row in rows.iterrows():
        model = row[model_col].strip().upper()
        price_raw = str(row[PRICE_COL]).strip()
        try:
            price = int(float(price_raw))
        except ValueError:
            continue

        path = safe_path(model)
        payload = {"model": model, "EPBOX": price}
        resp = firebase_patch(f"tradein_prices/prices/{path}", payload)
        if resp.status_code == 200:
            success += 1
        else:
            print(f"   ✗ {model}：{resp.status_code} {resp.text[:80]}")
            errors += 1

    # 更新 lastUpdated
    firebase_put("tradein_prices/meta/lastUpdated", datetime.now().isoformat())

    print(f"\n✅ 上傳完成：{success} 筆成功，{errors} 筆失敗")


if __name__ == "__main__":
    main()
