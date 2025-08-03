import os
import time
import requests
from linebot.models import FlexSendMessage, TextSendMessage, TemplateSendMessage
from backend.utils.member_utils import get_base_static_url

class ForexManager:
    def __init__(self):
        self.user_states = {}
        self.base_currency = "TWD"
        self.mock_rates = {}
        self.last_update = 0
        self.update_interval = 24 * 60 * 60  # 24小時更新一次

    def update_rates(self):
        now = time.time()
        if now - self.last_update < self.update_interval and self.mock_rates:
            return

        url = f"https://open.er-api.com/v6/latest/{self.base_currency}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("result") == "success":
                rates = data.get("rates", {})
                self.mock_rates = {
                    "美元": rates.get("USD"),
                    "日圓": rates.get("JPY"),
                    "歐元": rates.get("EUR"),
                    "人民幣": rates.get("CNY"),
                    "韓元": rates.get("KRW")
                }
                self.last_update = now
                print("[ForexManager] 匯率自動更新成功:", self.mock_rates)
            else:
                print("[ForexManager] 匯率API返回錯誤:", data)
        except Exception as e:
            print("[ForexManager] 匯率更新異常:", e)

    def start_forex(self, user_id):
        self.update_rates()
        self.user_states[user_id] = {"step": 1}
        flex_json = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
            {
                "type": "text",
                "text": "請從按鈕選擇『台幣換外幣』或『外幣換台幣』",
                "wrap": True,
                "weight": "bold",
                "gravity": "center",
                "size": "lg"
            },
            {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "action": {
                    "type": "message",
                    "label": "台幣換外幣",
                    "text": "台幣換外幣"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                    "type": "message",
                    "label": "外幣換台幣",
                    "text": "外幣換台幣"
                    }
                }
                ],
                "spacing": "md"
            }
            ],
            "paddingAll": "xl"
        }
        }
        return [FlexSendMessage(alt_text="選擇換算方式", contents=flex_json)]

    def process_forex(self, user_id, text):
        # 延遲匯入，避免環狀導入錯誤
        from backend.handlers.webhook_handler import get_main_menu_template

        self.update_rates()
        state = self.user_states.get(user_id, {"step": 1})
        step = state.get("step", 1)
        text = text.strip()

        base_url = get_base_static_url()
        if not base_url.endswith("/"):
            base_url += "/"

        currency_images = {
            "美元": base_url + "image7.png",
            "歐元": base_url + "image8.png",
            "日圓": base_url + "image10.png",
            "人民幣": base_url + "image9.png",
            "韓元": base_url + "image7.png"
        }
        print(f'[DEBUG] 目前{base_url}image7.png')

        if step == 1:
            if text not in ["台幣換外幣", "外幣換台幣"]:
                # 用 flex message 重新發送選擇按鈕，提升 UX
                flex_json = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                    {
                        "type": "text",
                        "text": "請從按鈕選擇『台幣換外幣』或『外幣換台幣』",
                        "wrap": True,
                        "weight": "bold",
                        "gravity": "center",
                        "size": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                            "type": "message",
                            "label": "台幣換外幣",
                            "text": "台幣換外幣"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                            "type": "message",
                            "label": "外幣換台幣",
                            "text": "外幣換台幣"
                            }
                        }
                        ],
                        "spacing": "md"
                    }
                    ],
                    "paddingAll": "xl"
                }
                }
        
                return [FlexSendMessage(alt_text="請選擇換算方式", contents=flex_json)]

            state["type"] = text
            state["step"] = 2
            self.user_states[user_id] = state

            columns = []
            for currency, img_url in currency_images.items():
                columns.append({
                    "thumbnailImageUrl": img_url,
                    "title": f"兌換{currency}服務",
                    "text": currency,
                    "actions": [
                        {"type": "message", "label": f"兌換{currency}", "text": currency}
                    ]
                })

            template_json = {
                "type": "carousel",
                "imageAspectRatio": "square",
                "columns": columns
            }
            return [TemplateSendMessage(alt_text="選擇幣種", template=template_json)]

        elif step == 2:
            if text not in self.mock_rates or self.mock_rates[text] is None:
                rates_list = ", ".join([k for k, v in self.mock_rates.items() if v is not None])
                return [TextSendMessage(text=f"我們目前支援的幣種為：{rates_list}，請重新輸入。")]

            state["currency"] = text
            state["step"] = 3
            self.user_states[user_id] = state
            prompt_currency = "台幣" if state["type"] == "台幣換外幣" else text
            return [TextSendMessage(text=f"請輸入您要換算的金額（{prompt_currency}）：")]

        elif step == 3:
            try:
                amount = float(text)
                if amount <= 0:
                    raise ValueError()
            except:
                return [TextSendMessage(text="請輸入有效的正數金額，請重新輸入。")]

            ctype = state["type"]
            currency = state["currency"]
            rate = self.mock_rates[currency]

            if ctype == "台幣換外幣":
                converted = amount * rate
                msg1 = f"金額{amount} 台幣"
                msg2 = f"可換{converted:.2f} {currency}"
            else:
                converted = amount / rate
                msg1 = f"金額{amount} {currency} "
                msg2 = f"可換{converted:.2f} 台幣"

            flex_json = {
                "type": "bubble",
                "body": {
                    "type": "box", "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": msg1, "weight": "bold", "size": "lg"},
                        {"type": "text", "text": msg2, "weight": "bold", "size": "lg"},
                        {"type": "text", "text": f"今日匯率：1 台幣 = {rate:.4f} {currency}", "size": "sm"}
                    ]
                },
                "footer": {
                    "type": "box", "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {"type": "message", "label": "繼續換匯", "text": "台幣換外幣"},
                            "offsetBottom": "md"
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {"type": "message", "label": "回主選單", "text": "主選單"}
                        }
                    ]
                }
            }
            print(flex_json)
            state["step"] = 4
            self.user_states[user_id] = state
            return [FlexSendMessage(alt_text="換算結果", contents=flex_json)]

        elif step == 4:
            if text in ["台幣換外幣", "外幣換台幣"]:
                state["step"] = 2
                state["type"] = text
                self.user_states[user_id] = state

                columns = []
                for currency, img_url in currency_images.items():
                    columns.append({
                        "thumbnailImageUrl": img_url,
                        "title": f"兌換{currency}服務",
                        "text": currency,
                        "actions": [
                            {"type": "message", "label": f"兌換{currency}", "text": currency}
                        ]
                    })

                template_json = {
                    "type": "carousel",
                    "imageAspectRatio": "square",
                    "columns": columns
                }
                return [TemplateSendMessage(alt_text="選擇幣種", template=template_json)]

            elif text == "主選單":
                if user_id in self.user_states:
                    del self.user_states[user_id]
                from backend.handlers.webhook_handler import get_main_menu_template
                return get_main_menu_template()
            else:
                # 用 Flex 的按鈕卡再問一次
                flex_json = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                    {
                        "type": "text",
                        "text": "請從按鈕選擇『台幣換外幣』或『外幣換台幣』",
                        "wrap": True,
                        "weight": "bold",
                        "gravity": "center",
                        "size": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                            "type": "message",
                            "label": "台幣換外幣",
                            "text": "台幣換外幣"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                            "type": "message",
                            "label": "外幣換台幣",
                            "text": "外幣換台幣"
                            }
                        }
                        ],
                        "spacing": "md"
                    }
                    ],
                    "paddingAll": "xl"
                }
                }
                return [FlexSendMessage(alt_text="選擇換算方式", contents=flex_json)]

        else:
            self.user_states[user_id] = {"step": 1}
            return [TextSendMessage(text="流程錯誤，重新開始。請輸入『台幣換外幣』或『外幣換台幣』")]

    def is_done(self, user_id):
        return user_id not in self.user_states or self.user_states[user_id].get("step") == 1
