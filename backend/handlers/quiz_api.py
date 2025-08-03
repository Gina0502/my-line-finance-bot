import os
import json
import random

from linebot.models import TextSendMessage, FlexSendMessage, TemplateSendMessage, CarouselTemplate, CarouselColumn, MessageAction
from backend.utils.member_utils import get_base_static_url


def get_main_menu_template():
    base_url = get_base_static_url()
    columns = [
        CarouselColumn(
            thumbnail_image_url=base_url + "image3.png",
            title="💱外幣換算服務",
            text="小金可以幫我換算匯率唷！",
            actions=[MessageAction(label="我要換算外幣", text="💱 外幣換算")]
        ),
        CarouselColumn(
            thumbnail_image_url=base_url + "image4.png",
            title="📚 金融小學堂",
            text="小金金融業務認證",
            actions=[MessageAction(label="我要認證考", text="📚 金融小學堂")]
        ),
        CarouselColumn(
            thumbnail_image_url=base_url + "image5.png",
            title="֍金融AI客服服務",
            text="可以問問小金金融相關問題唷",
            actions=[MessageAction(label="我要詢問小金AI", text="☺︎ 詢問AI")]
        ),
    ]
    print(f'[DEBUG] 目前{base_url}image4.png')
    template = CarouselTemplate(columns=columns, image_aspect_ratio="rectangle", image_size="cover")
    return [TemplateSendMessage(alt_text="歡迎選單", template=template)]


class QuizManager:
    def __init__(self, quiz_filepath, template_filepath):
        self.quiz_filepath = quiz_filepath
        self.template_filepath = template_filepath
        self.questions_data = self.load_quiz()  # 載入題庫資料，要使用的是 self.questions_data
        self.user_progress = {}  # user_id -> {level, index, correct_count}
        self.user_question_order = {}  # user_id -> 亂數題目索引列表
        self.levels = ["一般會員", "初級金融", "高級金融", "菁英金融"]
        self.last_upgrade_level = {}

    def load_quiz(self):
        if not os.path.exists(self.quiz_filepath):
            print(f"找不到題庫檔案: {self.quiz_filepath}")
            return {}
        with open(self.quiz_filepath, encoding="utf-8") as f:
            return json.load(f)

    def load_template(self):
        if not os.path.exists(self.template_filepath):
            print(f"找不到模板檔案: {self.template_filepath}")
            return None
        with open(self.template_filepath, encoding="utf-8") as f:
            return f.read()

    def start_quiz(self, user_id, level):
        question_list = self.questions_data.get(level, [])
        question_indices = list(range(len(question_list)))
        random.shuffle(question_indices)  # 亂數打亂題目順序
        self.user_question_order[user_id] = question_indices  # 紀錄此用戶題目順序

        self.user_progress[user_id] = {
            "level": level,
            "index": 0,
            "correct_count": 0
        }
        return self.send_question(user_id)

    def send_question(self, user_id):
        progress = self.user_progress.get(user_id)
        if not progress:
            return [TextSendMessage(text="尚未開始測驗，請輸入「我要考題」開始。")]
        level = progress["level"]
        index = progress["index"]
        question_obj = self.get_question(level, index, user_id)
        if not question_obj:
            return self.end_quiz(user_id)
        bubble = self.render_flex_bubble(question_obj, index, level)
        return [FlexSendMessage(alt_text="金融考題", contents=bubble)]

    def get_question(self, level, index, user_id):
        order = self.user_question_order.get(user_id)
        if not order:
            return None  # 尚未開始測驗或題目順序沒設定
        if index >= len(order):
            return None  # 已經做完所有題目
        question_idx = order[index]
        return self.questions_data.get(level, [])[question_idx]

    def check_answer(self, level, index, user_answer, user_id=None):
        if user_id is not None:
            question = self.get_question(level, index, user_id)
        else:
            # 傳統方式，不推薦，未包含題目亂序
            questions = self.questions_data.get(level, [])
            if index >= len(questions):
                return False
            question = questions[index]
        if not question:
            return False
        return user_answer == question.get("answer")

    def process_quiz(self, user_id, user_answer):
        progress = self.user_progress.get(user_id)
        if not progress:
            return [TextSendMessage(text="請輸入「我要考題」開始測驗")]
        level = progress["level"]
        index = progress["index"]

        if self.check_answer(level, index, user_answer, user_id):
            progress["correct_count"] += 1
            reply = TextSendMessage(text="答對了！🎉")
        else:
            correct_ans = self.get_question(level, index, user_id)["answer"]
            reply = TextSendMessage(text=f"答錯了！正確答案是：{correct_ans}")

        progress["index"] += 1

        question_obj = self.get_question(level, progress["index"], user_id)
        if question_obj is None:
            # 測驗結束，算成績與等級升級判定
            correct = progress["correct_count"]
            total = progress["index"]
            level_num = self.levels.index(level)
            self.user_progress.pop(user_id, None)  # 清理進度

            main_menu_msgs = get_main_menu_template()

            if correct / total >= 0.9 and level_num < len(self.levels) - 1:
                next_level = self.levels[level_num + 1]
                self.last_upgrade_level[user_id] = next_level
                return [
                    reply,
                    TextSendMessage(text=f"本次答對 {correct} / {total} 題，正確率達標！🎉 恭喜升級為 {next_level}！"),
                    TextSendMessage(text=f"請點選下方主選單繼續操作。"),
                ] + main_menu_msgs

            if level_num == len(self.levels) - 1 and correct / total >= 0.9:
                # 最高等級且達標
                return [
                    reply,
                    TextSendMessage(text=f"恭喜您，已完成最高等級 {level} 的所有題目且答對率優異！🎉"),
                    TextSendMessage(text="感謝您的熱情參與，歡迎再次練習或探索其他功能。"),
                    TextSendMessage(text=f"請點選下方主選單繼續操作。"),
                ] + main_menu_msgs

            return [
                reply,
                TextSendMessage(text=f"本次答對 {correct} / {total} 題。"),
                TextSendMessage(text="未達升級標準，歡迎再接再厲！"),
                TextSendMessage(text=f"請點選下方主選單繼續操作。"),
            ] + main_menu_msgs

        # 未結束，繼續下一題
        next_questions = self.send_question(user_id)
        return [reply] + next_questions

    def is_done(self, user_id):
        return user_id not in self.user_progress

    def render_flex_bubble(self, question_obj, index, level):
        template_str = self.load_template()
        if template_str is None:
            # 為保險起見，直接回傳簡單訊息
            return {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "題目模板載入失敗，請稍後再試。"}
                    ]
                }
            }
        # 將模板裡的關鍵字取代成題目內容
        replace_map = {
            "%%LEVEL%%": level,
            "%%INDEX%%": str(index + 1),
            "%%QUESTION%%": question_obj.get("question", "")
        }
        for k, v in replace_map.items():
            template_str = template_str.replace(k, v)
        bubble_dict = json.loads(template_str)

        buttons = []
        options = question_obj.get("options", []).copy()  # 複製一份，避免原資料改變
        random.shuffle(options)  # 打亂順序

        for option in options:
            buttons.append({
                "type": "button",
                "action": {"type": "message", "label": option, "text": option},
                "style": "primary",
                "margin": "sm"
            })
        # 假設模板中 contents[3] 是放按鈕區塊
        bubble_dict["body"]["contents"][3]["contents"] = buttons

        return bubble_dict

    def end_quiz(self, user_id):
        self.user_progress.pop(user_id, None)
        main_menu_msgs = get_main_menu_template()
        return [
            TextSendMessage(text="恭喜完成所有題目！"),
            TextSendMessage(text="請從下方選單繼續操作。")
        ] + main_menu_msgs
