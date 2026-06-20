#!/usr/bin/env python3
"""
從 Google Drive 自動下載最新 Excel 檔
- EPBOX 週報資料夾 → data-archive/
- EPBOX 回收價資料夾 → price-data/
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
except ImportError:
    sys.exit("❌ 請先執行：pip3 install --user google-api-python-client google-auth")

BASE_DIR = Path(__file__).parent.parent
SERVICE_ACCOUNT_FILE = BASE_DIR / "service-account.json"
DATA_ARCHIVE_DIR = BASE_DIR / "data-archive"
PRICE_DATA_DIR = BASE_DIR / "price-data"

WEEKLY_FOLDER_ID = "12b9spbQGVzav-QaptsxBMwFI1z-1JSDr"
PRICE_FOLDER_ID  = "1AVmxtv88WLUMRsWyRz-z5f_3CT1K_VAA"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_xlsx_files(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed=false",
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc"
    ).execute()
    return results.get("files", [])


def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    dest_path.write_bytes(buf.getvalue())


def sync_weekly_reports(service):
    print("📥 同步週報資料...")
    DATA_ARCHIVE_DIR.mkdir(exist_ok=True)
    files = list_xlsx_files(service, WEEKLY_FOLDER_ID)
    if not files:
        print("   ⚠️  週報資料夾沒有 Excel 檔")
        return 0

    count = 0
    for f in files:
        dest = DATA_ARCHIVE_DIR / f["name"]
        if dest.exists():
            print(f"   ✓ 已存在，跳過：{f['name']}")
            continue
        print(f"   ↓ 下載：{f['name']}")
        download_file(service, f["id"], dest)
        count += 1
    print(f"   → 新下載 {count} 個檔案")
    return count


def sync_price_file(service):
    print("📥 同步回收價資料...")
    PRICE_DATA_DIR.mkdir(exist_ok=True)
    files = list_xlsx_files(service, PRICE_FOLDER_ID)
    if not files:
        print("   ⚠️  回收價資料夾沒有 Excel 檔")
        return None

    latest = files[0]  # 已依 modifiedTime desc 排序
    dest = PRICE_DATA_DIR / latest["name"]
    print(f"   ↓ 最新回收價：{latest['name']}")
    download_file(service, latest["id"], dest)
    print(f"   ✓ 已下載到 {dest}")
    return dest


def main():
    if not SERVICE_ACCOUNT_FILE.exists():
        sys.exit(f"❌ 找不到金鑰檔：{SERVICE_ACCOUNT_FILE}")

    print("🔑 連線 Google Drive...")
    service = get_drive_service()

    sync_weekly_reports(service)
    price_file = sync_price_file(service)

    print("\n✅ 同步完成")
    if price_file:
        print(f"   最新回收價檔案：{price_file.name}")


if __name__ == "__main__":
    main()
