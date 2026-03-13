# 台股 AI 分析系統 — 完整建立教學

## 你需要準備的帳號（全部免費）

| 服務 | 用途 | 申請網址 |
|---|---|---|
| GitHub | 放程式碼 + 執行排程 + 網頁 | https://github.com |
| Groq | LLM 分析 API | https://console.groq.com |
| Discord | 接收推播通知 | https://discord.com |

---

## 第一步：取得 Groq API Key

1. 前往 https://console.groq.com
2. 點右上角 **Sign Up**，用 Google 帳號登入最快
3. 登入後點左側選單 **API Keys**
4. 點 **Create API Key**，名稱填 `twstock`
5. 複製產生的 Key（格式類似 `gsk_xxxxxxxxxxxx`）
6. **存到記事本，後面會用到**

---

## 第二步：建立 Discord Webhook

1. 打開 Discord，選擇你想接收通知的**頻道**
2. 對頻道點右鍵 → **編輯頻道**
3. 左側點 **整合** → **Webhook**
4. 點 **建立 Webhook**
5. 名稱填 `台股 AI`，頭像可選填
6. 點 **複製 Webhook 網址**（格式類似 `https://discord.com/api/webhooks/...`）
7. **存到記事本**

---

## 第三步：建立 GitHub Gist（當作雲端資料庫）

1. 前往 https://gist.github.com
2. 登入你的 GitHub 帳號
3. **Gist description** 填 `twstock-ai-data`
4. **Filename** 填 `portfolio.json`
5. **內容** 填 `[]`
6. 點右下角 **Create secret gist**
7. 建立後，複製網址列中的 Gist ID
   - 網址格式：`https://gist.github.com/你的帳號/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **最後那串英數字就是 Gist ID**，複製並存到記事本

---

## 第四步：建立 GitHub Personal Access Token

這個 Token 讓 GitHub Actions 有權限讀寫你的 Gist。

1. 前往 https://github.com/settings/tokens
2. 點 **Generate new token** → **Generate new token (classic)**
3. Note 填 `twstock-gist`
4. Expiration 選 **No expiration**（或 1 year）
5. 勾選 **gist** 這個權限
6. 點 **Generate token**
7. 複製產生的 Token（`ghp_xxxxxxxxxxxx`）
8. **存到記事本**

---

## 第五步：Fork 這個 Repository

1. 前往本專案的 GitHub 頁面
2. 點右上角 **Fork** → **Create fork**
3. 等待 Fork 完成

---

## 第六步：設定 Secrets（最重要的步驟）

1. 進入你 Fork 好的 Repository
2. 點上方 **Settings** 頁籤
3. 左側選單找到 **Secrets and variables** → **Actions**
4. 點 **New repository secret**，依序新增以下 4 個：

| Secret 名稱 | 填入的值 |
|---|---|
| `GROQ_API_KEY` | 第一步複製的 Groq Key |
| `DISCORD_WEBHOOK` | 第二步複製的 Discord Webhook 網址 |
| `GIST_ID` | 第三步複製的 Gist ID |
| `GIST_TOKEN` | 第四步複製的 GitHub Token |

每個都要點 **Add secret** 儲存。

---

## 第七步：開啟 GitHub Actions

1. 點上方 **Actions** 頁籤
2. 如果看到黃色警告說 Workflows 被停用，點 **I understand my workflows, enable them**
3. 確認左側看得到：
   - `盤前分析（第零層 + 第一層 + 第二層）`
   - `盤中持倉監控（第三層）`

---

## 第八步：開啟 GitHub Pages（Dashboard 網頁）

1. 點上方 **Settings** 頁籤
2. 左側找到 **Pages**
3. **Source** 選 **Deploy from a branch**
4. **Branch** 選 `main`，資料夾選 `/web`
5. 點 **Save**
6. 等 1～2 分鐘後，網頁會部署到：
   `https://你的GitHub帳號.github.io/twstock-ai/`

---

## 第九步：測試系統是否正常

1. 點 **Actions** → `盤前分析（第零層 + 第一層 + 第二層）`
2. 點右側 **Run workflow** → **Run workflow**
3. 等待執行（約 10～50 分鐘）
4. 執行完成後確認：
   - Discord 頻道收到推播訊息 ✅
   - 前往你的 GitHub Pages 網址，看到 Dashboard ✅
   - Gist 裡面有 recommendations.json 更新 ✅

---

## 第十步：設定持倉（在網頁上操作）

1. 前往你的 GitHub Pages 網址
2. 點 **💼 持倉管理** 頁籤
3. 點 **＋ 新增持倉**
4. 填入：股票代號、名稱、成本價、股數、停利目標、停損點
5. 點 **確認新增**
6. 重要：點右下角出現的 **「同步到雲端」** 按鈕，把持倉資料存到 Gist
   （這樣 GitHub Actions 才看得到你的持倉）

---

## 每日自動執行時間

| 時間（台灣） | 動作 |
|---|---|
| 08:00 | 自動執行第零層、第一層、第二層分析 |
| 08:50 前 | Discord 推播今日推薦清單 |
| 09:00～13:30 | 每 5 分鐘監控持倉，達標立即推播 |
| 13:30 | Discord 推播盤後總結 |

---

## 常見問題

**Q: Actions 顯示失敗？**
點進失敗的 Job 看 log，最常見原因是 Secret 名稱打錯，對照第六步重新確認。

**Q: Discord 沒收到通知？**
在 Actions log 搜尋 `[Discord]`，確認 Webhook URL 有沒有正確讀取到。

**Q: Gist 更新失敗？**
確認 GIST_TOKEN 有勾選 `gist` 權限，且 GIST_ID 是正確的 32 位英數字。

**Q: 想在非交易日手動測試？**
Actions → 選 Workflow → Run workflow，隨時都能手動觸發。
