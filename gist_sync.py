"""
scripts/gist_sync.py
用 GitHub Gist 當作免費的雲端資料庫
用法：
  python gist_sync.py pull   → 從 Gist 下載所有 JSON 到 data/
  python gist_sync.py push   → 把 data/ 裡的 JSON 上傳到 Gist
"""

import os
import sys
import json
import requests

GIST_ID    = os.environ.get("GIST_ID", "")
TOKEN      = os.environ.get("GIST_TOKEN", "")
DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
API_URL    = f"https://api.github.com/gists/{GIST_ID}"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# 需要同步的檔案清單
SYNC_FILES = [
    "portfolio.json",
    "today_strategy.json",
    "candidates.json",
    "recommendations.json",
]


def pull():
    """從 Gist 下載最新資料到 data/ 目錄"""
    os.makedirs(DATA_DIR, exist_ok=True)

    if not GIST_ID or not TOKEN:
        print("[Gist] 未設定 GIST_ID 或 GIST_TOKEN，跳過下載")
        _ensure_defaults()
        return

    try:
        r = requests.get(API_URL, headers=HEADERS, timeout=10)
        r.raise_for_status()
        files = r.json().get("files", {})

        for fname in SYNC_FILES:
            if fname in files:
                content = files[fname].get("content", "")
                path = os.path.join(DATA_DIR, fname)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[Gist] 下載 {fname} 成功")
            else:
                print(f"[Gist] {fname} 不存在於 Gist，使用預設值")

    except Exception as e:
        print(f"[Gist] 下載失敗: {e}")

    _ensure_defaults()


def push():
    """把 data/ 目錄的 JSON 上傳到 Gist"""
    if not GIST_ID or not TOKEN:
        print("[Gist] 未設定，跳過上傳")
        return

    files_payload = {}
    for fname in SYNC_FILES:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                files_payload[fname] = {"content": f.read()}

    if not files_payload:
        print("[Gist] 沒有可上傳的檔案")
        return

    try:
        r = requests.patch(
            API_URL,
            headers=HEADERS,
            json={"files": files_payload},
            timeout=15,
        )
        r.raise_for_status()
        print(f"[Gist] 上傳成功，共 {len(files_payload)} 個檔案")
    except Exception as e:
        print(f"[Gist] 上傳失敗: {e}")


def _ensure_defaults():
    """確保必要的 JSON 檔案存在，不存在就建立預設值"""
    defaults = {
        "portfolio.json": [],
        "today_strategy.json": {},
        "candidates.json": {"date": "", "candidates": []},
        "recommendations.json": {"date": "", "recommendations": []},
    }
    for fname, default in defaults.items():
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pull"
    if cmd == "pull":
        pull()
    elif cmd == "push":
        push()
    else:
        print(f"未知指令: {cmd}，請使用 pull 或 push")
