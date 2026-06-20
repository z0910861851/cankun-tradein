#!/bin/bash
# ════════════════════════════════════════════════════════════
#  燦坤 Trade-in 週報 — 一鍵更新腳本
#
#  使用方式：
#  1. 把新一週 Excel 放到同目錄的 data-archive/ 資料夾
#  2. 雙擊本檔案
#  3. 跑完看到「✅ 全部完成」就完成
# ════════════════════════════════════════════════════════════

set -e
cd "$(dirname "$0")"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

clear
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         燦坤 Trade-in 週報 — 一鍵更新                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

REPO_DIR="$(pwd)"
DATA_DIR="$REPO_DIR/data-archive"
SKILL_PATH="$REPO_DIR/skill/analyze_and_report.py"
GITHUB_REPO="z0910861851/cankun-tradein"

# ── Step 0：檢查環境 ──
echo -e "${BLUE}🔍 Step 0／5：檢查環境${NC}"
echo "──────────────────────────────────────────────"

if ! command -v python3 &> /dev/null; then
  echo -e "${RED}❌ 找不到 python3${NC}"
  read -p "按 Enter 結束..."; exit 1
fi
echo "✅ Python: $(python3 --version)"

if ! python3 -c "import pandas" 2>/dev/null; then
  echo -e "${YELLOW}⚠️  安裝 pandas 中…${NC}"
  pip3 install --user pandas openpyxl
fi
echo "✅ pandas 已安裝"

echo ""

# ── Step 1：從 Google Drive 同步資料 ──
echo -e "${BLUE}☁️  Step 1／5：從 Google Drive 同步資料${NC}"
echo "──────────────────────────────────────────────"
python3 "$REPO_DIR/skill/sync_from_drive.py" 2>/dev/null

echo ""
echo "📱 讀取 iPhone 銷量截圖..."
python3 "$REPO_DIR/skill/ocr_iphone_sales.py" 2>/dev/null
echo ""

EXCEL_COUNT=$(ls -1 "$DATA_DIR"/*.xlsx 2>/dev/null | wc -l | tr -d ' ')
if [ "$EXCEL_COUNT" -eq 0 ]; then
  echo -e "${RED}❌ data-archive 內沒有 Excel 檔${NC}"
  read -p "按 Enter 結束..."; exit 1
fi
echo "✅ data-archive 內有 $EXCEL_COUNT 個 Excel 檔"
echo ""

# ── Step 2：上傳回收價到 Firebase ──
echo -e "${BLUE}💰 Step 2／5：更新回收價格${NC}"
echo "──────────────────────────────────────────────"
python3 "$REPO_DIR/skill/upload_prices.py" 2>/dev/null
echo ""

# ── Step 3：分析 + 產生 HTML ──
echo -e "${BLUE}📊 Step 3／5：分析 Excel 資料${NC}"
echo "──────────────────────────────────────────────"
ls -1 "$DATA_DIR"/*.xlsx | sed 's|.*/|  • |'
echo ""

python3 "$SKILL_PATH" \
  --input "$DATA_DIR"/*.xlsx \
  --output "$REPO_DIR/index.html"

echo ""

# ── Step 4：推上 GitHub ──
echo -e "${BLUE}📤 Step 4／5：推送到 GitHub${NC}"
echo "──────────────────────────────────────────────"
cd "$REPO_DIR"
git add index.html skill/
if [ -z "$(git status --short)" ]; then
  echo -e "${YELLOW}⚠️  資料無變化，不需要推送${NC}"
else
  COMMIT_MSG="data: 自動更新（$(date '+%Y-%m-%d %H:%M')）"
  git commit -m "$COMMIT_MSG"

  # 嘗試直接 push；若未設定 credential 則提示輸入 token
  if ! git push origin main 2>&1; then
    echo ""
    echo -e "${YELLOW}⚠️  push 失敗，請輸入 GitHub Personal Access Token：${NC}"
    read -s -p "Token: " TOKEN
    echo ""
    git remote set-url origin "https://${TOKEN}@github.com/${GITHUB_REPO}.git"
    git push origin main
    git remote set-url origin "https://github.com/${GITHUB_REPO}.git"
  fi
  echo "✅ 已推送：$COMMIT_MSG"
fi
echo ""

# ── Step 5：等待 Pages ──
echo -e "${BLUE}⏳ Step 5／5：等待網站上線（最多 1 分鐘）${NC}"
echo "──────────────────────────────────────────────"
for i in $(seq 1 12); do
  sleep 5
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" "https://z0910861851.github.io/cankun-tradein/")
  printf "  [%2d/12] HTTP %s\n" $i "$HTTP"
  if [ "$HTTP" = "200" ]; then break; fi
done
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  ✅ 全部完成！                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "🌐 網站已更新："
echo "   https://z0910861851.github.io/cankun-tradein/"
echo ""
read -p "要在瀏覽器打開確認嗎？(y/N): " open_browser
if [[ "$open_browser" =~ ^[Yy]$ ]]; then
  open "https://z0910861851.github.io/cankun-tradein/"
fi
echo ""
read -p "按 Enter 關閉視窗..."
