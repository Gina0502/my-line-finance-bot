import os
import requests
from dotenv import load_dotenv
from flask import Flask, request, abort, send_from_directory
from linebot.exceptions import InvalidSignatureError
from pyngrok import ngrok
from backend.utils.member_utils import get_base_static_url

load_dotenv()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET or not CHANNEL_TOKEN:
    raise ValueError("❌ 缺少 LINE_CHANNEL_SECRET 或 LINE_CHANNEL_ACCESS_TOKEN，請確認 .env 設定")

from backend.handlers import webhook_handler

app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        webhook_handler.handle_body(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        print("Webhook 處理失敗：", e)
        abort(500)
    return "OK"


@app.route("/static/<path:filename>")
def static_files(filename):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, filename)


def get_ngrok_url():
    try:
        resp = requests.get("http://localhost:4040/api/tunnels")
        data = resp.json()
        for tunnel in data["tunnels"]:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
    except Exception as e:
        print("自動取得 ngrok 公網網址失敗", e)
        return None

if __name__ == "__main__":
    ngrok.kill()
    port = 5000
    tunnel = ngrok.connect(port, bind_tls=True)
    public_url = tunnel.public_url
    print(f"LINE Webhook 公開網址：{public_url}")
    print(f"請將此網址加上 /callback，貼到 LINE Developers Webhook URL")

    ngrok_url = get_ngrok_url()
    if ngrok_url:
        base_static_url = ngrok_url + "/static/"
        os.environ["BASE_STATIC_URL"] = base_static_url
        print("ngrok 靜態圖片網址已設定為：", base_static_url)
    else:
        base_url = get_base_static_url()
        print("使用預設 BASE_STATIC_URL：", base_static_url)

    webhook_handler.init_line_bot(CHANNEL_SECRET, CHANNEL_TOKEN)

    app.run(port=port)
