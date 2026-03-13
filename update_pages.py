"""
scripts/update_pages.py
把 data/ 裡的 JSON 複製到 web/ 目錄
GitHub Pages 會自動從 web/ 提供靜態檔案
"""
import os, json, shutil

ROOT     = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR  = os.path.join(ROOT, "web")

os.makedirs(WEB_DIR, exist_ok=True)

FILES = ["recommendations.json", "candidates.json",
         "today_strategy.json", "portfolio.json"]

for fname in FILES:
    src = os.path.join(DATA_DIR, fname)
    dst = os.path.join(WEB_DIR, fname)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"[Pages] 複製 {fname} 到 web/")

print("[Pages] 更新完成")
