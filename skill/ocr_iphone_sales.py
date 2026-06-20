#!/usr/bin/env python3
"""
從 Google Drive「各店 iPhone 銷量」資料夾讀取最新截圖，
用 Cloud Vision OCR 辨識數字，更新 analyze_and_report.py 的 DEFAULT_IPHONE_SALES
"""

import re
import sys
import io
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    sys.exit("❌ 請先執行：pip3 install --user google-api-python-client google-auth")

BASE_DIR = Path(__file__).parent.parent
SERVICE_ACCOUNT_FILE = BASE_DIR / "service-account.json"
ANALYZE_SCRIPT = Path(__file__).parent / "analyze_and_report.py"

SALES_FOLDER_ID = "16k856z1UrvPLF46QoiUVAvehpPrLw2NZ"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# 截圖店名 → Python 腳本中的 key
STORE_NAME_MAP = {
    "大甲":     "燦坤大甲店",
    "中華":     "燦坤中華店",
    "五甲":     "燦坤五甲店",
    "內湖旗艦": "燦坤內湖店",
    "公益":     "燦坤公益店",
    "斗六":     "燦坤斗六店",
    "北投新旗艦": "燦坤北投新旗艦店",
    "右昌":     "燦坤右昌店",
    "永華二":   "燦坤永華二店",
    "光復":     "燦坤光復店",
    "林口文化": "燦坤林口文化店",
    "信義":     "燦坤信義店",
    "桃園旗艦": "燦坤桃園旗艦店",
    "基隆旗艦": "燦坤基隆旗艦店",
    "華榮":     "TK3C@009華榮",
    "新文心":   "燦坤新文心店",
    "新光華":   "燦坤新光華店",
    "新岡山":   "燦坤岡山家電館",
    "新莊":     "燦坤新莊店",
    "新豐原旗艦": "燦坤新豐原旗艦店",
}


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_latest_image(service):
    results = service.files().list(
        q=f"'{SALES_FOLDER_ID}' in parents and trashed=false and (mimeType contains 'image/')",
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=1
    ).execute()
    files = results.get("files", [])
    if not files:
        sys.exit("❌ 銷量資料夾沒有圖片檔")
    return files[0]


def download_image(service, file_id):
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def ocr_image(image_bytes):
    """用 macOS 內建 Swift Vision framework 做 OCR（免費、無需 API key）"""
    import tempfile, subprocess, os
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(image_bytes)
        tmp_path = f.name
    try:
        swift_code = f'''
import Vision
import AppKit
let url = URL(fileURLWithPath: "{tmp_path}")
let handler = VNImageRequestHandler(url: url)
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
try? handler.perform([request])
if let results = request.results {{
    for obs in results {{
        if let c = obs.topCandidates(1).first {{ print(c.string) }}
    }}
}}
'''
        result = subprocess.run(["swift", "-"], input=swift_code, capture_output=True, text=True)
        return result.stdout
    finally:
        os.unlink(tmp_path)


def parse_sales(text):
    """
    從 OCR 文字解析銷量數字。
    因為截圖字型特殊導致中文辨識可能失準，改用「數字順序」比對：
    截圖中的數字順序與 STORE_NAME_MAP 的順序一致。
    """
    store_keys = list(STORE_NAME_MAP.values())
    # 抓出所有獨立的數字行（排除總計那行，通常是最大值）
    nums = []
    for line in text.splitlines():
        line = line.strip()
        if re.fullmatch(r"\d+", line):
            nums.append(int(line))

    # 移除總計（最後一個最大值）
    if nums and nums[-1] == sum(nums[:-1]):
        nums = nums[:-1]
    elif len(nums) > len(store_keys):
        nums = nums[:len(store_keys)]

    if len(nums) != len(store_keys):
        return {}

    return {store_keys[i]: nums[i] for i in range(len(store_keys))}


def update_analyze_script(sales):
    code = ANALYZE_SCRIPT.read_text(encoding="utf-8")
    # 產生新的 dict 內容
    lines = ["DEFAULT_IPHONE_SALES = {\n"]
    for short, full in STORE_NAME_MAP.items():
        val = sales.get(full, 0)
        lines.append(f'    "{full}":{" " * (18 - len(full))}{val},\n')
    lines.append("}\n")
    new_block = "".join(lines)

    # 取代原本的 DEFAULT_IPHONE_SALES
    new_code = re.sub(
        r"DEFAULT_IPHONE_SALES\s*=\s*\{[^}]+\}",
        new_block.rstrip("\n"),
        code,
        flags=re.DOTALL
    )
    ANALYZE_SCRIPT.write_text(new_code, encoding="utf-8")


def main():
    print("🔑 連線 Google Drive...")
    service = get_drive_service()

    print("📥 取得最新銷量截圖...")
    file_info = get_latest_image(service)
    print(f"   檔案：{file_info['name']}")
    image_bytes = download_image(service, file_info["id"])

    print("🔍 OCR 辨識中...")
    text = ocr_image(image_bytes)

    print("📊 解析數字...")
    sales = parse_sales(text)

    if not sales:
        print("❌ 無法辨識任何門市銷量，請確認截圖格式")
        print("OCR 原文：")
        print(text[:500])
        sys.exit(1)

    print(f"✅ 辨識到 {len(sales)} 間門市：")
    total = 0
    for full, val in sales.items():
        short = [k for k, v in STORE_NAME_MAP.items() if v == full][0]
        print(f"   {short:8s} → {val}")
        total += val
    print(f"   總計：{total}")

    print("\n📝 更新 analyze_and_report.py...")
    update_analyze_script(sales)
    print("✅ 完成")


if __name__ == "__main__":
    main()
