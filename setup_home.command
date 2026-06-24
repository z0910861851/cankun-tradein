#!/bin/bash
# 家裡電腦初始設定腳本

cd "$(dirname "$0")"
REPO_DIR="$(pwd)"

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║     燦坤 Trade-in — 家裡電腦初始設定       ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Step 1: 安裝 Python 套件
echo "📦 Step 1：安裝 Python 套件..."
pip3 install --user google-api-python-client google-auth pandas openpyxl requests
echo "✅ 套件安裝完成"
echo ""

# Step 2: 確認 service-account.json
echo "🔑 Step 2：確認服務帳號金鑰..."
if [ ! -f "$REPO_DIR/service-account.json" ]; then
  echo "❌ 找不到 service-account.json"
  echo "   請把 service-account.json 複製到這個資料夾後再執行一次"
  read -p "按 Enter 結束..."; exit 1
fi
echo "✅ service-account.json 存在"
echo ""

# Step 3: 建立 logs 資料夾
echo "📁 Step 3：建立 logs 資料夾..."
mkdir -p "$REPO_DIR/logs"
echo "✅ logs 資料夾建立完成"
echo ""

# Step 4: 設定 launchd 排程（每週二早上 9:00）
echo "⏰ Step 4：設定每週二自動執行..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.cankun.tradein.update.plist"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cankun.tradein.update</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${REPO_DIR}/update.command</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>2</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${REPO_DIR}/logs/update.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO_DIR}/logs/update.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"
echo "✅ 排程設定完成（每週二 09:00 自動執行）"
echo ""

echo "╔════════════════════════════════════════════╗"
echo "║            ✅ 設定完成！                    ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "📌 注意事項："
echo "   • 每週二早上 9:00 會自動更新"
echo "   • 執行記錄：${REPO_DIR}/logs/update.log"
echo "   • 電腦要保持開機狀態"
echo ""
read -p "按 Enter 關閉視窗..."
