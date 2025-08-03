# my-line-finance-bot

這是一個 LINE 金融教學與互動機器人專案，提供外幣匯率查詢、金融小學堂、AI 問答等功能。
backend/
├── handlers/ # 機器人各主要功能的程式碼
├── members/ # 會員與題庫相關 json
├── static/ # 靜態圖片資源（LINE 回覆會用到）
├── utils/ # 共用工具/輔助函式
├── app.py # 主程式檔

## 安裝步驟
1. 安裝虛擬環境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

2. 設定 .env 環境變數（範例內容如下，要自行填寫）  
LINE_CHANNEL_SECRET=xxxx
LINE_CHANNEL_ACCESS_TOKEN=xxx
GEMINI_API_KEY=XXX

3. 啟動伺服器
python -m backend.app


## 功能介紹

- 外幣換算：即時查詢多國匯率
- 金融小學堂：分等級多題庫，答題完成可升級
- AI 金融助理：可詢問金融相關知識

## 作者

- Gina

## 其他事項

- 靜態圖片請放在 `backend/static/`
- 會員題庫資料於 `backend/members/`

---

## 3. 存檔和版本控制

- 編輯完按下儲存（Ctrl+S）。
- 用 git 加入版本控制：

git add README.md
git commit -m "Update README.md"
git push


---

## 小提醒

- Markdown 支援標題（#）、粗體、連結、圖片、程式碼格式等，多多活用能讓說明更美觀易讀。
- GitHub 會自動渲染 README.md 為首頁。
---
如果你需要補充說明某一區（如安裝、功能介紹），只要直接編輯對應區塊即可。如果你有檔案內容想改我再幫你看、或寫出專案專屬介紹，也可以把現在內容提供給我協助潤飾！
