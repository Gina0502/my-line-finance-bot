import os
import json
import traceback

from dotenv import load_dotenv
load_dotenv()

from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FollowEvent,
    FlexSendMessage, TemplateSendMessage, CarouselTemplate,
    CarouselColumn, MessageAction,
)
from linebot.exceptions import InvalidSignatureError
from backend.utils.member_utils import get_base_static_url

# 功能管理器相對匯入，路徑請根據你的專案調整
from .forex_api import ForexManager
from .quiz_api import QuizManager
from .ai_api import AIManager


# 全域物件
line_bot_api: LineBotApi = None
handler: WebhookHandler = None
user_states = {}  # user_id -> 狀態字串
member_data_store = {}  # user_id -> 會員資料字典

# 會員資料檔路徑（請依專案實際路徑修改）
MEMBER_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'members.json')


def load_members():
    if not os.path.isfile(MEMBER_JSON_PATH):
        print("[INFO] 會員資料檔不存在，建立空資料")
        return {}
    try:
        with open(MEMBER_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[INFO] 載入會員資料 {len(data)} 筆")
            return data
    except Exception as e:
        print(f"[ERROR] 載入會員資料失敗：{e}")
        return {}

def handle_body(body: str, signature: str):
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. 中斷處理")
        raise
    except Exception as e:
        print(f"Webhook 處理錯誤：{e}")
        raise

def save_members():
    try:
        with open(MEMBER_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(member_data_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] 儲存會員資料失敗：{e}")


# 載入會員資料
member_data_store = load_members()

# 建立 manager 實體（可依你的類別建構參數微調）
forex_manager = ForexManager()
quiz_manager = QuizManager(
    quiz_filepath="backend/members/quiz_questions.json",
    template_filepath="backend/members/question_bubble_template.json"
)
ai_manager = AIManager()


def get_main_menu_template():
    base_url = get_base_static_url()
    print(f"[DEBUG] 目前 BASE_STATIC_URL：{base_url}")

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
    template = CarouselTemplate(
        columns=columns,
        image_aspect_ratio="rectangle",
        image_size="cover"
    )
    return [TemplateSendMessage(alt_text="歡迎選單", template=template)]


def init_line_bot(channel_secret, channel_access_token):
    global line_bot_api, handler
    line_bot_api = LineBotApi(channel_access_token)
    handler = WebhookHandler(channel_secret)

    handler.add(MessageEvent, message=TextMessage)(handle_message)
    handler.add(FollowEvent)(handle_follow)


def init_member(user_id, profile=None):
    """初始化會員資料，避免KeyError"""
    if user_id not in member_data_store:
        member_data_store[user_id] = {
            "user_id": user_id,
            "name": profile.display_name if profile else "匿名",
            "picture_url": profile.picture_url if profile else "",
            "member_level": "一般會員",
            "quiz_record": {
                "last_date": "",
                "correct_count": 0,
                "total_count": 0,
                "passed_count": 0
            }
        }
        save_members()
        print(f"[INFO] 初始化會員資料 user_id={user_id}")


def handle_follow(event: FollowEvent):
    user_id = event.source.user_id
    try:
        profile = line_bot_api.get_profile(user_id)
    except Exception as e:
        print(f"[取得用戶資料失敗]: {e}")
        profile = None

    init_member(user_id, profile)

    welcome_flex = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"歡迎 {member_data_store[user_id]['name']} 加入！", "weight": "bold", "size": "lg", "wrap": True},
                {"type": "text", "text": "您已成為「一般會員」，祝您使用愉快！", "margin": "md", "wrap": True}
            ]
        }
    }

    main_menu_msgs = get_main_menu_template()

    reply_msgs = [FlexSendMessage(alt_text="歡迎加入", contents=welcome_flex)] + main_menu_msgs
    line_bot_api.reply_message(event.reply_token, reply_msgs)

    user_states[user_id] = "main_menu"


def handle_message(event: MessageEvent):
    user_id = event.source.user_id
    msg = event.message

    if not isinstance(msg, TextMessage):
        print(f"[非文字訊息] user_id={user_id}, type={type(msg)}，略過")
        return

    text = msg.text.strip()

    if user_id not in member_data_store:
        init_member(user_id)

    reply_msgs = []  # 先初始化，避免 append 錯誤

    # 升級挑戰或重測作答優先攔截
    if text.startswith("繼續升級挑戰:"):
        next_level = text.split(":", 1)[1]
        quiz_manager.user_progress[user_id] = {
            "level": next_level,
            "index": 0,
            "correct_count": 0,
        }
        member_data_store[user_id]["member_level"] = next_level
        save_members()
        user_states[user_id] = "quiz_mode"
        reply_msgs = quiz_manager.send_question(user_id)
        line_bot_api.reply_message(event.reply_token, reply_msgs)
        return

    if text.startswith("再挑戰本級:"):
        this_level = text.split(":", 1)[1]
        quiz_manager.user_progress[user_id] = {
            "level": this_level,
            "index": 0,
            "correct_count": 0,
        }
        user_states[user_id] = "quiz_mode"
        reply_msgs = quiz_manager.send_question(user_id)
        line_bot_api.reply_message(event.reply_token, reply_msgs)
        return

    if text == "開始作答":
        progress = quiz_manager.user_progress.get(user_id)
        if not progress:
            level = member_data_store.get(user_id, {}).get("member_level", "一般會員")
            quiz_manager.user_progress[user_id] = {
                "level": level,
                "index": 0,
                "correct_count": 0,
            }
        user_states[user_id] = "quiz_mode"
        reply_msgs = quiz_manager.send_question(user_id)
        line_bot_api.reply_message(event.reply_token, reply_msgs)
        return

    state = user_states.get(user_id, "main_menu")
    level = member_data_store.get(user_id, {}).get("member_level", "一般會員")

    # 主選單狀態
    if state == "main_menu":
        if text == "💱 外幣換算":
            user_states[user_id] = "forex_mode"
            reply_msgs = forex_manager.start_forex(user_id)
            line_bot_api.reply_message(event.reply_token, reply_msgs)
            return

        elif text == "📚 金融小學堂":
            user_states[user_id] = "quiz_mode"
            level = member_data_store.get(user_id, {}).get("member_level", "一般會員")
            reply_msgs = quiz_manager.start_quiz(user_id, level)
            line_bot_api.reply_message(event.reply_token, reply_msgs)
            return

        elif text == "☺︎ 詢問AI":
            user_states[user_id] = "ai_mode"
            reply_msgs = ai_manager.get_ai_mode_flex()
            line_bot_api.reply_message(event.reply_token, reply_msgs)
            return

        else:
            # 主選單或不認識指令，回主選單提示
            reply_msgs = get_main_menu_template()
            reply_msgs.append(TextSendMessage(text="請從下方選單選擇功能或點擊按鈕開始。"))
            line_bot_api.reply_message(event.reply_token, reply_msgs)
            return

    # 外幣換算模式
    elif state == "forex_mode":
        reply_msgs = forex_manager.process_forex(user_id, text)
        # 完成後返回主選單
        if forex_manager.is_done(user_id):
            user_states[user_id] = "main_menu"
        line_bot_api.reply_message(event.reply_token, reply_msgs)
        return

    # 金融小學堂 quiz 模式
    elif state == "quiz_mode":
        reply_msgs = quiz_manager.process_quiz(user_id, text)
        # 升級等級紀錄處理
        if hasattr(quiz_manager, "last_upgrade_level") and user_id in quiz_manager.last_upgrade_level:
            new_level = quiz_manager.last_upgrade_level[user_id]
            member_data_store[user_id]["member_level"] = new_level
            save_members()
            del quiz_manager.last_upgrade_level[user_id]

        # 繼續或結束 quiz
        if quiz_manager.is_done(user_id):
            user_states[user_id] = "main_menu"

        line_bot_api.reply_message(event.reply_token, reply_msgs)
        return

    # AI 問答模式
    elif state == "ai_mode":
        if text == "結束提問":
            user_states[user_id] = "main_menu"
            reply_msgs = get_main_menu_template()
            reply_msgs.append(TextSendMessage(text="已離開AI客服，回到主選單"))
            line_bot_api.reply_message(event.reply_token, reply_msgs)
            return
        else:
            reply_msgs = ai_manager.ask(user_id, text)
            line_bot_api.reply_message(event.reply_token, reply_msgs)
            return

    # 預設回主選單，避免狀態異常
    user_states[user_id] = "main_menu"
    reply_msgs = get_main_menu_template()
    reply_msgs.append(TextSendMessage(text="發生異常，已回到主選單，請重新操作"))
    line_bot_api.reply_message(event.reply_token, reply_msgs)
