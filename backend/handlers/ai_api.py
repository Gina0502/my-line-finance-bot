import os
from dotenv import load_dotenv

load_dotenv()

from linebot.models import TextSendMessage, FlexSendMessage

import google.generativeai as genai

class AIManager:
    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("請設定 GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-pro')  # 確認你的模型名稱正確

    def get_ai_mode_flex(self):
        # 回傳 Flex Message 告知用戶已進入 AI 客服模式
        flex_content = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
            {
                "type": "text",
                "text": "已進入AI客服模式，請輸入您的金融相關問題！",
                "wrap": True,
                "weight": "bold",
                "gravity": "center",
                "size": "xl"
            },
            {
                "type": "text",
                "text": "執行「結束提問」退出AI客服"
            },
            {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "button",
                    "action": {
                    "type": "message",
                    "label": "結束提問",
                    "text": "結束提問"
                    },
                    "style": "secondary"
                }
                ]
            }
            ]
        }
        }
        return [FlexSendMessage(alt_text="AI客服模式", contents=flex_content)]

    def ask(self, user_id, question):
        try:
            # 兩條訊息都放入 list，讓AI回覆限制在金融相關，且字數控制300字內
            response = self.model.generate_content([
                question,
                '請與金融相關回覆，字數300字內'
            ])
            if hasattr(response, "text") and response.text.strip():
                return [TextSendMessage(text=response.text)]
            else:
                print(f"AI 回覆為空: {response}")
                return [TextSendMessage(text="抱歉，無法取得回覆，請稍後再試。")]
        except Exception as e:
            print("AI 問答失敗：", e)
            return [TextSendMessage(text="抱歉，無法回答您的問題，請稍後再試。")]
