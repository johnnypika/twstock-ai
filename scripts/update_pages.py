"""
scripts/update_pages.py
確認 data/ 資料夾的 JSON 狀態
GitHub Pages 從根目錄提供靜態檔案，data/ 就在根目錄下
index.html 也在根目錄，路徑完全對應
"""
import os

ROOT     = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data")

FILES = ["recommendations.json", "candidates.json",
         "today_strategy.json", "portfolio.json"]

print("[Pages] 確認資料檔案狀態：")
for fname in FILES:
    path = os.path.join(DATA_DIR, fname)
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  OK data/{fname} ({size} bytes)")
    else:
        print(f"  MISSING data/{fname}")

print("[Pages] 完成")
